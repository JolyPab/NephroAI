__all__ = ['ShareGrantRequest', 'ShareGrantResponse', 'grant_doctor_access', 'list_grants', 'revoke_grant']

from backend.deps import *
from backend.utils import *
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func, text
from sqlalchemy.sql import over
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from jose import jwt
from pydantic import BaseModel, ValidationError
from typing import Any, Dict, List, Optional, Tuple
import io
import os
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from dotenv import load_dotenv
import hashlib
from pathlib import Path
from backend.models import ImportJson
from backend.v2.extractor import extract as extract_v2
from backend.v2.schemas import (
    ImportV2,
    V2AnalyteItemResponse,
    V2CreateDocumentDuplicateResponse,
    V2CreateDocumentResponse,
    V2DeleteDocumentResponse,
    V2DoctorNoteResponse,
    V2DoctorPatientResponse,
    V2DocumentDetailResponse,
    V2DocumentListItemResponse,
    V2UpsertDoctorNoteRequest,
    V2SeriesResponse,
)
from backend.analyte_utils import normalize_analyte_name
from backend.pdf_parser import extract_raw_text
from backend.parsing.pipeline import coerce_raw_text, parse_with_ocr_fallback
from backend.tasks import process_pdf_task, CELERY_ENABLED
from backend.database import (
    create_db_engine,
    get_session_factory,
    init_db,
    get_database_url,
    DoctorGrant,
    DoctorNote,
    ConsultationThread,
    ConsultationMessage,
    ConsultationCall,
    Patient,
    LabResult,
    User,
    UploadStatus,
    V2DoctorNote,
    V2Document,
    V2Metric,
    ChatSession,
    ChatMessageRecord,
    PatientMemory,
    BloodPressure,
    BodyTemperature,
    AuditLog,
    save_parsed_records,
)
from backend.auth import decode_token, get_current_user_id
from backend.encryption import encrypt_file_data
from backend.auth_routes import router as auth_router, UserResponse as AuthUserResponse
from backend.patient_routes import router as patient_router
import datetime as dt
import json
import re
import requests
import unicodedata
from urllib.parse import urljoin
import redis as redis_lib



from fastapi import APIRouter
router = APIRouter()

class ShareGrantRequest(BaseModel):
    doctor_email: str


class ShareGrantResponse(BaseModel):
    doctor_email: str
    doctor_id: Optional[int] = None
    doctor_name: Optional[str] = None
    can_message: bool = True
    can_call: bool = False
    granted_at: dt.datetime
    revoked_at: Optional[dt.datetime] = None


@router.post("/api/share/grant", response_model=ShareGrantResponse)
async def grant_doctor_access(
    payload: ShareGrantRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Patient grants access to a doctor by email."""
    # Ensure patient record exists for current user
    current_user = db.query(User).filter(User.id == user_id).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    patient = get_patient_for_user(db, user_id)
    if not patient:
        patient = Patient(
            user_id=current_user.id,
            full_name=current_user.full_name or current_user.email.split("@")[0],
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

    doctor_email = payload.doctor_email.strip().lower()
    if not doctor_email:
        raise HTTPException(status_code=400, detail="Doctor email is required")

    doctor_user = db.query(User).filter(User.email.ilike(doctor_email)).first()
    doctor_id = doctor_user.id if doctor_user and doctor_user.is_doctor else None
    doctor_name = doctor_user.full_name if doctor_user else None

    grant = (
        db.query(DoctorGrant)
        .filter(DoctorGrant.patient_id == patient.id, DoctorGrant.doctor_email.ilike(doctor_email))
        .first()
    )
    now = dt.datetime.utcnow()
    if grant:
        grant.revoked_at = None
        grant.granted_at = now
        grant.doctor_id = doctor_id
        if grant.can_message is None:
            grant.can_message = True
        if grant.can_call is None:
            grant.can_call = False
    else:
        grant = DoctorGrant(
            patient_id=patient.id,
            doctor_email=doctor_email,
            doctor_id=doctor_id,
            can_message=True,
            can_call=False,
            granted_at=now,
        )
        db.add(grant)
    db.flush()
    write_audit_log(
        db,
        actor_user_id=user_id,
        actor_role="patient",
        action="doctor_grant_created",
        resource_type="doctor_grant",
        resource_id=grant.id,
        patient_id=patient.id,
        doctor_id=doctor_id,
        metadata={"doctor_email": doctor_email, "can_message": bool(grant.can_message), "can_call": bool(grant.can_call)},
    )
    db.commit()
    db.refresh(grant)
    doctor_user = _resolve_doctor_user(db, grant.doctor_id, grant.doctor_email)
    return ShareGrantResponse(
        doctor_email=grant.doctor_email,
        doctor_id=grant.doctor_id,
        doctor_name=doctor_user.full_name if doctor_user else doctor_name,
        can_message=grant.can_message,
        can_call=grant.can_call,
        granted_at=grant.granted_at,
        revoked_at=grant.revoked_at,
    )


@router.get("/api/share/grants", response_model=List[ShareGrantResponse])
async def list_grants(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List active grants for patient."""
    patient = get_patient_for_user(db, user_id)
    if not patient:
        return []
    grants = (
        db.query(DoctorGrant)
        .filter(DoctorGrant.patient_id == patient.id)
        .order_by(DoctorGrant.granted_at.desc())
        .all()
    )
    result = []
    for g in grants:
        doc_user = _resolve_doctor_user(db, g.doctor_id, g.doctor_email)
        result.append(
            ShareGrantResponse(
                doctor_email=g.doctor_email,
                doctor_id=g.doctor_id,
                doctor_name=doc_user.full_name if doc_user else None,
                can_message=g.can_message,
                can_call=g.can_call,
                granted_at=g.granted_at,
                revoked_at=g.revoked_at,
            )
        )
    return result


@router.delete("/api/share/revoke/{doctor_email}", response_model=ShareGrantResponse)
async def revoke_grant(
    doctor_email: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Revoke doctor access."""
    patient = get_patient_for_user(db, user_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    grant = (
        db.query(DoctorGrant)
        .filter(DoctorGrant.patient_id == patient.id, DoctorGrant.doctor_email.ilike(doctor_email))
        .first()
    )
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")
    grant.revoked_at = dt.datetime.utcnow()
    write_audit_log(
        db,
        actor_user_id=user_id,
        actor_role="patient",
        action="doctor_grant_revoked",
        resource_type="doctor_grant",
        resource_id=grant.id,
        patient_id=patient.id,
        doctor_id=grant.doctor_id,
        metadata={"doctor_email": grant.doctor_email},
    )
    db.commit()
    db.refresh(grant)
    doctor_user = _resolve_doctor_user(db, grant.doctor_id, grant.doctor_email)
    return ShareGrantResponse(
        doctor_email=grant.doctor_email,
        doctor_id=grant.doctor_id,
        doctor_name=doctor_user.full_name if doctor_user else None,
        can_message=grant.can_message,
        can_call=grant.can_call,
        granted_at=grant.granted_at,
        revoked_at=grant.revoked_at,
    )
