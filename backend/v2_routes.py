__all__ = ['_query_v2_analytes_for_user', '_query_v2_series_rows_for_user', 'create_v2_document', 'list_v2_analytes', 'list_v2_documents', 'get_v2_series', 'delete_v2_document', 'get_v2_document']

import logging
logger = logging.getLogger(__name__)

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
    Subscription,
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

def _query_v2_analytes_for_user(db: Session, scoped_user_id: int) -> list[V2AnalyteItemResponse]:
    dt_expr = func.coalesce(V2Document.analysis_date, V2Document.created_at)
    rn = func.row_number().over(
        partition_by=V2Metric.analyte_key,
        order_by=(dt_expr.desc(), V2Document.id.desc(), V2Metric.id.desc()),
    ).label("rn")

    subq = (
        db.query(
            V2Metric.analyte_key.label("analyte_key"),
            V2Metric.raw_name.label("raw_name"),
            V2Metric.value_numeric.label("last_value_numeric"),
            V2Metric.value_text.label("last_value_text"),
            V2Metric.unit.label("unit"),
            dt_expr.label("dt"),
            rn,
        )
        .join(V2Document, V2Metric.document_id == V2Document.id)
        .filter(V2Document.user_id == scoped_user_id)
        .subquery()
    )

    rows = (
        db.query(
            subq.c.analyte_key,
            subq.c.raw_name,
            subq.c.last_value_numeric,
            subq.c.last_value_text,
            subq.c.unit,
            subq.c.dt,
        )
        .filter(subq.c.rn == 1)
        .order_by(subq.c.analyte_key.asc())
        .all()
    )

    return [
        V2AnalyteItemResponse(
            analyte_key=row.analyte_key,
            raw_name=row.raw_name,
            last_value_numeric=row.last_value_numeric,
            last_value_text=row.last_value_text,
            last_date=_iso_or_none(row.dt),
            unit=row.unit,
        )
        for row in rows
    ]


def _query_v2_series_rows_for_user(db: Session, scoped_user_id: int, analyte_key: str):
    dt_expr = func.coalesce(V2Document.analysis_date, V2Document.created_at)
    return (
        db.query(V2Metric, V2Document, dt_expr.label("dt"))
        .join(V2Document, V2Metric.document_id == V2Document.id)
        .filter(
            V2Document.user_id == scoped_user_id,
            V2Metric.analyte_key == analyte_key,
        )
        .order_by(dt_expr.asc(), V2Document.id.asc(), V2Metric.id.asc())
        .all()
    )


@router.post("/api/v2/documents", response_model=V2CreateDocumentResponse | V2CreateDocumentDuplicateResponse)
async def create_v2_document(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Persist a parsed V2 document and metrics for the authenticated user."""
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    # Hard paywall check
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.role != "DOCTOR":
        sub = db.query(Subscription).filter(Subscription.user_id == user_id, Subscription.status == "active").first()
        if not sub:
            raise HTTPException(status_code=403, detail="Se requiere una suscripción activa para subir documentos.")

    document_hash = hashlib.sha256(pdf_bytes).hexdigest()
    try:
        existing_doc = (
            db.query(V2Document)
            .filter(
                V2Document.user_id == user_id,
                V2Document.document_hash == document_hash,
            )
            .first()
        )
        if existing_doc:
            num_metrics = (
                db.query(func.count(V2Metric.id))
                .filter(V2Metric.document_id == existing_doc.id)
                .scalar()
                or 0
            )
            write_audit_log(
                db,
                actor_user_id=user_id,
                actor_role="patient",
                action="v2_document_duplicate_upload",
                resource_type="v2_document",
                resource_id=existing_doc.id,
                metadata={"num_metrics": int(num_metrics)},
            )
            db.commit()
            return {
                "status": "duplicate",
                "document_id": existing_doc.id,
                "analysis_date": _iso_or_none(existing_doc.analysis_date),
                "num_metrics": int(num_metrics),
            }

        try:
            payload = await extract_v2(pdf_bytes)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())

        doc = V2Document(
            user_id=user_id,
            document_hash=document_hash,
            source_filename=file.filename,
            analysis_date=payload.analysis_date,
            report_date=payload.report_date,
        )
        db.add(doc)
        db.flush()

        for metric in payload.metrics:
            db.add(
                V2Metric(
                    document_id=doc.id,
                    analyte_key=metric.analyte_key,
                    raw_name=metric.raw_name,
                    specimen=metric.specimen.value if hasattr(metric.specimen, "value") else str(metric.specimen),
                    context=metric.context.value if hasattr(metric.context, "value") else str(metric.context),
                    value_numeric=metric.value_numeric,
                    value_text=metric.value_text,
                    unit=metric.unit,
                    reference_json=metric.reference.model_dump(mode="json") if metric.reference else None,
                    page=metric.page,
                    evidence=metric.evidence,
                )
            )

        write_audit_log(
            db,
            actor_user_id=user_id,
            actor_role="patient",
            action="v2_document_created",
            resource_type="v2_document",
            resource_id=doc.id,
            metadata={"num_metrics": len(payload.metrics)},
        )
        db.commit()
        r = _get_redis()
        if r:
            try:
                r.delete(f"analyte_snapshot:{user_id}")
            except Exception:
                pass
        db.refresh(doc)
        return {
            "document_id": doc.id,
            "analysis_date": _iso_or_none(doc.analysis_date),
            "num_metrics": len(payload.metrics),
        }
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(V2Document)
            .filter(
                V2Document.user_id == user_id,
                V2Document.document_hash == document_hash,
            )
            .first()
        )
        if existing:
            num_metrics = db.query(V2Metric).filter(V2Metric.document_id == existing.id).count()
            return {
                "document_id": existing.id,
                "analysis_date": _iso_or_none(existing.analysis_date),
                "num_metrics": num_metrics,
            }
        raise HTTPException(status_code=500, detail="Failed to persist V2 document: IntegrityError")
    except Exception as e:
        db.rollback()
        logger.exception(
            "Failed to persist V2 document user_id=%s filename=%s document_hash=%s",
            user_id,
            file.filename,
            document_hash,
        )
        raise HTTPException(status_code=500, detail=f"Failed to persist V2 document: {type(e).__name__}")


@router.get("/api/v2/analytes", response_model=List[V2AnalyteItemResponse])
async def list_v2_analytes(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List user's analytes with latest observed value/date (fast)."""
    return _query_v2_analytes_for_user(db, user_id)


@router.get("/api/v2/documents", response_model=List[V2DocumentListItemResponse])
async def list_v2_documents(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List uploaded V2 documents for the authenticated user."""
    dt_expr = func.coalesce(V2Document.analysis_date, V2Document.created_at)
    rows = (
        db.query(
            V2Document.id.label("id"),
            V2Document.source_filename.label("source_filename"),
            V2Document.analysis_date.label("analysis_date"),
            V2Document.report_date.label("report_date"),
            V2Document.created_at.label("created_at"),
            func.count(V2Metric.id).label("num_metrics"),
        )
        .outerjoin(V2Metric, V2Metric.document_id == V2Document.id)
        .filter(V2Document.user_id == user_id)
        .group_by(
            V2Document.id,
            V2Document.source_filename,
            V2Document.analysis_date,
            V2Document.report_date,
            V2Document.created_at,
        )
        .order_by(dt_expr.desc(), V2Document.id.desc())
        .all()
    )
    return [
        {
            "id": row.id,
            "source_filename": row.source_filename,
            "analysis_date": _iso_or_none(row.analysis_date),
            "report_date": _iso_or_none(row.report_date),
            "created_at": _iso_or_none(row.created_at),
            "num_metrics": int(row.num_metrics or 0),
        }
        for row in rows
    ]


@router.get("/api/v2/series", response_model=V2SeriesResponse)
async def get_v2_series(
    analyte_key: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Return time series for a specific V2 analyte_key."""
    rows = _query_v2_series_rows_for_user(db, user_id, analyte_key)

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

    return {
        "analyte_key": analyte_key,
        "raw_name": latest_raw_name,
        "series_type": series_type,
        "unit": latest_unit,
        "reference": latest_reference,
        "points": points,
    }


@router.delete("/api/v2/documents/{document_id}", response_model=V2DeleteDocumentResponse)
async def delete_v2_document(
    document_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Delete a V2 document and its linked metrics for the authenticated user."""
    document = (
        db.query(V2Document)
        .filter(
            V2Document.id == document_id,
            V2Document.user_id == user_id,
        )
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    num_metrics = (
        db.query(func.count(V2Metric.id))
        .filter(V2Metric.document_id == document.id)
        .scalar()
        or 0
    )
    try:
        write_audit_log(
            db,
            actor_user_id=user_id,
            actor_role="patient",
            action="v2_document_deleted",
            resource_type="v2_document",
            resource_id=document.id,
            metadata={"num_metrics_deleted": int(num_metrics)},
        )
        db.delete(document)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to delete V2 document user_id=%s document_id=%s", user_id, document_id)
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {type(exc).__name__}")

    return {
        "status": "deleted",
        "document_id": document_id,
        "num_metrics_deleted": int(num_metrics),
    }


@router.get("/api/v2/documents/{document_id}", response_model=V2DocumentDetailResponse)
async def get_v2_document(
    document_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Return V2 document and all metrics for debug/trust views."""
    document = (
        db.query(V2Document)
        .filter(
            V2Document.id == document_id,
            V2Document.user_id == user_id,
        )
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    metrics = (
        db.query(V2Metric)
        .filter(V2Metric.document_id == document.id)
        .order_by(V2Metric.analyte_key.asc(), V2Metric.id.asc())
        .all()
    )
    return {
        "document": {
            "id": document.id,
            "user_id": document.user_id,
            "document_hash": document.document_hash,
            "source_filename": document.source_filename,
            "analysis_date": _iso_or_none(document.analysis_date),
            "report_date": _iso_or_none(document.report_date),
            "created_at": _iso_or_none(document.created_at),
        },
        "metrics": [
            {
                "id": metric.id,
                "document_id": metric.document_id,
                "analyte_key": metric.analyte_key,
                "raw_name": metric.raw_name,
                "specimen": metric.specimen,
                "context": metric.context,
                "value_numeric": metric.value_numeric,
                "value_text": metric.value_text,
                "unit": metric.unit,
                "reference_json": metric.reference_json,
                "page": metric.page,
                "evidence": metric.evidence,
            }
            for metric in metrics
        ],
    }
