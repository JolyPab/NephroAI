"""FastAPI application for lab import module."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import io
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from dotenv import load_dotenv
import hashlib

from backend.models import ImportJson
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
    Patient,
    LabResult,
    User,
    Subscription,
    Payment,
    UploadStatus,
    save_parsed_records,
)
from backend.auth import get_current_user_id
from backend.auth_routes import router as auth_router, UserResponse as AuthUserResponse
from backend.patient_routes import router as patient_router
import datetime as dt
import json
import re
import requests
from urllib.parse import urljoin

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


def get_current_user(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Get current authenticated user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Load environment variables from .env file
load_dotenv()

# Database setup
database_url = get_database_url()
engine = create_db_engine(database_url)
SessionLocal = get_session_factory(engine)


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


def _analysis_id(patient_id: int, source: str) -> str:
    """Create analysis id consistent with patient analyses grouping."""
    return f"{patient_id}_{abs(hash(source)) % 10000}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db(engine)
    _ensure_note_columns()
    yield
    # Cleanup if needed


app = FastAPI(
    title="Lab Import API",
    description="API for importing laboratory test results from PDF files",
    version="1.0.0",
    lifespan=lifespan,
)

# Request logging middleware
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        print(f"[DEBUG] {request.method} {request.url.path}")
        print(f"[DEBUG] Headers: {dict(request.headers)}")
        response = await call_next(request)
        print(f"[DEBUG] Response status: {response.status_code}")
        return response

app.add_middleware(LoggingMiddleware)

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

# Include auth routes
app.include_router(auth_router)

# Include patient routes
app.include_router(patient_router)


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


def _openai_chat_completion(system_prompt: str, user_prompt: str):
    """Call OpenAI chat completion."""
    key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o")

    if not key:
        raise HTTPException(status_code=500, detail="OpenAI API key is missing.")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 800,
    }

    resp = requests.post(url, headers=headers, data=json.dumps(payload))
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"OpenAI error: {resp.text}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        raise HTTPException(status_code=502, detail="Malformed response from OpenAI.")


class AdviceRequest(BaseModel):
    question: str
    metric_names: Optional[List[str]] = None
    days: Optional[int] = 180
    language: Optional[str] = None


class AdviceMetric(BaseModel):
    name: str
    value: Optional[float] = None
    unit: Optional[str] = None


class AdviceResponse(BaseModel):
    answer: str
    usedMetrics: List[AdviceMetric]
    disclaimer: bool = True

class SubscriptionStatus(BaseModel):
    active: bool
    status: str
    period_end: Optional[dt.datetime] = None
    subscription_id: Optional[str] = None
    plan_id: Optional[str] = None

class CreateSubscriptionRequest(BaseModel):
    plan_id: Optional[str] = None
    return_url: Optional[str] = None
    cancel_url: Optional[str] = None

class CreateSubscriptionResponse(BaseModel):
    approval_url: str
    subscription_id: Optional[str] = None

# PayPal helpers
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")
PAYPAL_BASE_URL = os.getenv("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com")
PAYPAL_PLAN_ID = os.getenv("PAYPAL_PLAN_ID", "")


def _paypal_get_token() -> str:
    """Fetch OAuth token from PayPal."""
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="PayPal credentials not configured")
    token_url = urljoin(PAYPAL_BASE_URL, "/v1/oauth2/token")
    resp = requests.post(
        token_url,
        headers={"Accept": "application/json", "Accept-Language": "en_US"},
        data={"grant_type": "client_credentials"},
        auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"PayPal token error: {resp.text}")
    return resp.json().get("access_token")


def _paypal_create_subscription(plan_id: str, return_url: str, cancel_url: str) -> dict:
    """Create a PayPal subscription and return response JSON."""
    token = _paypal_get_token()
    sub_url = urljoin(PAYPAL_BASE_URL, "/v1/billing/subscriptions")
    payload = {
        "plan_id": plan_id,
        "application_context": {
            "brand_name": "Medic Insight",
            "user_action": "SUBSCRIBE_NOW",
            "return_url": return_url,
            "cancel_url": cancel_url,
        },
    }
    resp = requests.post(
        sub_url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        data=json.dumps(payload),
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"PayPal create error: {resp.text}")
    return resp.json()


def _paypal_get_subscription(sub_id: str) -> dict:
    token = _paypal_get_token()
    url = urljoin(PAYPAL_BASE_URL, f"/v1/billing/subscriptions/{sub_id}")
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"PayPal fetch error: {resp.text}")
    return resp.json()

class SubscriptionStatus(BaseModel):
    active: bool
    status: str
    period_end: Optional[dt.datetime] = None
    subscription_id: Optional[str] = None
    plan_id: Optional[str] = None

class CreateSubscriptionRequest(BaseModel):
    plan_id: Optional[str] = None
    return_url: Optional[str] = None
    cancel_url: Optional[str] = None

class CreateSubscriptionResponse(BaseModel):
    approval_url: str
    subscription_id: Optional[str] = None

# PayPal helpers
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")
PAYPAL_BASE_URL = os.getenv("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com")
PAYPAL_PLAN_ID = os.getenv("PAYPAL_PLAN_ID", "")


def _paypal_get_token() -> str:
    """Fetch OAuth token from PayPal."""
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="PayPal credentials not configured")
    token_url = urljoin(PAYPAL_BASE_URL, "/v1/oauth2/token")
    resp = requests.post(
        token_url,
        headers={"Accept": "application/json", "Accept-Language": "en_US"},
        data={"grant_type": "client_credentials"},
        auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"PayPal token error: {resp.text}")
    return resp.json().get("access_token")


def _paypal_create_subscription(plan_id: str, return_url: str, cancel_url: str) -> dict:
    """Create a PayPal subscription and return response JSON."""
    token = _paypal_get_token()
    sub_url = urljoin(PAYPAL_BASE_URL, "/v1/billing/subscriptions")
    payload = {
        "plan_id": plan_id,
        "application_context": {
            "brand_name": "Medic Insight",
            "user_action": "SUBSCRIBE_NOW",
            "return_url": return_url,
            "cancel_url": cancel_url,
        },
    }
    resp = requests.post(
        sub_url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        data=json.dumps(payload),
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"PayPal create error: {resp.text}")
    return resp.json()


def _paypal_get_subscription(sub_id: str) -> dict:
    token = _paypal_get_token()
    url = urljoin(PAYPAL_BASE_URL, f"/v1/billing/subscriptions/{sub_id}")
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"PayPal fetch error: {resp.text}")
    return resp.json()


class ShareGrantRequest(BaseModel):
    doctor_email: str


class ShareGrantResponse(BaseModel):
    doctor_email: str
    doctor_id: Optional[int] = None
    doctor_name: Optional[str] = None
    granted_at: dt.datetime
    revoked_at: Optional[dt.datetime] = None


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


class UserUpdate(BaseModel):
    full_name: Optional[str] = None


@app.post("/api/preview", response_model=ImportJson)
async def preview_import(
    file: UploadFile = File(...),
    patient_id: str = Form(...),
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


@app.post("/api/files/pdf")
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
            f.write(pdf_bytes)

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


@app.get("/api/files/status/{upload_id}")
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


@app.post("/api/import")
async def import_lab_results(
    file: UploadFile = File(...),
    patient_id: int = Form(...),
):
    """
    Extract raw text from PDF and save parsed lab results.
    Patient_id must be ID of patient belonging to authenticated user.

    For testing without auth, just pass patient_id.
    For production, add user_id: int = Depends(get_current_user_id) parameter.

    Returns status and number of items imported.
    """
    try:
        # Read PDF file
        pdf_bytes = await file.read()
        
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Verify patient exists (comment out for testing without auth)
        # db_session = SessionLocal()
        # patient = db_session.query(Patient).filter(
        #     Patient.id == patient_id,
        #     Patient.user_id == user_id  # uncomment when using auth
        # ).first()
        # db_session.close()
        # if not patient:
        #     raise HTTPException(status_code=404, detail="Patient not found")
        
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


@app.get("/api/patient/analyses")
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


@app.get("/api/patient/series")
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


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

def _ensure_doctor_access(db: Session, doctor_user: User, patient_id: int) -> Patient:
    """Ensure doctor has an active grant to the patient and return patient."""
    if not doctor_user or not doctor_user.is_doctor:
        raise HTTPException(status_code=403, detail="Not a doctor")
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
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


def _resolve_doctor_user(db: Session, doctor_id: Optional[int], doctor_email: Optional[str]) -> Optional[User]:
    """Helper to fetch doctor user by id or email."""
    doctor_user = None
    if doctor_id:
        doctor_user = db.query(User).filter(User.id == doctor_id).first()
    if not doctor_user and doctor_email:
        doctor_user = db.query(User).filter(User.email.ilike(doctor_email)).first()
    return doctor_user


@app.post("/api/share/grant", response_model=ShareGrantResponse)
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
    else:
        grant = DoctorGrant(
            patient_id=patient.id,
            doctor_email=doctor_email,
            doctor_id=doctor_id,
            granted_at=now,
        )
        db.add(grant)
    db.commit()
    db.refresh(grant)
    doctor_user = _resolve_doctor_user(db, grant.doctor_id, grant.doctor_email)
    return ShareGrantResponse(
        doctor_email=grant.doctor_email,
        doctor_id=grant.doctor_id,
        doctor_name=doctor_user.full_name if doctor_user else doctor_name,
        granted_at=grant.granted_at,
        revoked_at=grant.revoked_at,
    )


@app.get("/api/doctor/patients")
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


@app.get("/api/doctor/patient/{patient_id}/analyses")
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


@app.get("/api/doctor/patient/{patient_id}/series")
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


@app.post("/api/doctor/patient/{patient_id}/notes", response_model=DoctorNoteResponse)
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


@app.get("/api/doctor/patient/{patient_id}/notes", response_model=List[DoctorNoteResponse])
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


@app.get("/api/patient/notes", response_model=List[DoctorNoteResponse])
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


@app.get("/api/share/grants", response_model=List[ShareGrantResponse])
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
                granted_at=g.granted_at,
                revoked_at=g.revoked_at,
            )
        )
    return result


@app.delete("/api/share/revoke/{doctor_email}", response_model=ShareGrantResponse)
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
    db.commit()
    db.refresh(grant)
    doctor_user = _resolve_doctor_user(db, grant.doctor_id, grant.doctor_email)
    return ShareGrantResponse(
        doctor_email=grant.doctor_email,
        doctor_id=grant.doctor_id,
        doctor_name=doctor_user.full_name if doctor_user else None,
        granted_at=grant.granted_at,
        revoked_at=grant.revoked_at,
    )

@app.post("/api/advice", response_model=AdviceResponse)
async def get_advice(
    req: AdviceRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Generate wellness-style advice based on recent labs using Azure OpenAI."""
    current_user = db.query(User).filter(User.id == user_id).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    days = req.days or 180
    metrics_summary = _summarize_metrics(
        db,
        patient_id=patient.id,
        metric_names=req.metric_names,
        days=days,
    )

    if not metrics_summary:
        raise HTTPException(status_code=400, detail="No lab data available for advice.")

    language = req.language or "es"

    # Pull latest doctor notes for context
    notes = (
        db.query(DoctorNote)
        .filter(DoctorNote.patient_id == patient.id)
        .order_by(DoctorNote.created_at.desc())
        .limit(5)
        .all()
    )
    notes_lines = []
    for n in notes:
        meta_parts = []
        if n.metric_name:
            meta_parts.append(n.metric_name)
        if n.metric_time:
            meta_parts.append(n.metric_time)
        elif n.created_at:
            meta_parts.append(n.created_at.isoformat())
        prefix = f"[{' · '.join(meta_parts)}] " if meta_parts else ""
        notes_lines.append(f"- {prefix}{n.text}")
    notes_text = "\n".join(notes_lines) if notes_lines else ""

    system_prompt = (
        "Eres un asistente de un nefrólogo y dietólogo experto en problemas renales y enfermedad renal crónica. "
        "No eres el médico del paciente y no das diagnósticos ni prescribes fármacos. "
        "Ofreces consejos generales de bienestar, alimentación y hábitos, y sugieres consultar a su médico. "
        "Responde en el idioma solicitado, sé breve y práctico. Usa solo los datos de laboratorio proporcionados."
    )

    metrics_text = json.dumps(metrics_summary, ensure_ascii=False, indent=2)
    parts = [
        f"Idioma de respuesta: {language}",
        f"Pregunta del usuario: {req.question}",
        f"Periodo considerado: últimos {days} días.",
        "Datos de laboratorio recientes (hasta 5 puntos por métrica):",
        metrics_text,
    ]
    if notes_text:
        parts.append("Notas del médico (recientes):")
        parts.append(notes_text)
    parts.append(
        "Instrucciones: responde de forma concisa, con puntos claros. "
        "Si algún valor está fuera de rango, menciónalo brevemente y da consejos generales de estilo de vida/alimentación. "
        "No hagas diagnósticos ni ajustes de medicación."
    )
    user_prompt = "\n".join(parts)

    answer = _openai_chat_completion(system_prompt, user_prompt)

    used_metrics = [
        AdviceMetric(name=name, value=values[0].get("value"), unit=values[0].get("unit"))
        for name, values in metrics_summary.items()
        if values
    ]

    return AdviceResponse(
        answer=answer,
        usedMetrics=used_metrics,
        disclaimer=True,
    )


@app.get("/api/me")
async def get_me_shortcut(user_id: int = Depends(get_current_user_id)):
    """Shortcut for /api/auth/me (frontend compatibility)."""
    print(f"[DEBUG] GET /api/me called for user_id={user_id}")
    
    db = SessionLocal()
    try:
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
    finally:
        db.close()


@app.get("/api/billing/status", response_model=SubscriptionStatus)
async def billing_status(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Return subscription status for current user."""
    sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id)
        .order_by(Subscription.updated_at.desc())
        .first()
    )
    if not sub:
        return SubscriptionStatus(active=False, status="inactive")
    active = sub.status == "active" and (sub.period_end is None or sub.period_end > dt.datetime.utcnow())
    return SubscriptionStatus(
        active=active,
        status=sub.status,
        period_end=sub.period_end,
        subscription_id=sub.paypal_subscription_id,
        plan_id=sub.plan_id,
    )


@app.post("/api/billing/paypal/create", response_model=CreateSubscriptionResponse)
async def billing_create(
    req: CreateSubscriptionRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Create PayPal subscription and return approval URL."""
    plan_id = req.plan_id or PAYPAL_PLAN_ID
    if not plan_id:
        raise HTTPException(status_code=500, detail="PayPal plan_id not configured")
    # Fallback return/cancel URLs (frontend should pass its own)
    base_app_url = os.getenv("APP_URL", "http://localhost:4200")
    return_url = req.return_url or f"{base_app_url}/billing/return"
    cancel_url = req.cancel_url or f"{base_app_url}/billing/cancel"

    data = _paypal_create_subscription(plan_id, return_url, cancel_url)
    approval_url = ""
    sub_id = data.get("id")
    for link in data.get("links", []):
        if link.get("rel") == "approve":
            approval_url = link.get("href")
            break
    if not approval_url:
        raise HTTPException(status_code=502, detail="PayPal approval URL not found")

    # Create or update local subscription record
    sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id)
        .first()
    )
    now = dt.datetime.utcnow()
    if sub:
        sub.status = "pending"
        sub.plan_id = plan_id
        sub.paypal_subscription_id = sub_id
        sub.updated_at = now
    else:
        sub = Subscription(
            user_id=user_id,
            status="pending",
            plan_id=plan_id,
            paypal_subscription_id=sub_id,
            created_at=now,
            updated_at=now,
        )
        db.add(sub)
    db.commit()

    return CreateSubscriptionResponse(approval_url=approval_url, subscription_id=sub_id)


@app.post("/api/billing/paypal/confirm", response_model=SubscriptionStatus)
async def billing_confirm(
    subscription_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Confirm subscription after PayPal redirect."""
    if not subscription_id:
        raise HTTPException(status_code=400, detail="subscription_id required")

    data = _paypal_get_subscription(subscription_id)
    status = (data.get("status") or "").lower()
    now = dt.datetime.utcnow()
    billing_info = data.get("billing_info", {})
    next_billing_time = billing_info.get("next_billing_time")
    period_end = None
    if next_billing_time:
        try:
            period_end = dt.datetime.fromisoformat(next_billing_time.replace("Z", "+00:00"))
        except Exception:
            period_end = None

    sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id)
        .first()
    )
    if not sub:
        sub = Subscription(
            user_id=user_id,
            paypal_subscription_id=subscription_id,
            plan_id=data.get("plan_id"),
            created_at=now,
        )
        db.add(sub)

    sub.status = "active" if status == "active" else status or "pending"
    sub.period_start = now
    sub.period_end = period_end
    sub.updated_at = now
    db.commit()
    db.refresh(sub)

    return SubscriptionStatus(
        active=sub.status == "active",
        status=sub.status,
        period_end=sub.period_end,
        subscription_id=sub.paypal_subscription_id,
        plan_id=sub.plan_id,
    )

@app.patch("/api/me", response_model=AuthUserResponse)
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
        role="DOCTOR" if user.is_doctor else "PATIENT",
    )


@app.get("/")
async def root():
    """API root - redirect to docs."""
    return RedirectResponse(url="/docs")
