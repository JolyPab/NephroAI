__all__ = ['_redis_client', 'consultation_ws_manager', 'ConsultationConnectionManager', '_get_redis', 'get_db', 'get_patient_for_user', 'get_current_user', 'write_audit_log']
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

class ConsultationConnectionManager:
    def __init__(self) -> None:
        self._connections: Dict[int, set[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        sockets = self._connections.get(user_id)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: int, event: Dict[str, Any]) -> None:
        sockets = list(self._connections.get(user_id, set()))
        if not sockets:
            return
        payload = json.dumps(jsonable_encoder(event))
        stale: list[WebSocket] = []
        for socket in sockets:
            try:
                await socket.send_text(payload)
            except Exception:
                stale.append(socket)
        for socket in stale:
            self.disconnect(user_id, socket)

    async def send_to_users(self, user_ids: List[int], event: Dict[str, Any]) -> None:
        for user_id in set(user_ids):
            await self.send_to_user(user_id, event)


def _get_redis() -> Optional[redis_lib.Redis]:
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            _redis_client = redis_lib.from_url(redis_url, socket_connect_timeout=2)
            _redis_client.ping()
        except Exception:
            _redis_client = None
    return _redis_client


def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_patient_for_user(db: Session, user_id: int):
    """Return Patient for given user_id or None."""
    return db.query(Patient).filter(Patient.user_id == user_id).first()


def get_current_user(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Get current authenticated user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def write_audit_log(
    db: Session,
    *,
    actor_user_id: Optional[int],
    action: str,
    resource_type: str,
    resource_id: Optional[Any] = None,
    patient_id: Optional[int] = None,
    doctor_id: Optional[int] = None,
    actor_role: Optional[str] = None,
    status: str = "success",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Record a low-PII audit event without committing the transaction."""
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            patient_id=patient_id,
            doctor_id=doctor_id,
            status=status,
            metadata_json=metadata or None,
        )
    )



_redis_client = None
consultation_ws_manager = ConsultationConnectionManager()
