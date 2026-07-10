
from backend.v2_routes import _query_v2_series_rows_for_user
from backend.chat_routes import _trim_chat_context, _openai_chat_with_tools, _is_low_signal_advice

from backend.v2_routes import _query_v2_analytes_for_user
from backend.chat_routes import _build_doctor_chat_context, _summarize_patient_metrics_for_ai
__all__ = ['DoctorChatHistoryItem', 'DoctorChatRequest', 'DoctorChatResponse', 'DoctorNoteRequest', 'DoctorNoteResponse', 'list_v2_doctor_patients', 'list_v2_doctor_patient_analytes', 'get_v2_doctor_patient_series', 'list_v2_patient_notes', 'list_v2_doctor_patient_notes', 'upsert_v2_doctor_patient_note', 'doctor_patients', 'doctor_patient_analyses', 'doctor_patient_series', 'add_doctor_note', 'list_doctor_notes', 'doctor_patient_chat_context', 'doctor_patient_chat', 'list_notes_for_patient']

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

class DoctorChatHistoryItem(BaseModel):
    role: str
    content: str


class DoctorChatRequest(BaseModel):
    message: str
    history: Optional[List[DoctorChatHistoryItem]] = None


class DoctorChatResponse(BaseModel):
    reply: str
    disclaimer: bool = False




from fastapi import APIRouter
router = APIRouter()

class DoctorNoteRequest(BaseModel):
    text: str
    metric_name: Optional[str] = None
    metric_time: Optional[str] = None


class DoctorNoteResponse(BaseModel):
    id: int
    text: str
    doctor_id: int
    doctor_email: Optional[str] = None
    metric_name: Optional[str] = None
    metric_time: Optional[str] = None
    created_at: dt.datetime


@router.get("/api/v2/doctor/patients", response_model=List[V2DoctorPatientResponse])
async def list_v2_doctor_patients(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List patients who granted V2 access to the authenticated doctor."""
    doctor = db.query(User).filter(User.id == user_id).first()
    if not doctor or not doctor.is_doctor:
        raise HTTPException(status_code=403, detail="Not a doctor")

    grants = (
        db.query(DoctorGrant)
        .filter(
            DoctorGrant.revoked_at.is_(None),
            (
                (DoctorGrant.doctor_id == doctor.id)
                | (DoctorGrant.doctor_email.ilike(doctor.email))
            ),
        )
        .order_by(DoctorGrant.granted_at.desc(), DoctorGrant.id.desc())
        .all()
    )
    if not grants:
        return []

    latest_grant_by_patient: dict[int, DoctorGrant] = {}
    for grant in grants:
        if grant.patient_id not in latest_grant_by_patient:
            latest_grant_by_patient[grant.patient_id] = grant

    patient_ids = list(latest_grant_by_patient.keys())
    patients = (
        db.query(Patient)
        .filter(Patient.id.in_(patient_ids))
        .all()
    )
    if not patients:
        return []

    patients_by_id = {patient.id: patient for patient in patients}
    owner_ids = {patient.user_id for patient in patients}

    owners = db.query(User).filter(User.id.in_(owner_ids)).all()
    owners_by_id = {owner.id: owner for owner in owners}

    latest_dates_by_user: dict[int, dt.datetime] = {}
    for row in (
        db.query(
            V2Document.user_id,
            func.max(func.coalesce(V2Document.analysis_date, V2Document.created_at)).label("latest_dt"),
        )
        .filter(V2Document.user_id.in_(owner_ids))
        .group_by(V2Document.user_id)
        .all()
    ):
        if row.latest_dt is not None:
            latest_dates_by_user[row.user_id] = row.latest_dt

    result: list[V2DoctorPatientResponse] = []
    for patient_id, grant in latest_grant_by_patient.items():
        patient = patients_by_id.get(patient_id)
        if not patient:
            continue
        owner = owners_by_id.get(patient.user_id)
        latest_dt = latest_dates_by_user.get(patient.user_id)
        display_name = patient.full_name or (owner.full_name if owner else None)
        result.append(
            V2DoctorPatientResponse(
                patient_id=patient.id,
                display_name=display_name,
                email=owner.email if owner else None,
                granted_at=_iso_or_none(grant.granted_at),
                latest_analysis_date=_iso_or_none(latest_dt),
            )
        )

    result.sort(key=lambda item: ((item.display_name or item.email or "").lower(), item.patient_id))
    write_audit_log(
        db,
        actor_user_id=user_id,
        actor_role="doctor",
        action="doctor_patient_list_viewed",
        resource_type="doctor_patient_list",
        doctor_id=doctor.id,
        metadata={"patients_returned": len(result)},
    )
    db.commit()
    return result


@router.get("/api/v2/doctor/patients/{patient_id}/analytes", response_model=List[V2AnalyteItemResponse])
async def list_v2_doctor_patient_analytes(
    patient_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List V2 analytes for a granted patient in doctor scope."""
    doctor = db.query(User).filter(User.id == user_id).first()
    patient = _ensure_doctor_access(db, doctor, patient_id)
    result = _query_v2_analytes_for_user(db, patient.user_id)
    write_audit_log(
        db,
        actor_user_id=user_id,
        actor_role="doctor",
        action="doctor_patient_analytes_viewed",
        resource_type="patient",
        resource_id=patient.id,
        patient_id=patient.id,
        doctor_id=doctor.id if doctor else None,
        metadata={"analytes_returned": len(result)},
    )
    db.commit()
    return result


@router.get("/api/v2/doctor/patients/{patient_id}/series", response_model=V2SeriesResponse)
async def get_v2_doctor_patient_series(
    patient_id: int,
    analyte_key: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Return V2 series for a granted patient and analyte_key in doctor scope."""
    doctor = db.query(User).filter(User.id == user_id).first()
    patient = _ensure_doctor_access(db, doctor, patient_id)
    rows = _query_v2_series_rows_for_user(db, patient.user_id, analyte_key)

    series_type = _classify_v2_series_type(rows)

    latest_raw_name = None
    latest_unit = None
    latest_reference = None
    for metric, _doc, _dt in reversed(rows):
        if latest_raw_name is None and metric.raw_name is not None:
            latest_raw_name = metric.raw_name
        if latest_unit is None and metric.unit is not None:
            latest_unit = metric.unit
        if latest_reference is None and metric.reference_json is not None:
            latest_reference = metric.reference_json
        if latest_raw_name is not None and latest_unit is not None and latest_reference is not None:
            break

    points = []
    for metric, _doc, dt_value in rows:
        points.append(
            {
                "t": _iso_or_none(dt_value),
                "y": metric.value_numeric,
                "text": metric.value_text,
                "page": metric.page,
                "evidence": metric.evidence,
            }
        )

    write_audit_log(
        db,
        actor_user_id=user_id,
        actor_role="doctor",
        action="doctor_patient_series_viewed",
        resource_type="patient",
        resource_id=patient.id,
        patient_id=patient.id,
        doctor_id=doctor.id if doctor else None,
        metadata={"analyte_key": analyte_key, "points_returned": len(points)},
    )
    db.commit()
    return {
        "analyte_key": analyte_key,
        "raw_name": latest_raw_name,
        "series_type": series_type,
        "unit": latest_unit,
        "reference": latest_reference,
        "points": points,
    }


@router.get("/api/v2/notes", response_model=List[V2DoctorNoteResponse])
async def list_v2_patient_notes(
    analyte_key: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List doctor notes for the authenticated patient and analyte."""
    rows = (
        db.query(V2DoctorNote, User)
        .join(User, User.id == V2DoctorNote.doctor_user_id)
        .filter(
            V2DoctorNote.patient_user_id == user_id,
            V2DoctorNote.analyte_key == analyte_key,
            V2DoctorNote.visibility == "patient",
        )
        .order_by(V2DoctorNote.t.desc(), V2DoctorNote.updated_at.desc())
        .all()
    )
    return [
        _serialize_v2_doctor_note(
            note,
            doctor_name=(doctor.full_name or doctor.email) if doctor else None,
        )
        for note, doctor in rows
    ]


@router.get("/api/v2/doctor/patients/{patient_id}/notes", response_model=List[V2DoctorNoteResponse])
async def list_v2_doctor_patient_notes(
    patient_id: int,
    analyte_key: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List current doctor's point notes for a granted patient and analyte."""
    doctor = db.query(User).filter(User.id == user_id).first()
    patient = _ensure_doctor_access(db, doctor, patient_id)
    rows = (
        db.query(V2DoctorNote)
        .filter(
            V2DoctorNote.patient_user_id == patient.user_id,
            V2DoctorNote.doctor_user_id == user_id,
            V2DoctorNote.analyte_key == analyte_key,
        )
        .order_by(V2DoctorNote.t.desc(), V2DoctorNote.updated_at.desc())
        .all()
    )
    doctor_name = (doctor.full_name or doctor.email) if doctor else None
    result = [_serialize_v2_doctor_note(note, doctor_name=doctor_name) for note in rows]
    write_audit_log(
        db,
        actor_user_id=user_id,
        actor_role="doctor",
        action="doctor_patient_notes_viewed",
        resource_type="patient",
        resource_id=patient.id,
        patient_id=patient.id,
        doctor_id=doctor.id if doctor else None,
        metadata={"analyte_key": analyte_key, "notes_returned": len(result)},
    )
    db.commit()
    return result


@router.post("/api/v2/doctor/patients/{patient_id}/notes", response_model=V2DoctorNoteResponse)
async def upsert_v2_doctor_patient_note(
    patient_id: int,
    payload: V2UpsertDoctorNoteRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Create/update a doctor's point note for a granted patient and analyte."""
    doctor = db.query(User).filter(User.id == user_id).first()
    patient = _ensure_doctor_access(db, doctor, patient_id)

    note_text = payload.note.strip()
    if not note_text:
        raise HTTPException(status_code=400, detail="Note must not be empty")

    point_time = payload.t.replace(tzinfo=None) if payload.t.tzinfo else payload.t
    existing = (
        db.query(V2DoctorNote)
        .filter(
            V2DoctorNote.patient_user_id == patient.user_id,
            V2DoctorNote.doctor_user_id == user_id,
            V2DoctorNote.analyte_key == payload.analyte_key,
            V2DoctorNote.t == point_time,
        )
        .first()
    )

    now = dt.datetime.utcnow()
    if existing:
        existing.note = note_text
        existing.updated_at = now
        note_row = existing
    else:
        note_row = V2DoctorNote(
            patient_user_id=patient.user_id,
            doctor_user_id=user_id,
            analyte_key=payload.analyte_key,
            t=point_time,
            note=note_text,
            visibility="patient",
            created_at=now,
            updated_at=now,
        )
        db.add(note_row)

    db.flush()
    write_audit_log(
        db,
        actor_user_id=user_id,
        actor_role="doctor",
        action="doctor_note_upserted",
        resource_type="v2_doctor_note",
        resource_id=note_row.id,
        patient_id=patient.id,
        doctor_id=doctor.id if doctor else None,
        metadata={"analyte_key": payload.analyte_key},
    )
    db.commit()
    db.refresh(note_row)

    doctor_name = (doctor.full_name or doctor.email) if doctor else None
    return _serialize_v2_doctor_note(note_row, doctor_name=doctor_name)


@router.get("/api/doctor/patients")
async def doctor_patients(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List patients who granted access to the doctor."""
    doctor = db.query(User).filter(User.id == user_id).first()
    if not doctor or not doctor.is_doctor:
        raise HTTPException(status_code=403, detail="Not a doctor")

    grants = (
        db.query(DoctorGrant)
        .filter(
            DoctorGrant.revoked_at.is_(None),
            (
                (DoctorGrant.doctor_id == doctor.id)
                | (DoctorGrant.doctor_email.ilike(doctor.email))
            ),
        )
        .all()
    )
    patient_ids = {g.patient_id for g in grants}
    if not patient_ids:
        return {"patients": []}

    # Latest lab date per patient
    latest_dates = {}
    for row in (
        db.query(LabResult.patient_id, func.max(LabResult.taken_at), func.max(LabResult.created_at))
        .filter(LabResult.patient_id.in_(patient_ids))
        .group_by(LabResult.patient_id)
        .all()
    ):
        pid, max_taken, max_created = row
        latest_dates[pid] = max_taken or max_created

    patients = db.query(Patient).filter(Patient.id.in_(patient_ids)).all()
    result = []
    for p in patients:
        owner = db.query(User).filter(User.id == p.user_id).first()
        # Find corresponding grant for this patient to get granted_at
        g = next((x for x in grants if x.patient_id == p.id), None)
        result.append(
            {
                "patient_id": p.id,
                "email": owner.email if owner else None,
                "full_name": p.full_name,
                "granted_at": g.granted_at.isoformat() if g else None,
                "latest_taken_at": latest_dates.get(p.id).isoformat() if latest_dates.get(p.id) else None,
            }
        )
    return {"patients": result}


@router.get("/api/doctor/patient/{patient_id}/analyses")
async def doctor_patient_analyses(
    patient_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get analyses for a patient (doctor view with grant)."""
    doctor = db.query(User).filter(User.id == user_id).first()
    patient = _ensure_doctor_access(db, doctor, patient_id)

    results = db.query(LabResult).filter(LabResult.patient_id == patient.id).all()
    if not results:
        return []

    analyses_by_source = {}
    metrics_by_source = {}

    for result in results:
        name_norm = normalize_analyte_name(result.analyte_name)
        if not name_norm:
            continue

        source = result.source_pdf or "unknown"
        if source not in analyses_by_source:
            analyses_by_source[source] = {
                "id": f"{patient.id}_{abs(hash(source)) % 10000}",
                "date": (result.taken_at or result.created_at).isoformat() if (result.taken_at or result.created_at) else None,
                "source": source,
            }
            metrics_by_source[source] = []

        metrics_by_source[source].append(
            {
                "name": name_norm,
                "value": result.value,
                "value_text": result.value_text,
                "unit": result.unit,
                "ref_range": result.ref_range,
            }
        )

    analyses = []
    for source, analysis in analyses_by_source.items():
        analysis["metrics"] = metrics_by_source.get(source, [])
        analyses.append(analysis)

    return analyses


@router.get("/api/doctor/patient/{patient_id}/series")
async def doctor_patient_series(
    patient_id: int,
    name: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get series for a patient (doctor view with grant)."""
    doctor = db.query(User).filter(User.id == user_id).first()
    _ensure_doctor_access(db, doctor, patient_id)

    # reuse logic from patient series by calling directly
    # Temporarily override patient fetch
    # Get patient lab results for this metric
    name_norm = normalize_analyte_name(name)
    results = db.query(LabResult).filter(
        LabResult.patient_id == patient_id
    ).all()
    results = [
        r for r in results
        if normalize_analyte_name(r.analyte_name) == name_norm
    ]
    results.sort(key=lambda r: (r.taken_at or r.created_at))

    numeric_results = [r for r in results if r.value is not None]
    if numeric_results:
        results = numeric_results
    else:
        categorical_results = [r for r in results if r.value_text]
        if categorical_results:
            points = []
            for r in categorical_results:
                timestamp = r.taken_at if r.taken_at else r.created_at
                if not timestamp:
                    continue
                points.append(
                    {
                        "date": timestamp.isoformat(),
                        "value_text": r.value_text,
                    }
                )
            return {"series_type": "categorical", "points": points}
        return {"series_type": "numeric", "points": []}

    def parse_ref_range(rr: str):
        if not rr:
            return (None, None)
        numbers = re.findall(r'[\d.]+', rr.replace(',', '.'))
        if len(numbers) >= 2:
            try:
                return (float(numbers[0]), float(numbers[1]))
            except ValueError:
                return (None, None)
        return (None, None)

    latest_ref_min = None
    latest_ref_max = None
    latest_ref_ts = None
    for r in results:
        ts = r.taken_at if r.taken_at else r.created_at
        if not r.ref_range or not ts:
            continue
        ref_min_tmp, ref_max_tmp = parse_ref_range(r.ref_range or "")
        if ref_min_tmp is None or ref_max_tmp is None:
            continue
        if latest_ref_ts is None or ts > latest_ref_ts:
            latest_ref_ts = ts
            latest_ref_min = ref_min_tmp
            latest_ref_max = ref_max_tmp

    if results:
        units = {r.unit for r in results}
        if len(units) > 1:
            buckets = {}
            for r in results:
                bucket_key = r.unit
                buckets.setdefault(bucket_key, []).append(r)

            chosen_key = max(buckets.items(), key=lambda kv: len(kv[1]))[0]
            results = buckets[chosen_key]

    seen = set()
    series = []
    for result in results:
        timestamp = result.taken_at if result.taken_at else result.created_at
        if not timestamp:
            continue
        ref_min_tmp, ref_max_tmp = parse_ref_range(result.ref_range or "")
        if name_norm == "CREATININA" and ref_max_tmp is not None and ref_max_tmp > 10:
            continue

        if latest_ref_min is not None and latest_ref_max is not None:
            ref_min, ref_max = latest_ref_min, latest_ref_max
        else:
            ref_min = ref_max = None
            if result.ref_range:
                numbers = re.findall(r'[\d.]+', result.ref_range.replace(',', '.'))
                if len(numbers) >= 2:
                    try:
                        ref_min = float(numbers[0])
                        ref_max = float(numbers[1])
                    except ValueError:
                        pass
        key = (timestamp.isoformat(), result.value, result.unit)
        if key in seen:
            continue
        seen.add(key)
        stage, stage_label = _derive_egfr_stage_label(name_norm, result.unit, result.value)
        series.append(
            {
                "t": timestamp.isoformat(),
                "y": result.value,
                "refMin": ref_min,
                "refMax": ref_max,
                "unit": result.unit,
                "stage": stage,
                "stage_label": stage_label,
            }
        )

    latest_stage = None
    latest_stage_label = None
    if series:
        latest_stage = series[-1].get("stage")
        latest_stage_label = series[-1].get("stage_label")

    return {
        "series_type": "numeric",
        "points": series,
        "stage": latest_stage,
        "stage_label": latest_stage_label,
    }


@router.post("/api/doctor/patient/{patient_id}/notes", response_model=DoctorNoteResponse)
async def add_doctor_note(
    patient_id: int,
    payload: DoctorNoteRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Add a doctor note for the patient."""
    doctor = db.query(User).filter(User.id == user_id).first()
    _ensure_doctor_access(db, doctor, patient_id)
    if not payload.text or not payload.text.strip():
        raise HTTPException(status_code=400, detail="Note text is required")
    note = DoctorNote(
        patient_id=patient_id,
        doctor_id=doctor.id,
        text=payload.text.strip(),
        metric_name=payload.metric_name,
        metric_time=payload.metric_time,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return DoctorNoteResponse(
        id=note.id,
        text=note.text,
        doctor_id=note.doctor_id,
        doctor_email=doctor.email,
        metric_name=note.metric_name,
        metric_time=note.metric_time,
        created_at=note.created_at,
    )


@router.get("/api/doctor/patient/{patient_id}/notes", response_model=List[DoctorNoteResponse])
async def list_doctor_notes(
    patient_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List notes for a patient (doctor view with grant)."""
    doctor = db.query(User).filter(User.id == user_id).first()
    _ensure_doctor_access(db, doctor, patient_id)
    notes = (
        db.query(DoctorNote)
        .filter(DoctorNote.patient_id == patient_id)
        .order_by(DoctorNote.created_at.desc())
        .limit(50)
        .all()
    )
    result = []
    for n in notes:
        author = db.query(User).filter(User.id == n.doctor_id).first()
        result.append(
            DoctorNoteResponse(
                id=n.id,
                text=n.text,
                doctor_id=n.doctor_id,
                doctor_email=author.email if author else None,
                metric_name=n.metric_name,
                metric_time=n.metric_time,
                created_at=n.created_at,
            )
        )
    return result


@router.get("/api/doctor/patient/{patient_id}/chat/context")
async def doctor_patient_chat_context(
    patient_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Provide chat context for a doctor viewing a patient."""
    doctor = db.query(User).filter(User.id == user_id).first()
    patient = _ensure_doctor_access(db, doctor, patient_id)
    context = _build_doctor_chat_context(db, patient)
    context = _trim_chat_context(context)
    write_audit_log(
        db,
        actor_user_id=user_id,
        actor_role="doctor",
        action="doctor_ai_context_viewed",
        resource_type="patient",
        resource_id=patient.id,
        patient_id=patient.id,
        doctor_id=doctor.id if doctor else None,
        metadata={
            "metrics_snapshot_count": len(context.get("metrics_snapshot") or []),
            "recent_analyses_count": len(context.get("recent_analyses") or []),
        },
    )
    db.commit()
    return context


@router.post("/api/doctor/patient/{patient_id}/chat", response_model=DoctorChatResponse)
async def doctor_patient_chat(
    patient_id: int,
    payload: DoctorChatRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Doctor-facing assistant chat with patient lab context."""
    doctor = db.query(User).filter(User.id == user_id).first()
    patient = _ensure_doctor_access(db, doctor, patient_id)
    question = (payload.message or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Message is required")

    metrics_summary = _summarize_patient_metrics_for_ai(db, patient, days=36500)
    if not metrics_summary:
        return DoctorChatResponse(
            reply="Todavía no hay datos de laboratorio disponibles para este paciente. Primero debe subir o importar informes.",
            disclaimer=False,
        )

    compact_summary = _build_compact_metrics_summary(metrics_summary)
    history_messages: list[dict] = []
    for item in (payload.history or [])[-6:]:
        role = (item.role or "").strip().lower()
        if role not in {"user", "assistant"}:
            continue
        content = (item.content or "").strip()
        if not content:
            continue
        history_messages.append({"role": role, "content": content})

    notes_lines = []
    v2_notes = (
        db.query(V2DoctorNote)
        .filter(V2DoctorNote.patient_user_id == patient.user_id)
        .order_by(V2DoctorNote.updated_at.desc())
        .limit(8)
        .all()
    )
    for n in v2_notes:
        meta = " · ".join(p for p in [n.analyte_key or "", n.t.isoformat() if n.t else ""] if p)
        notes_lines.append(f"- [{meta}] {n.note}" if meta else f"- {n.note}")

    legacy_notes = (
        db.query(DoctorNote)
        .filter(DoctorNote.patient_id == patient.id)
        .order_by(DoctorNote.created_at.desc())
        .limit(5)
        .all()
    )
    for n in legacy_notes:
        meta_parts = [p for p in [n.metric_name or "", n.metric_time or ""] if p]
        prefix = f"[{' · '.join(meta_parts)}] " if meta_parts else ""
        notes_lines.append(f"- {prefix}{n.text}")

    bp_records = (
        db.query(BloodPressure)
        .filter(BloodPressure.user_id == patient.user_id)
        .order_by(BloodPressure.measured_at.desc())
        .limit(10)
        .all()
    )
    bp_lines = []
    for r in bp_records:
        date_str = r.measured_at.strftime("%Y-%m-%d %H:%M")
        line = f"- {date_str}: {r.systolic}/{r.diastolic} mmHg"
        if r.pulse:
            line += f", pulso {r.pulse} lpm"
        if r.notes:
            line += f" ({r.notes})"
        bp_lines.append(line)

    system_prompt = (
        "Eres NephroAI, un asistente clínico de apoyo para médicos en Ecuador, "
        "especializado en seguimiento nefrológico y análisis de laboratorio.\n\n"
        "Usa el contexto de laboratorio del paciente para resumir tendencias, destacar "
        "valores fuera de rango o riesgos, y sugerir qué aclarar o verificar después. "
        "No inventes datos, no diagnostiques de forma definitiva y no prescribas tratamientos "
        "ni dosis. Responde de forma concisa, estructurada y útil para una consulta médica.\n\n"
        "Siempre responde en español."
    )

    user_prompt_parts = [
        f"Paciente: {patient.full_name or ('#' + str(patient.id))}",
        f"Pregunta del médico: {question}",
        "",
        "Resumen de todos los análisis disponibles del paciente (usa get_metric_details para obtener el historial completo de cualquier métrica):",
        compact_summary,
    ]
    if bp_lines:
        user_prompt_parts.append("Registros de presión arterial del paciente (más recientes primero):")
        user_prompt_parts.extend(bp_lines)
    if notes_lines:
        user_prompt_parts.append("Notas médicas recientes:")
        user_prompt_parts.extend(notes_lines)
    history_messages.append({"role": "user", "content": "\n".join(user_prompt_parts)})

    reply = _openai_chat_with_tools(system_prompt, history_messages, metrics_summary)
    if isinstance(reply, str):
        reply = reply.strip()
    if not reply or _is_low_signal_advice(reply):
        reply = _build_deterministic_advice(metrics_summary, "es", 36500)
    write_audit_log(
        db,
        actor_user_id=user_id,
        actor_role="doctor",
        action="doctor_ai_chat_completed",
        resource_type="patient",
        resource_id=patient.id,
        patient_id=patient.id,
        doctor_id=doctor.id if doctor else None,
        metadata={
            "metrics_count": len(metrics_summary),
            "history_count": len(payload.history or []),
            "reply_chars": len(reply or ""),
        },
    )
    db.commit()
    return DoctorChatResponse(reply=reply, disclaimer=True)


@router.get("/api/patient/notes", response_model=List[DoctorNoteResponse])
async def list_notes_for_patient(
    name: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List doctor notes for the authenticated patient (optional metric filter)."""
    patient = get_patient_for_user(db, user_id)
    if not patient:
        return []
    q = db.query(DoctorNote).filter(DoctorNote.patient_id == patient.id)
    if name:
        q = q.filter(DoctorNote.metric_name.ilike(name))
    notes = q.order_by(DoctorNote.created_at.desc()).limit(200).all()
    result = []
    for n in notes:
        author = db.query(User).filter(User.id == n.doctor_id).first()
        result.append(
            DoctorNoteResponse(
                id=n.id,
                text=n.text,
                doctor_id=n.doctor_id,
                doctor_email=author.email if author else None,
                metric_name=n.metric_name,
                metric_time=n.metric_time,
                created_at=n.created_at,
            )
        )
    return result
