__all__ = ['BloodPressureCreate', 'BloodPressureItem', 'TemperatureCreate', 'TemperatureItem', 'UserUpdate', 'get_patient_analyses', 'get_patient_series', 'get_me_shortcut', 'update_me', 'create_blood_pressure', 'list_blood_pressure', 'create_temperature', 'list_temperature']

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

class BloodPressureCreate(BaseModel):
    systolic: int
    diastolic: int
    pulse: Optional[int] = None
    measured_at: Optional[str] = None  # ISO datetime, defaults to now
    notes: Optional[str] = None


class BloodPressureItem(BaseModel):
    id: int
    measured_at: str
    systolic: int
    diastolic: int
    pulse: Optional[int]
    notes: Optional[str]
    created_at: str


class TemperatureCreate(BaseModel):
    value: float  # Celsius
    measured_at: Optional[str] = None
    notes: Optional[str] = None


class TemperatureItem(BaseModel):
    id: int
    measured_at: str
    value: float
    notes: Optional[str]
    created_at: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None


@router.get("/api/patient/analyses")
async def get_patient_analyses(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get all analyses for current patient.

    Р’РђР–РќРћ: Р·РґРµСЃСЊ РјС‹ РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅРѕ С„РёР»СЊС‚СЂСѓРµРј РјСѓСЃРѕСЂРЅС‹Рµ Р·Р°РїРёСЃРё, РєРѕС‚РѕСЂС‹Рµ РЅР° СЃР°РјРѕРј РґРµР»Рµ
    СЏРІР»СЏСЋС‚СЃСЏ С€Р°РїРєРѕР№ PDF (NUMERO DE SERVICIO, PACIENTE, GENERALES Рё С‚.Рї.), Р° РЅРµ
    Р»Р°Р±РѕСЂР°С‚РѕСЂРЅС‹РјРё РїРѕРєР°Р·Р°С‚РµР»СЏРјРё. Р­С‚Рѕ РЅСѓР¶РЅРѕ, С‡С‚РѕР±С‹ РЅР° РіСЂР°С„РёРєР°С… РЅРµ РїРѕСЏРІР»СЏР»РёСЃСЊ
    В«РіРµРЅРµСЂР°Р»РµСЃРёВ» Рё РЅРѕРјРµСЂР° СѓСЃР»СѓРі РІРјРµСЃС‚Рѕ СЂРµР°Р»СЊРЅС‹С… Р°РЅР°Р»РёР·РѕРІ.
    """
    # РќР°Р±РѕСЂ РѕС‡РµРІРёРґРЅРѕ РЅРµ-Р°РЅР°Р»РёС‚РёС‡РµСЃРєРёС… Р·Р°РіРѕР»РѕРІРєРѕРІ / СЃР»СѓР¶РµР±РЅС‹С… СЃС‚СЂРѕРє
    header_keywords = [
        "NUMERO DE SERVICIO",
        "PACIENTE",
        "GENERALES",
        "MEDICO",
        "FECHA DE REGISTRO",
        "FECHA DE LIBERACION",
        "IMP.DERESULTADOS",
        "RESPONSABLE DE LABORATORIO",
        "RESPONSABLE DE SUCURSAL",
        "CED.PROF",
        "PAG.",
        "VALORES DE REFERENCIA",
        "OTROS",
        "OTROS:",
    ]

    def is_junk_lab_result(result: "LabResult") -> bool:
        """Filter out junk/non-analyte rows parsed from PDFs."""
        name = normalize_analyte_name(result.analyte_name)
        unit_like_patterns = [
            r"^/\s*UL\b",
            r"^X10\^?\d+/?UL\b",
            r"^10\^?\d+/?UL\b",
        ]

        junk_names = {
            "RESPONSABLE DE LABORATORIO",
            "RESPONSABLE DE SUCURSAL",
            "OTROS",
            "OTROS:",
            "A",
            "A OPTIMO",
            "A ESTADIO",
            "OPTIMO",
            "ALTO",
            "BAJO",
        }

        if not name:
            return True

        if name in junk_names:
            return True

        # Rows like ''_____'', ''-----'', etc.
        if re.fullmatch(r"[_\-\.\s]{5,}", name):
            return True

        # Strings that look like barcodes: ****** or numbers with asterisks
        compact = name.replace(" ", "")
        if "*" in compact and re.fullmatch(r"\*?\d{6,}\*?\d*\*?", compact):
            return True

        # PDF headers (service number, doctor info, etc.)
        for kw in header_keywords:
            if name.startswith(kw):
                return True

        # Staff signatures like Q.F.B.XXX or similar
        if name.startswith("Q.F.B") or "Q.F.B." in name:
            return True

        # Unit-like labels accidentally parsed as analyte names
        for pattern in unit_like_patterns:
            if re.match(pattern, name):
                return True

        # Long text without digits and without unit/ref ranges -> likely header/footer noise
        if (
            len(name) > 25
            and not any(ch.isdigit() for ch in name)
            and not result.unit
            and not result.ref_range
        ):
            return True

        # Extremely long strings without digits
        if len(name) > 80 and not any(ch.isdigit() for ch in name):
            return True

        # Labels ending with ':' without unit/ref -> section headers
        if name.endswith(":") and not result.unit and not result.ref_range:
            return True

        return False

    # Get current user
    current_user = db.query(User).filter(User.id == user_id).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get patient for current user
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        return []

    # Get all lab results for this patient
    results = db.query(LabResult).filter(LabResult.patient_id == patient.id).all()

    if not results:
        return []

    # Group by source_pdf to create analyses
    analyses_by_source = {}
    metrics_by_source = {}

    for result in results:
        # РћС‚Р±СЂР°СЃС‹РІР°РµРј РѕС‡РµРІРёРґРЅС‹Р№ РјСѓСЃРѕСЂ РёР· С€Р°РїРєРё/С„СѓС‚РµСЂР° PDF
        name_norm = normalize_analyte_name(result.analyte_name)
        if not name_norm or is_junk_lab_result(result):
            continue

        source = result.source_pdf or "unknown"
        if source not in analyses_by_source:
            analyses_by_source[source] = {
                "id": f"{patient.id}_{abs(hash(source)) % 10000}",
                "date": (result.taken_at or result.created_at).isoformat(),
                "source": source,
            }
            metrics_by_source[source] = []

        # Add metric for this result
        metrics_by_source[source].append(
            {
                "name": name_norm,
                "value": result.value,
                "value_text": result.value_text,
                "unit": result.unit,
                "ref_range": result.ref_range,
            }
        )

    # Build response with metrics
    analyses = []
    for source, analysis in analyses_by_source.items():
        analysis["metrics"] = metrics_by_source.get(source, [])
        analyses.append(analysis)

    return analyses


@router.get("/api/patient/series")
async def get_patient_series(
    name: str,  # metric name
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get time series data for a specific metric."""
    # Get current user
    current_user = db.query(User).filter(User.id == user_id).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get patient for current user
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        return []

    # Get all lab results for this metric (normalized match)
    name_norm = normalize_analyte_name(name)
    results = db.query(LabResult).filter(
        LabResult.patient_id == patient.id
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

    # Use the latest available reference range (by date) to keep norms consistent over time
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

    # Avoid mixing different units (e.g., serum vs urine). If all units are the same, keep all ref ranges/points.
    if results:
        units = {r.unit for r in results}
        if len(units) > 1:
            preferred_units = {
                "ERITROCITOS": ["x10^6/uL", "10^6/uL", "x10^6/ul", "10^6/ul"],
                "LEUCOCITOS": ["x10^3/uL", "10^3/uL", "x10^3/ul", "10^3/ul"],
            }

            # Bucket by unit only
            buckets = {}
            for r in results:
                bucket_key = r.unit
                buckets.setdefault(bucket_key, []).append(r)

            name_up = name_norm
            chosen_key = None

            # Prefer whitelisted units first
            if name_up in preferred_units:
                preferred_lower = [u.lower() for u in preferred_units[name_up]]
                for key in buckets.keys():
                    unit_value = key
                    if unit_value and unit_value.lower() in preferred_lower:
                        chosen_key = key
                        break

            # Fallback: bucket with most non-null values, then most rows, then has a unit
            if chosen_key is None:
                def score(bucket_key, items):
                    non_null = sum(1 for x in items if x.value is not None)
                    return (non_null, len(items), 1 if bucket_key else 0)
                chosen_key = max(buckets.items(), key=lambda kv: score(kv[0], kv[1]))[0]

            results = buckets[chosen_key]

            results = [r for r in results if (r.unit, *parse_ref_range(r.ref_range or "")) == chosen_key]

    # Deduplicate and drop obvious outliers (e.g., urine-style ref ranges parsed as creatinina serum)
    seen = set()
    series = []
    for result in results:
        # Skip if no timestamp at all (avoids broken X axis)
        timestamp = result.taken_at if result.taken_at else result.created_at
        if not timestamp:
            continue

        ref_min_tmp, ref_max_tmp = parse_ref_range(result.ref_range or "")
        # If this is creatinina and ref_max is very high (e.g., 30-250 mg/dL), likely urine/24h misparsed -> skip
        if name_norm == "CREATININA" and ref_max_tmp is not None and ref_max_tmp > 10:
            continue

        # Parse ref_range to get min/max
        if latest_ref_min is not None and latest_ref_max is not None:
            ref_min, ref_max = latest_ref_min, latest_ref_max
        else:
            ref_min = None
            ref_max = None
            if result.ref_range:
                # Try to parse "100-200" or "100 a 200" or "min max" format
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
        series.append({
            "t": timestamp.isoformat(),
            "y": result.value,
            "refMin": ref_min,
            "refMax": ref_max,
            "unit": result.unit,  # Add unit for Y-axis label
            "stage": stage,
            "stage_label": stage_label,
        })

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


@router.get("/api/me")
async def get_me_shortcut(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Shortcut for /api/auth/me (frontend compatibility)."""
    print(f"[DEBUG] GET /api/me called for user_id={user_id}")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        print(f"[DEBUG] User not found: id={user_id}")
        raise HTTPException(status_code=404, detail="User not found")

    print(f"[DEBUG] Returning user: {user.email}")
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_doctor": user.is_doctor,
        "is_active": user.is_active,
        "role": "DOCTOR" if user.is_doctor else "PATIENT"
    }


@router.patch("/api/me", response_model=AuthUserResponse)
async def update_me(
    payload: UserUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Update current user's profile (currently only full_name)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.full_name is not None:
        full = payload.full_name.strip()
        if not full:
            raise HTTPException(status_code=400, detail="Full name cannot be empty")
        user.full_name = full
        if not user.is_doctor:
            patient = db.query(Patient).filter(Patient.user_id == user.id).first()
            if patient:
                patient.full_name = full
            else:
                patient = Patient(user_id=user.id, full_name=full)
                db.add(patient)
    db.commit()
    db.refresh(user)
    return AuthUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_doctor=user.is_doctor,
        is_active=user.is_active,
        email_verified=user.email_verified_at is not None,
        role="DOCTOR" if user.is_doctor else "PATIENT",
    )


@router.post("/api/vitals/blood-pressure", response_model=BloodPressureItem)
async def create_blood_pressure(
    payload: BloodPressureCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Record a blood pressure measurement for the authenticated user."""
    measured_at = dt.datetime.utcnow()
    if payload.measured_at:
        try:
            measured_at = dt.datetime.fromisoformat(
                payload.measured_at.replace("Z", "+00:00")
            ).replace(tzinfo=None)
        except ValueError:
            pass

    if not (60 <= payload.systolic <= 250):
        raise HTTPException(status_code=400, detail="Sistólica fuera de rango (60-250)")
    if not (40 <= payload.diastolic <= 150):
        raise HTTPException(status_code=400, detail="Diastólica fuera de rango (40-150)")

    record = BloodPressure(
        user_id=user_id,
        measured_at=measured_at,
        systolic=payload.systolic,
        diastolic=payload.diastolic,
        pulse=payload.pulse,
        notes=payload.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return BloodPressureItem(
        id=record.id,
        measured_at=record.measured_at.isoformat(),
        systolic=record.systolic,
        diastolic=record.diastolic,
        pulse=record.pulse,
        notes=record.notes,
        created_at=record.created_at.isoformat(),
    )


@router.get("/api/vitals/blood-pressure", response_model=List[BloodPressureItem])
async def list_blood_pressure(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List blood pressure readings for the authenticated user."""
    records = (
        db.query(BloodPressure)
        .filter(BloodPressure.user_id == user_id)
        .order_by(BloodPressure.measured_at.desc())
        .limit(200)
        .all()
    )
    return [
        BloodPressureItem(
            id=r.id,
            measured_at=r.measured_at.isoformat(),
            systolic=r.systolic,
            diastolic=r.diastolic,
            pulse=r.pulse,
            notes=r.notes,
            created_at=r.created_at.isoformat(),
        )
        for r in records
    ]


@router.post("/api/vitals/temperature", response_model=TemperatureItem)
async def create_temperature(
    payload: TemperatureCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Record a body temperature measurement for the authenticated user."""
    measured_at = dt.datetime.utcnow()
    if payload.measured_at:
        try:
            measured_at = dt.datetime.fromisoformat(
                payload.measured_at.replace("Z", "+00:00")
            ).replace(tzinfo=None)
        except ValueError:
            pass

    if not (34.0 <= payload.value <= 43.0):
        raise HTTPException(status_code=400, detail="Temperatura fuera de rango (34-43 °C)")

    record = BodyTemperature(
        user_id=user_id,
        measured_at=measured_at,
        value=payload.value,
        notes=payload.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return TemperatureItem(
        id=record.id,
        measured_at=record.measured_at.isoformat(),
        value=record.value,
        notes=record.notes,
        created_at=record.created_at.isoformat(),
    )


@router.get("/api/vitals/temperature", response_model=List[TemperatureItem])
async def list_temperature(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List body temperature readings for the authenticated user."""
    records = (
        db.query(BodyTemperature)
        .filter(BodyTemperature.user_id == user_id)
        .order_by(BodyTemperature.measured_at.desc())
        .limit(200)
        .all()
    )
    return [
        TemperatureItem(
            id=r.id,
            measured_at=r.measured_at.isoformat(),
            value=r.value,
            notes=r.notes,
            created_at=r.created_at.isoformat(),
        )
        for r in records
    ]
