__all__ = ['_analysis_id', '_parse_ref_range', '_derive_egfr_stage_label', '_summarize_metrics', '_reference_bounds_from_v2', '_summarize_metrics_v2', '_build_compact_metrics_summary', '_short_iso_date', '_fmt_num', '_classify_metric_latest_status', '_iso_or_none', '_serialize_v2_doctor_note', '_normalize_series_text', '_is_missing_like_text', '_is_binary_text', '_is_ordinal_text', '_classify_v2_series_type', '_ensure_doctor_access', '_resolve_doctor_user', '_active_grant_for_doctor']
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

def _analysis_id(patient_id: int, source: str) -> str:
    """Create analysis id consistent with patient analyses grouping."""
    return f"{patient_id}_{abs(hash(source)) % 10000}"


def _parse_ref_range(rr: str):
    """Parse numeric min/max from a ref range string."""
    if not rr:
        return (None, None)
    numbers = re.findall(r"[\d.]+", rr.replace(",", "."))
    if len(numbers) >= 2:
        try:
            return (float(numbers[0]), float(numbers[1]))
        except ValueError:
            return (None, None)
    return (None, None)


def _derive_egfr_stage_label(
    name_norm: str,
    unit: Optional[str],
    value: Optional[float],
) -> tuple[Optional[str], Optional[str]]:
    if value is None or unit is None:
        return None, None
    unit_norm = unit.upper()
    if "ML/MIN/1.73" not in unit_norm:
        return None, None
    if not any(tag in name_norm for tag in ("TFG", "EGFR", "GFR", "FILTRACION")):
        return None, None

    if value >= 90:
        return "G1", "TFG normal"
    if value >= 60:
        return "G2", "TFG levemente disminuida"
    if value >= 45:
        return "G3A", "TFG moderadamente disminuida"
    if value >= 30:
        return "G3B", "TFG moderadamente a severamente disminuida"
    if value >= 15:
        return "G4", "TFG severamente disminuida"
    return "G5", "TFG fallo renal"


def _summarize_metrics(db, patient_id: int, metric_names=None, days: int = 180):
    """Collect recent lab data for the patient."""
    now = dt.datetime.utcnow()
    since = now - dt.timedelta(days=days)

    q = db.query(LabResult).filter(LabResult.patient_id == patient_id)
    q = q.filter((LabResult.taken_at >= since) | (LabResult.created_at >= since))
    if metric_names:
        q = q.filter(LabResult.analyte_name.in_(metric_names))

    rows = q.order_by(LabResult.analyte_name.asc(), LabResult.taken_at.desc(), LabResult.created_at.desc()).all()
    grouped = {}
    for r in rows:
        name = r.analyte_name
        grouped.setdefault(name, [])
        timestamp = r.taken_at or r.created_at
        ref_min, ref_max = _parse_ref_range(r.ref_range or "")
        grouped[name].append(
            {
                "t": timestamp.isoformat() if timestamp else None,
                "value": r.value,
                "unit": r.unit,
                "ref_min": ref_min,
                "ref_max": ref_max,
            }
        )

    # keep up to 5 latest points per metric
    for k, v in grouped.items():
        grouped[k] = v[:5]

    return grouped


def _reference_bounds_from_v2(reference_json: Optional[dict]) -> tuple[Optional[float], Optional[float]]:
    if not reference_json or not isinstance(reference_json, dict):
        return (None, None)
    ref_type = str(reference_json.get("type") or "").lower()
    min_val = reference_json.get("min")
    max_val = reference_json.get("max")
    threshold = reference_json.get("threshold")

    def _to_float(value):
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.replace(",", ".").strip())
            except ValueError:
                return None
        return None

    min_num = _to_float(min_val)
    max_num = _to_float(max_val)
    threshold_num = _to_float(threshold)

    if ref_type == "max" and threshold_num is not None:
        return (None, threshold_num)
    if ref_type == "min" and threshold_num is not None:
        return (threshold_num, None)
    return (min_num, max_num)


def _summarize_metrics_v2(db: Session, user_id: int, metric_names=None, days: int = 180):
    """Collect recent V2 lab data for the user."""
    since = dt.datetime.utcnow() - dt.timedelta(days=days)
    dt_expr = func.coalesce(V2Document.analysis_date, V2Document.created_at)

    rows = (
        db.query(V2Metric, dt_expr.label("dt"))
        .join(V2Document, V2Metric.document_id == V2Document.id)
        .filter(V2Document.user_id == user_id)
        .filter(dt_expr >= since)
        .order_by(V2Metric.analyte_key.asc(), dt_expr.desc(), V2Metric.id.desc())
        .all()
    )

    metric_filters = None
    if metric_names:
        metric_filters = {str(name).strip().upper() for name in metric_names if str(name).strip()}

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for metric, ts in rows:
        key = metric.analyte_key or (metric.raw_name or "").strip().upper()
        if not key:
            continue

        if metric_filters:
            raw_name = (metric.raw_name or "").strip().upper()
            if key.upper() not in metric_filters and raw_name not in metric_filters:
                continue

        grouped.setdefault(key, [])
        reference_json = metric.reference_json if isinstance(metric.reference_json, dict) else None
        ref_min, ref_max = _reference_bounds_from_v2(reference_json)
        grouped[key].append(
            {
                "t": ts.isoformat() if ts else None,
                "value": metric.value_numeric,
                "value_text": metric.value_text,
                "unit": metric.unit,
                "ref_min": ref_min,
                "ref_max": ref_max,
            }
        )

    for name in list(grouped.keys()):
        grouped[name] = grouped[name][:5]
        if not grouped[name]:
            grouped.pop(name, None)

    return grouped


def _build_compact_metrics_summary(metrics_summary: dict) -> str:
    """One-line-per-metric overview of all available lab metrics.

    Used as the initial context in Function Calling mode so the AI can decide
    which metrics to inspect in detail via get_metric_details().
    """
    lines = []
    for key, entries in sorted(metrics_summary.items()):
        if not entries:
            continue
        latest = entries[0]
        value = latest.get("value")
        value_text = latest.get("value_text") or ""
        unit = latest.get("unit") or ""
        ref_min = latest.get("ref_min")
        ref_max = latest.get("ref_max")
        date = (latest.get("t") or "")[:10]

        val_str = str(value) if value is not None else value_text

        if ref_min is not None and ref_max is not None:
            ref_str = f" (ref {ref_min}–{ref_max})"
        elif ref_min is not None:
            ref_str = f" (ref >{ref_min})"
        elif ref_max is not None:
            ref_str = f" (ref <{ref_max})"
        else:
            ref_str = ""

        flag = ""
        if value is not None and ref_min is not None and value < ref_min:
            flag = " ↓"
        elif value is not None and ref_max is not None and value > ref_max:
            flag = " ↑"

        unit_str = f" {unit}" if unit else ""
        date_str = f" [{date}]" if date else ""
        lines.append(f"{key}: {val_str}{unit_str}{ref_str}{date_str}{flag}")

    return "\n".join(lines) if lines else "(sin datos)"


def _short_iso_date(value: Optional[str]) -> str:
    if not value:
        return "-"
    text = str(value).strip()
    if len(text) >= 10:
        return text[:10]
    return text


def _fmt_num(value: Optional[float]) -> str:
    if value is None:
        return "-"
    if float(value).is_integer():
        return str(int(value))
    return f"{float(value):.2f}".rstrip("0").rstrip(".")


def _classify_metric_latest_status(values: list[Dict[str, Any]]) -> str:
    if not values:
        return "unknown"
    latest = values[0]
    value = latest.get("value")
    if value is None:
        return "text" if latest.get("value_text") else "unknown"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "unknown"

    ref_min = latest.get("ref_min")
    ref_max = latest.get("ref_max")
    try:
        min_num = float(ref_min) if ref_min is not None else None
    except (TypeError, ValueError):
        min_num = None
    try:
        max_num = float(ref_max) if ref_max is not None else None
    except (TypeError, ValueError):
        max_num = None

    if min_num is not None and num < min_num:
        return "low"
    if max_num is not None and num > max_num:
        return "high"
    if min_num is not None or max_num is not None:
        return "normal"
    return "no_ref"


def _iso_or_none(value: Optional[dt.datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _serialize_v2_doctor_note(note: V2DoctorNote, doctor_name: Optional[str] = None) -> V2DoctorNoteResponse:
    return V2DoctorNoteResponse(
        id=note.id,
        analyte_key=note.analyte_key,
        t=_iso_or_none(note.t) or "",
        note=note.note,
        doctor_id=note.doctor_user_id,
        doctor_name=doctor_name,
        updated_at=_iso_or_none(note.updated_at) or "",
    )


def _normalize_series_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    text_value = str(value).strip()
    if not text_value:
        return ""
    text_value = unicodedata.normalize("NFKD", text_value)
    text_value = "".join(ch for ch in text_value if not unicodedata.combining(ch))
    text_value = re.sub(r"\s+", " ", text_value).strip().upper()
    return text_value


def _is_missing_like_text(normalized: str) -> bool:
    if not normalized:
        return True
    missing_values = {
        "",
        "-",
        "--",
        "---",
        "N/A",
        "NA",
        "NA`",
        "N.D",
        "N.D.",
        "ND",
        "N/D",
        "NULL",
        "NONE",
        "NO APLICA",
        "NOT AVAILABLE",
    }
    return normalized in missing_values


def _is_binary_text(normalized: str) -> bool:
    compact = re.sub(r"[\s\-_./]+", "", normalized)
    binary_values = {
        "NEG",
        "NEGATIVE",
        "NEGATIVO",
        "POS",
        "POSITIVE",
        "POSITIVO",
        "REACTIVO",
        "NOREACTIVO",
        "REACTIVE",
        "NOREACTIVE",
        "NONREACTIVE",
        "DETECTED",
        "NOTDETECTED",
        "DETECTADO",
        "NODETECTADO",
    }
    return compact in binary_values


def _is_ordinal_text(normalized: str) -> bool:
    compact = normalized.replace(" ", "")
    if not compact:
        return False
    return all(ch == "+" for ch in compact)


def _classify_v2_series_type(rows: list[tuple[Any, Any, Any]]) -> str:
    if not rows:
        return "text"
    all_numeric = all(metric.value_numeric is not None for metric, _doc, _dt in rows)
    no_text_values = all(
        _normalize_series_text(metric.value_text) == "" for metric, _doc, _dt in rows
    )
    if all_numeric and no_text_values:
        return "numeric"

    text_values: list[str] = []
    for metric, _doc, _dt in rows:
        normalized = _normalize_series_text(metric.value_text)
        if _is_missing_like_text(normalized):
            continue
        text_values.append(normalized)

    if text_values and all(_is_binary_text(value) for value in text_values):
        return "binary"
    if text_values and all(_is_ordinal_text(value) for value in text_values):
        return "ordinal"
    return "text"


def _ensure_doctor_access(db: Session, doctor_user: User, patient_id: int) -> Patient:
    """Ensure doctor has an active grant to the patient and return patient."""
    if not doctor_user or not doctor_user.is_doctor:
        raise HTTPException(status_code=403, detail="Not a doctor")
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    grant = (
        db.query(DoctorGrant)
        .filter(
            DoctorGrant.patient_id == patient_id,
            DoctorGrant.revoked_at.is_(None),
            (
                (DoctorGrant.doctor_id == doctor_user.id)
                | (DoctorGrant.doctor_email.ilike(doctor_user.email))
            ),
        )
        .first()
    )
    if not grant:
        raise HTTPException(status_code=403, detail="No access to this patient")
    return patient


def _resolve_doctor_user(db: Session, doctor_id: Optional[int], doctor_email: Optional[str]) -> Optional[User]:
    """Helper to fetch doctor user by id or email."""
    doctor_user = None
    if doctor_id:
        doctor_user = db.query(User).filter(User.id == doctor_id).first()
    if not doctor_user and doctor_email:
        doctor_user = db.query(User).filter(User.email.ilike(doctor_email)).first()
    return doctor_user


def _active_grant_for_doctor(db: Session, doctor: User, patient_id: int) -> Optional[DoctorGrant]:
    """Return active grant for doctor/patient, matching either doctor_id or email."""
    return (
        db.query(DoctorGrant)
        .filter(
            DoctorGrant.patient_id == patient_id,
            DoctorGrant.revoked_at.is_(None),
            (
                (DoctorGrant.doctor_id == doctor.id)
                | (DoctorGrant.doctor_email.ilike(doctor.email))
            ),
        )
        .order_by(DoctorGrant.granted_at.desc(), DoctorGrant.id.desc())
        .first()
    )
