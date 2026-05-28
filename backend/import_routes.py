__all__ = ['_pdf_processing_mode', 'preview_import', 'preview_import_v2', 'upload_pdf_file', 'get_upload_status', 'import_lab_results']

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

def _pdf_processing_mode() -> str:
    """Return 'sync' or 'async' based on environment configuration."""
    mode = (os.getenv("PDF_PROCESSING_MODE") or "").strip().lower()
    if mode in {"sync", "async"}:
        if mode == "async" and not CELERY_ENABLED:
            return "sync"
        return mode
    # Back-compat toggle for dev
    if (os.getenv("PROCESS_PDF_SYNC") or "").strip().lower() in {"1", "true", "yes"}:
        return "sync"
    return "async" if CELERY_ENABLED else "sync"


@router.post("/api/preview", response_model=ImportJson)
async def preview_import(
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    user_id: int = Depends(get_current_user_id),
):
    """
    Preview raw text extraction without saving to database.

    Returns ImportJson with empty items.
    """
    try:
        # Read PDF file
        pdf_bytes = await file.read()

        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="Empty file")

        # Extract raw text only (no parsing)
        try:
            extract_raw_text(pdf_bytes)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        return ImportJson(
            patient_id=patient_id,
            items=[],
            source_pdf=file.filename,
            normalization_method="raw_text_only",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/api/v2/preview", response_model=ImportV2)
async def preview_import_v2(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
):
    """Preview v2 extraction from uploaded PDF via GPT-5.2 structured output."""
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    try:
        return await extract_v2(pdf_bytes)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())


@router.post("/api/files/pdf")
async def upload_pdf_file(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Upload PDF file and extract raw text only.
    Returns analysis_id for the uploaded file.
    """
    # Get current user
    current_user = db.query(User).filter(User.id == user_id).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get or create patient for current user
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        # Create patient if doesn't exist
        patient = Patient(
            user_id=current_user.id,
            full_name=current_user.full_name or current_user.email.split('@')[0],
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

    try:
        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="Empty file")

        upload_dir = os.getenv("UPLOAD_DIR", "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        # Create UploadStatus entry
        upload = UploadStatus(
            patient_id=patient.id,
            file_path="",
            status="pending",
            error_message=None,
        )
        db.add(upload)
        db.commit()
        db.refresh(upload)

        file_name = f"{upload.id}_{file.filename}"
        file_path = os.path.join(upload_dir, file_name)
        with open(file_path, "wb") as f:
            f.write(encrypt_file_data(pdf_bytes))

        upload.file_path = file_path
        db.commit()

        mode = _pdf_processing_mode()
        if mode == "sync":
            upload.status = "processing"
            db.commit()
            try:
                raw_text = extract_raw_text(pdf_bytes)
                raw_text_str = coerce_raw_text(raw_text)
                print(
                    "[RAW_TEXT] type={type_name} len={length} preview={preview}".format(
                        type_name=type(raw_text).__name__,
                        length=len(raw_text_str),
                        preview=repr(raw_text_str[:200]),
                    )
                )

                parse_result = parse_with_ocr_fallback(pdf_bytes, raw_text_str)
                metrics_before = parse_result["metrics_before"]
                print(
                    "[PARSE] records_count={records_count}".format(**metrics_before)
                )
                if parse_result["triggered_by"]:
                    print(
                        "[OCR] triggered_by={triggered_by}".format(
                            triggered_by=parse_result["triggered_by"]
                        )
                    )
                    print(
                        "[PARSE_AFTER_OCR] records_count={records_count}".format(
                            **parse_result["metrics"]
                        )
                    )

                records = parse_result["records"]
                metrics = parse_result["metrics"]
                document_hash = hashlib.sha256(pdf_bytes).hexdigest()
                save_parsed_records(
                    db,
                    patient.id,
                    records,
                    file.filename or "unknown",
                    document_hash,
                )
                upload.status = "done"
                upload.error_message = None
                db.commit()
                analysis_id = _analysis_id(patient.id, file.filename or "unknown")
                response = {
                    "analysis_id": analysis_id,
                    "upload_id": upload.id,
                    "status": upload.status,
                    "items_count": metrics["records_count"],
                    **metrics,
                }
                if metrics["records_count"] == 0:
                    response["warning"] = "no records extracted"
                return response
            except Exception as e:
                upload.status = "error"
                upload.error_message = str(e)
                db.commit()
                raise HTTPException(status_code=500, detail=f"Text extraction error: {e}")

        upload.status = "queued"
        db.commit()

        # Trigger background processing
        process_pdf_task.delay(upload.id)

        return {"upload_id": upload.id, "status": upload.status}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/api/files/status/{upload_id}")
async def get_upload_status(
    upload_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get processing status for an uploaded PDF."""
    patient = db.query(Patient).filter(Patient.user_id == user_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    upload = db.query(UploadStatus).filter(
        UploadStatus.id == upload_id,
        UploadStatus.patient_id == patient.id,
    ).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    return {
        "upload_id": upload.id,
        "status": upload.status,
        "error": upload.error_message,
    }


@router.post("/api/import")
async def import_lab_results(
    file: UploadFile = File(...),
    patient_id: int = Form(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Extract raw text from PDF and save parsed lab results.
    Patient_id must be ID of patient belonging to authenticated user.

    Returns status and number of items imported.
    """
    try:
        # Read PDF file
        pdf_bytes = await file.read()

        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="Empty file")

        # Verify patient belongs to authenticated user
        patient = db.query(Patient).filter(
            Patient.id == patient_id,
            Patient.user_id == user_id,
        ).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        # Extract raw text and parse into minimal records
        try:
            raw_text = extract_raw_text(pdf_bytes)
            raw_text_str = coerce_raw_text(raw_text)
            print(
                "[RAW_TEXT] type={type_name} len={length} preview={preview}".format(
                    type_name=type(raw_text).__name__,
                    length=len(raw_text_str),
                    preview=repr(raw_text_str[:200]),
                )
            )

            parse_result = parse_with_ocr_fallback(pdf_bytes, raw_text_str)
            metrics_before = parse_result["metrics_before"]
            print(
                "[PARSE] records_count={records_count}".format(**metrics_before)
            )
            if parse_result["triggered_by"]:
                print(
                    "[OCR] triggered_by={triggered_by}".format(
                        triggered_by=parse_result["triggered_by"]
                    )
                )
                print(
                    "[PARSE_AFTER_OCR] records_count={records_count}".format(
                        **parse_result["metrics"]
                    )
                )

            records = parse_result["records"]
            metrics = parse_result["metrics"]
            document_hash = hashlib.sha256(pdf_bytes).hexdigest()
            save_parsed_records(
                db,
                patient_id,
                records,
                file.filename or "unknown",
                document_hash,
            )
        except HTTPException:
            raise
        except Exception as e:
            # Surface OpenAI / parsing issues as HTTP 502 to client
            raise HTTPException(status_code=502, detail=f"Text extraction error: {e}")

        response = {
            "status": "ok",
            "items_count": metrics["records_count"],
            "patient_id": patient_id,
            **metrics,
        }
        if metrics["records_count"] == 0:
            response["warning"] = "no records extracted"
        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
