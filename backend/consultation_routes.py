__all__ = ['ConsultationThreadCreate', 'ConsultationMessageCreate', 'ConsultationThreadItem', 'ConsultationMessageItem', 'ConsultationCallCreate', 'ConsultationCallAction', 'ConsultationPermissionsUpdate', 'ConsultationCallItem', 'ConsultationCallTokenResponse', '_get_or_create_consultation_thread', '_serialize_consultation_thread', '_ensure_consultation_participant', '_serialize_consultation_call', '_get_livekit_settings', '_consultation_event_user_ids', '_broadcast_consultation_event', 'consultations_websocket', 'list_consultations', 'create_consultation_thread', 'list_consultation_messages', 'create_consultation_message', 'mark_consultation_read', 'update_consultation_permissions', 'list_active_consultation_calls', 'create_consultation_call', 'update_consultation_call', 'get_consultation_call_token']

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
import jwt
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

class ConsultationThreadCreate(BaseModel):
    patient_id: Optional[int] = None
    grant_id: Optional[int] = None


class ConsultationMessageCreate(BaseModel):
    body: str


class ConsultationThreadItem(BaseModel):
    id: Optional[int] = None
    patient_id: int
    patient_name: Optional[str] = None
    doctor_id: Optional[int] = None
    doctor_email: str
    doctor_name: Optional[str] = None
    grant_id: int
    status: str
    can_message: bool
    can_call: bool
    unread_count: int = 0
    last_message: Optional[str] = None
    updated_at: Optional[dt.datetime] = None


class ConsultationMessageItem(BaseModel):
    id: int
    thread_id: int
    sender_user_id: int
    sender_name: Optional[str] = None
    sender_role: str
    body: str
    message_type: str
    read_at: Optional[dt.datetime] = None
    created_at: dt.datetime


class ConsultationCallCreate(BaseModel):
    thread_id: int


class ConsultationCallAction(BaseModel):
    action: str


class ConsultationPermissionsUpdate(BaseModel):
    can_message: Optional[bool] = None
    can_call: Optional[bool] = None


class ConsultationCallItem(BaseModel):
    id: int
    thread_id: int
    doctor_id: int
    patient_id: int
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    status: str
    livekit_room: Optional[str] = None
    created_at: dt.datetime
    accepted_at: Optional[dt.datetime] = None
    ended_at: Optional[dt.datetime] = None


class ConsultationCallTokenResponse(BaseModel):
    server_url: str
    room: str
    token: str


def _get_or_create_consultation_thread(
    db: Session,
    patient: Patient,
    doctor: User,
    grant: DoctorGrant,
    created_by_user_id: int,
) -> ConsultationThread:
    """Find or create an active consultation thread for a grant."""
    if not doctor or not doctor.is_doctor:
        raise HTTPException(status_code=400, detail="Doctor account is required for consultation")

    thread = (
        db.query(ConsultationThread)
        .filter(
            ConsultationThread.patient_id == patient.id,
            ConsultationThread.doctor_id == doctor.id,
            ConsultationThread.grant_id == grant.id,
        )
        .first()
    )
    if thread:
        return thread

    thread = ConsultationThread(
        patient_id=patient.id,
        doctor_id=doctor.id,
        grant_id=grant.id,
        status="active",
        created_by_user_id=created_by_user_id,
        updated_at=dt.datetime.utcnow(),
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


def _serialize_consultation_thread(
    db: Session,
    thread: ConsultationThread,
    grant: DoctorGrant,
    viewer_user_id: Optional[int] = None,
) -> ConsultationThreadItem:
    """Build API response for a consultation thread or grant-backed placeholder."""
    patient = thread.patient if thread else db.query(Patient).filter(Patient.id == grant.patient_id).first()
    doctor = _resolve_doctor_user(db, grant.doctor_id, grant.doctor_email)
    last_message = None
    if thread:
        last = (
            db.query(ConsultationMessage)
            .filter(ConsultationMessage.thread_id == thread.id)
            .order_by(ConsultationMessage.created_at.desc(), ConsultationMessage.id.desc())
            .first()
        )
        last_message = last.body[:120] if last else None
        unread_count = 0
        if viewer_user_id is not None:
            unread_count = (
                db.query(func.count(ConsultationMessage.id))
                .filter(
                    ConsultationMessage.thread_id == thread.id,
                    ConsultationMessage.sender_user_id != viewer_user_id,
                    ConsultationMessage.read_at.is_(None),
                )
                .scalar()
                or 0
            )
    else:
        unread_count = 0

    return ConsultationThreadItem(
        id=thread.id if thread else None,
        patient_id=patient.id if patient else grant.patient_id,
        patient_name=patient.full_name if patient else None,
        doctor_id=doctor.id if doctor else grant.doctor_id,
        doctor_email=grant.doctor_email,
        doctor_name=doctor.full_name if doctor else None,
        grant_id=grant.id,
        status=thread.status if thread else "not_started",
        can_message=bool(getattr(grant, "can_message", True)),
        can_call=bool(getattr(grant, "can_call", False)),
        unread_count=int(unread_count),
        last_message=last_message,
        updated_at=thread.updated_at if thread else grant.granted_at,
    )


def _ensure_consultation_participant(db: Session, thread_id: int, user: User) -> tuple[ConsultationThread, DoctorGrant]:
    """Ensure current user is the patient or doctor participant for a thread."""
    thread = db.query(ConsultationThread).filter(ConsultationThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Consultation not found")

    grant = db.query(DoctorGrant).filter(DoctorGrant.id == thread.grant_id).first()
    if not grant or grant.revoked_at is not None:
        raise HTTPException(status_code=403, detail="Consultation access is not active")

    patient = db.query(Patient).filter(Patient.id == thread.patient_id).first()
    is_patient = bool(patient and patient.user_id == user.id)
    is_doctor = bool(user.is_doctor and thread.doctor_id == user.id)
    if not is_patient and not is_doctor:
        raise HTTPException(status_code=403, detail="No access to this consultation")
    return thread, grant


def _serialize_consultation_call(db: Session, call: ConsultationCall) -> ConsultationCallItem:
    patient = db.query(Patient).filter(Patient.id == call.patient_id).first()
    doctor = db.query(User).filter(User.id == call.doctor_id).first()
    return ConsultationCallItem(
        id=call.id,
        thread_id=call.thread_id,
        doctor_id=call.doctor_id,
        patient_id=call.patient_id,
        patient_name=patient.full_name if patient else None,
        doctor_name=doctor.full_name if doctor else None,
        status=call.status,
        livekit_room=call.livekit_room,
        created_at=call.created_at,
        accepted_at=call.accepted_at,
        ended_at=call.ended_at,
    )


def _get_livekit_settings() -> Tuple[str, str, str]:
    server_url = (os.getenv("LIVEKIT_URL") or "").strip()
    api_key = (os.getenv("LIVEKIT_API_KEY") or "").strip()
    api_secret = (os.getenv("LIVEKIT_API_SECRET") or "").strip()
    if not server_url or not api_key or not api_secret:
        raise HTTPException(status_code=503, detail="LiveKit is not configured")
    return server_url, api_key, api_secret


def _consultation_event_user_ids(db: Session, thread: ConsultationThread) -> List[int]:
    patient = db.query(Patient).filter(Patient.id == thread.patient_id).first()
    user_ids = [thread.doctor_id]
    if patient and patient.user_id:
        user_ids.append(patient.user_id)
    return user_ids


async def _broadcast_consultation_event(
    db: Session,
    thread: ConsultationThread,
    event_type: str,
    payload: Dict[str, Any],
) -> None:
    event = {
        "type": event_type,
        "thread_id": thread.id,
        "patient_id": thread.patient_id,
        "doctor_id": thread.doctor_id,
        **payload,
    }
    await consultation_ws_manager.send_to_users(_consultation_event_user_ids(db, thread), event)


@router.websocket("/api/consultations/ws")
async def consultations_websocket(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return
    try:
        payload = decode_token(token)
        user_id = int(payload.get("sub"))
    except Exception:
        await websocket.close(code=1008)
        return

    await consultation_ws_manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        consultation_ws_manager.disconnect(user_id, websocket)
    except Exception:
        consultation_ws_manager.disconnect(user_id, websocket)


@router.get("/api/consultations", response_model=List[ConsultationThreadItem])
async def list_consultations(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List patient-doctor consultation entries for the current user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_doctor:
        grants = (
            db.query(DoctorGrant)
            .filter(
                DoctorGrant.revoked_at.is_(None),
                (
                    (DoctorGrant.doctor_id == user.id)
                    | (DoctorGrant.doctor_email.ilike(user.email))
                ),
            )
            .order_by(DoctorGrant.granted_at.desc(), DoctorGrant.id.desc())
            .all()
        )
        for grant in grants:
            if grant.doctor_id is None and grant.doctor_email.lower() == user.email.lower():
                grant.doctor_id = user.id
        if grants:
            db.commit()
    else:
        patient = get_patient_for_user(db, user_id)
        if not patient:
            return []
        grants = (
            db.query(DoctorGrant)
            .filter(DoctorGrant.patient_id == patient.id, DoctorGrant.revoked_at.is_(None))
            .order_by(DoctorGrant.granted_at.desc(), DoctorGrant.id.desc())
            .all()
        )

    result: list[ConsultationThreadItem] = []
    for grant in grants:
        thread = (
            db.query(ConsultationThread)
            .filter(ConsultationThread.grant_id == grant.id)
            .order_by(ConsultationThread.updated_at.desc(), ConsultationThread.id.desc())
            .first()
        )
        result.append(_serialize_consultation_thread(db, thread, grant, user_id))
    result.sort(key=lambda item: item.updated_at or dt.datetime.min, reverse=True)
    return result


@router.post("/api/consultations/threads", response_model=ConsultationThreadItem)
async def create_consultation_thread(
    payload: ConsultationThreadCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Create or return a consultation thread backed by an active doctor grant."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_doctor:
        if not payload.patient_id:
            raise HTTPException(status_code=400, detail="patient_id is required")
        patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        grant = _active_grant_for_doctor(db, user, patient.id)
        if not grant:
            raise HTTPException(status_code=403, detail="No active grant")
        if grant.doctor_id is None:
            grant.doctor_id = user.id
            db.commit()
        doctor = user
    else:
        if not payload.grant_id:
            raise HTTPException(status_code=400, detail="grant_id is required")
        patient = get_patient_for_user(db, user_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        grant = (
            db.query(DoctorGrant)
            .filter(
                DoctorGrant.id == payload.grant_id,
                DoctorGrant.patient_id == patient.id,
                DoctorGrant.revoked_at.is_(None),
            )
            .first()
        )
        if not grant:
            raise HTTPException(status_code=404, detail="Grant not found")
        doctor = _resolve_doctor_user(db, grant.doctor_id, grant.doctor_email)
        if not doctor or not doctor.is_doctor:
            raise HTTPException(status_code=400, detail="Doctor has not registered yet")
        if grant.doctor_id is None:
            grant.doctor_id = doctor.id
            db.commit()

    thread = _get_or_create_consultation_thread(db, patient, doctor, grant, user_id)
    write_audit_log(
        db,
        actor_user_id=user_id,
        actor_role="doctor" if user.is_doctor else "patient",
        action="consultation_thread_opened",
        resource_type="consultation_thread",
        resource_id=thread.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        metadata={"grant_id": grant.id},
    )
    db.commit()
    item = _serialize_consultation_thread(db, thread, grant, user_id)
    await _broadcast_consultation_event(db, thread, "thread.updated", {"thread": item})
    return item


@router.get("/api/consultations/threads/{thread_id}/messages", response_model=List[ConsultationMessageItem])
async def list_consultation_messages(
    thread_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List messages for a consultation thread."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    thread, _grant = _ensure_consultation_participant(db, thread_id, user)
    messages = (
        db.query(ConsultationMessage)
        .filter(ConsultationMessage.thread_id == thread.id)
        .order_by(ConsultationMessage.created_at.asc(), ConsultationMessage.id.asc())
        .limit(200)
        .all()
    )
    sender_ids = {message.sender_user_id for message in messages}
    senders = db.query(User).filter(User.id.in_(sender_ids)).all() if sender_ids else []
    senders_by_id = {sender.id: sender for sender in senders}
    return [
        ConsultationMessageItem(
            id=message.id,
            thread_id=message.thread_id,
            sender_user_id=message.sender_user_id,
            sender_name=senders_by_id.get(message.sender_user_id).full_name if senders_by_id.get(message.sender_user_id) else None,
            sender_role="doctor" if (senders_by_id.get(message.sender_user_id) and senders_by_id[message.sender_user_id].is_doctor) else "patient",
            body=message.body,
            message_type=message.message_type,
            read_at=message.read_at,
            created_at=message.created_at,
        )
        for message in messages
    ]


@router.post("/api/consultations/threads/{thread_id}/messages", response_model=ConsultationMessageItem)
async def create_consultation_message(
    thread_id: int,
    payload: ConsultationMessageCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Send a text message in a consultation thread."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    thread, grant = _ensure_consultation_participant(db, thread_id, user)
    if not getattr(grant, "can_message", True):
        raise HTTPException(status_code=403, detail="Messaging is not enabled for this grant")

    body = (payload.body or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="Message body is required")
    if len(body) > 4000:
        raise HTTPException(status_code=400, detail="Message body is too long")

    message = ConsultationMessage(
        thread_id=thread.id,
        sender_user_id=user.id,
        body=body,
        message_type="text",
    )
    thread.updated_at = dt.datetime.utcnow()
    db.add(message)
    write_audit_log(
        db,
        actor_user_id=user_id,
        actor_role="doctor" if user.is_doctor else "patient",
        action="consultation_message_created",
        resource_type="consultation_thread",
        resource_id=thread.id,
        patient_id=thread.patient_id,
        doctor_id=thread.doctor_id,
    )
    db.commit()
    db.refresh(message)
    item = ConsultationMessageItem(
        id=message.id,
        thread_id=message.thread_id,
        sender_user_id=message.sender_user_id,
        sender_name=user.full_name,
        sender_role="doctor" if user.is_doctor else "patient",
        body=message.body,
        message_type=message.message_type,
        read_at=message.read_at,
        created_at=message.created_at,
    )
    await _broadcast_consultation_event(db, thread, "message.created", {"message": item})
    return item


@router.post("/api/consultations/threads/{thread_id}/read")
async def mark_consultation_read(
    thread_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Mark incoming messages in a consultation thread as read."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    thread, _grant = _ensure_consultation_participant(db, thread_id, user)
    now = dt.datetime.utcnow()
    updated = (
        db.query(ConsultationMessage)
        .filter(
            ConsultationMessage.thread_id == thread.id,
            ConsultationMessage.sender_user_id != user.id,
            ConsultationMessage.read_at.is_(None),
        )
        .update({"read_at": now}, synchronize_session=False)
    )
    db.commit()
    if updated:
        await _broadcast_consultation_event(db, thread, "messages.read", {"reader_user_id": user.id, "updated": int(updated)})
    return {"updated": int(updated or 0)}


@router.patch("/api/consultations/grants/{grant_id}/permissions", response_model=ConsultationThreadItem)
async def update_consultation_permissions(
    grant_id: int,
    payload: ConsultationPermissionsUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Patient updates consultation permissions for a doctor grant."""
    patient = get_patient_for_user(db, user_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    grant = (
        db.query(DoctorGrant)
        .filter(DoctorGrant.id == grant_id, DoctorGrant.patient_id == patient.id, DoctorGrant.revoked_at.is_(None))
        .first()
    )
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")
    if payload.can_message is not None:
        grant.can_message = payload.can_message
    if payload.can_call is not None:
        grant.can_call = payload.can_call
    write_audit_log(
        db,
        actor_user_id=user_id,
        actor_role="patient",
        action="doctor_grant_permissions_updated",
        resource_type="doctor_grant",
        resource_id=grant.id,
        patient_id=patient.id,
        doctor_id=grant.doctor_id,
        metadata={"can_message": bool(grant.can_message), "can_call": bool(grant.can_call)},
    )
    db.commit()
    db.refresh(grant)
    thread = (
        db.query(ConsultationThread)
        .filter(ConsultationThread.grant_id == grant.id)
        .order_by(ConsultationThread.updated_at.desc(), ConsultationThread.id.desc())
        .first()
    )
    item = _serialize_consultation_thread(db, thread, grant, user_id)
    if thread:
        await _broadcast_consultation_event(db, thread, "thread.updated", {"thread": item})
    return item


@router.get("/api/consultations/calls/active", response_model=List[ConsultationCallItem])
async def list_active_consultation_calls(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List ringing/accepted calls visible to the current user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    active_statuses = ["ringing", "accepted"]
    if user.is_doctor:
        calls = (
            db.query(ConsultationCall)
            .filter(ConsultationCall.doctor_id == user.id, ConsultationCall.status.in_(active_statuses))
            .order_by(ConsultationCall.created_at.desc(), ConsultationCall.id.desc())
            .all()
        )
    else:
        patient = get_patient_for_user(db, user_id)
        if not patient:
            return []
        calls = (
            db.query(ConsultationCall)
            .filter(ConsultationCall.patient_id == patient.id, ConsultationCall.status.in_(active_statuses))
            .order_by(ConsultationCall.created_at.desc(), ConsultationCall.id.desc())
            .all()
        )
    return [_serialize_consultation_call(db, call) for call in calls]


@router.post("/api/consultations/calls", response_model=ConsultationCallItem)
async def create_consultation_call(
    payload: ConsultationCallCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Doctor starts a consultation call lifecycle."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can start calls")

    thread, grant = _ensure_consultation_participant(db, payload.thread_id, user)
    if not getattr(grant, "can_call", False):
        raise HTTPException(status_code=403, detail="Calls are not enabled for this grant")
    _get_livekit_settings()

    existing = (
        db.query(ConsultationCall)
        .filter(
            ConsultationCall.thread_id == thread.id,
            ConsultationCall.status.in_(["ringing", "accepted"]),
        )
        .order_by(ConsultationCall.created_at.desc(), ConsultationCall.id.desc())
        .first()
    )
    if existing:
        return _serialize_consultation_call(db, existing)

    call = ConsultationCall(
        thread_id=thread.id,
        doctor_id=user.id,
        patient_id=thread.patient_id,
        status="ringing",
        livekit_room=f"consultation-{thread.id}-{int(dt.datetime.utcnow().timestamp())}",
    )
    db.add(call)
    db.flush()
    write_audit_log(
        db,
        actor_user_id=user_id,
        actor_role="doctor",
        action="consultation_call_started",
        resource_type="consultation_call",
        resource_id=call.id,
        patient_id=thread.patient_id,
        doctor_id=user.id,
        metadata={"thread_id": thread.id},
    )
    db.commit()
    db.refresh(call)
    item = _serialize_consultation_call(db, call)
    await _broadcast_consultation_event(db, thread, "call.updated", {"call": item})
    return item


@router.post("/api/consultations/calls/{call_id}/action", response_model=ConsultationCallItem)
async def update_consultation_call(
    call_id: int,
    payload: ConsultationCallAction,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Accept, decline, or end a consultation call."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    call = db.query(ConsultationCall).filter(ConsultationCall.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    thread, _grant = _ensure_consultation_participant(db, call.thread_id, user)

    patient = db.query(Patient).filter(Patient.id == thread.patient_id).first()
    is_patient = bool(patient and patient.user_id == user.id)
    is_doctor = bool(user.is_doctor and call.doctor_id == user.id)
    action = (payload.action or "").strip().lower()
    now = dt.datetime.utcnow()

    if action == "accept":
        if not is_patient:
            raise HTTPException(status_code=403, detail="Only patient can accept the call")
        if call.status != "ringing":
            raise HTTPException(status_code=400, detail="Call is not ringing")
        call.status = "accepted"
        call.accepted_at = now
    elif action == "decline":
        if not is_patient:
            raise HTTPException(status_code=403, detail="Only patient can decline the call")
        if call.status != "ringing":
            raise HTTPException(status_code=400, detail="Call is not ringing")
        call.status = "declined"
        call.ended_at = now
    elif action == "end":
        if not is_patient and not is_doctor:
            raise HTTPException(status_code=403, detail="No access to this call")
        if call.status not in {"ringing", "accepted"}:
            raise HTTPException(status_code=400, detail="Call is already closed")
        call.status = "ended"
        call.ended_at = now
    else:
        raise HTTPException(status_code=400, detail="Unsupported call action")

    write_audit_log(
        db,
        actor_user_id=user_id,
        actor_role="doctor" if user.is_doctor else "patient",
        action=f"consultation_call_{action}",
        resource_type="consultation_call",
        resource_id=call.id,
        patient_id=thread.patient_id,
        doctor_id=call.doctor_id,
        metadata={"thread_id": thread.id},
    )
    db.commit()
    db.refresh(call)
    item = _serialize_consultation_call(db, call)
    await _broadcast_consultation_event(db, thread, "call.updated", {"call": item})
    return item


@router.get("/api/consultations/calls/{call_id}/token", response_model=ConsultationCallTokenResponse)
async def get_consultation_call_token(
    call_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Issue a LiveKit room token for an active consultation call."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    call = db.query(ConsultationCall).filter(ConsultationCall.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    _ensure_consultation_participant(db, call.thread_id, user)

    if call.status not in {"ringing", "accepted"}:
        raise HTTPException(status_code=400, detail="Call is not active")
    if not user.is_doctor and call.status != "accepted":
        raise HTTPException(status_code=403, detail="Patient can join after accepting the call")

    server_url, api_key, api_secret = _get_livekit_settings()

    room = call.livekit_room or f"consultation-{call.thread_id}-{call.id}"
    if not call.livekit_room:
        call.livekit_room = room
        db.commit()

    now = dt.datetime.now(dt.timezone.utc)
    issued_at = int((now - dt.timedelta(minutes=1)).timestamp())
    identity = f"user-{user.id}"
    display_name = user.full_name or user.email
    payload = {
        "iss": api_key,
        "sub": identity,
        "name": display_name,
        "nbf": issued_at,
        "iat": issued_at,
        "exp": int((now + dt.timedelta(hours=2)).timestamp()),
        "video": {
            "roomJoin": True,
            "room": room,
            "canPublish": True,
            "canSubscribe": True,
            "canPublishData": True,
        },
    }
    token = jwt.encode(payload, api_secret, algorithm="HS256")
    return ConsultationCallTokenResponse(server_url=server_url, room=room, token=token)
