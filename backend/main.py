
# Exports for tests
from backend.deps import *
from backend.utils import *
from backend.import_routes import *
from backend.v2_routes import *
from backend.doctor_routes import *
from backend.chat_routes import *
from backend.consultation_routes import *
from backend.share_routes import *
from backend.patient_legacy_routes import *
from backend.billing_routes import *

from backend.import_routes import router as import_router
from backend.v2_routes import router as v2_router
from backend.doctor_routes import router as doctor_router
from backend.chat_routes import router as chat_router
from backend.consultation_routes import router as consultation_router
from backend.share_routes import router as share_router
from backend.patient_legacy_routes import router as patient_legacy_router
from backend.billing_routes import router as billing_router
from backend.deps import *
from backend.utils import *

"""FastAPI application for lab import module."""

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

logger = logging.getLogger(__name__)

_redis_client: Optional[redis_lib.Redis] = None

consultation_ws_manager = ConsultationConnectionManager()

def _ensure_note_columns():
    """Ensure doctor_notes has metric_name/metric_time columns (only for SQLite)."""
    if engine.dialect.name != "sqlite":
        return
    try:
        conn = engine.raw_connection()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(doctor_notes)")
        cols = {row[1] for row in cur.fetchall()}
        if "metric_name" not in cols:
            cur.execute("ALTER TABLE doctor_notes ADD COLUMN metric_name TEXT")
        if "metric_time" not in cols:
            cur.execute("ALTER TABLE doctor_notes ADD COLUMN metric_time TEXT")
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[WARN] Could not ensure doctor_notes columns: {e}")


ENV_PATH = Path(__file__).resolve().parent / ".env"

load_dotenv(dotenv_path=ENV_PATH)

print("[DEBUG] OPENAI_API_KEY loaded:", bool(os.getenv("OPENAI_API_KEY")))

print("[DEBUG] CWD:", os.getcwd())

database_url = get_database_url()

engine = create_db_engine(database_url)

SessionLocal = get_session_factory(engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db(engine)
    _ensure_note_columns()
    yield


_env_value_pre = (os.getenv("ENV") or os.getenv("APP_ENV") or "development").lower()

_docs_url = None if _env_value_pre in {"prod", "production"} else "/docs"

_redoc_url = None if _env_value_pre in {"prod", "production"} else "/redoc"

app = FastAPI(
    title="Lab Import API",
    description="API for importing laboratory test results from PDF files",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
)

_env_value = (os.getenv("ENV") or os.getenv("APP_ENV") or "development").lower()

_is_production = _env_value in {"prod", "production"}

if _is_production:
    cors_raw = os.getenv("CORS_ORIGINS", "")
    allow_origins = [origin.strip() for origin in cors_raw.split(",") if origin.strip()]
    if not allow_origins:
        print("[WARN] CORS_ORIGINS not set in production; CORS will block all origins.")
else:
    allow_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

app.include_router(patient_router)

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/health/ready")
async def readiness():
    """Readiness check for dependencies used by production traffic."""
    checks: Dict[str, str] = {}

    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            checks["database"] = "ok"
        finally:
            db.close()
    except Exception:
        logger.exception("Readiness database check failed")
        checks["database"] = "error"

    require_redis = (os.getenv("REQUIRE_REDIS_HEALTH") or ("true" if _is_production else "false")).lower() in {
        "1",
        "true",
        "yes",
    }
    if require_redis:
        try:
            redis_client = _get_redis()
            if redis_client is None:
                checks["redis"] = "error"
            else:
                redis_client.ping()
                checks["redis"] = "ok"
        except Exception:
            logger.exception("Readiness redis check failed")
            checks["redis"] = "error"
    else:
        checks["redis"] = "skipped"

    ready = all(value in {"ok", "skipped"} for value in checks.values())
    status_code = 200 if ready else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if ready else "not_ready", "checks": checks},
    )


@app.get("/")
async def root():
    """API root - redirect to docs."""
    return RedirectResponse(url="/docs")




app.include_router(import_router)
app.include_router(v2_router)
app.include_router(doctor_router)
app.include_router(chat_router)
app.include_router(consultation_router)
app.include_router(share_router)
app.include_router(patient_legacy_router)
app.include_router(billing_router)
