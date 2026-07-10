__all__ = ['_build_positive_trend_notes', '_build_deterministic_advice', '_is_low_signal_advice', '_build_doctor_chat_context', '_summarize_patient_metrics_for_ai', '_trim_chat_context', '_openai_chat_completion', '_openai_chat_completion_with_history', '_openai_chat_with_tools', 'ChatSessionCreate', 'ChatSessionItem', 'ChatSessionMessageItem', 'AdviceRequest', 'AdviceMetric', 'AdviceResponse', 'list_chat_sessions', 'create_chat_session', 'get_session_messages', 'delete_chat_session', 'PatientMemoryItem', 'list_patient_memory', 'delete_patient_memory', 'get_advice']

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
    Subscription,
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

def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _normal_distance(value: float, ref_min: Optional[float], ref_max: Optional[float]) -> Optional[float]:
    if ref_min is None and ref_max is None:
        return None
    if ref_min is not None and value < ref_min:
        return ref_min - value
    if ref_max is not None and value > ref_max:
        return value - ref_max
    return 0.0


def _value_with_unit(value: float, unit: str) -> str:
    return f"{_fmt_num(value)}{f' {unit}' if unit else ''}"


def _build_positive_trend_notes(metrics_summary: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    """Return patient-friendly Spanish notes for metrics moving toward range."""
    notes: List[str] = []
    for name, values in metrics_summary.items():
        numeric_values = [
            item for item in values
            if _as_float(item.get("value")) is not None
        ]
        if len(numeric_values) < 2:
            continue

        latest = numeric_values[0]
        previous = numeric_values[1]
        latest_value = _as_float(latest.get("value"))
        previous_value = _as_float(previous.get("value"))
        if latest_value is None or previous_value is None:
            continue

        ref_min = _as_float(latest.get("ref_min"))
        ref_max = _as_float(latest.get("ref_max"))
        previous_distance = _normal_distance(previous_value, ref_min, ref_max)
        latest_distance = _normal_distance(latest_value, ref_min, ref_max)
        if previous_distance is None or latest_distance is None:
            continue

        tolerance = max(abs(previous_value) * 0.005, 0.01)
        if previous_distance <= latest_distance + tolerance:
            continue

        unit = str(latest.get("unit") or "")
        previous_label = _value_with_unit(previous_value, unit)
        latest_label = _value_with_unit(latest_value, unit)

        if latest_distance == 0:
            notes.append(
                f"Buen progreso: {name} mejoró de {previous_label} a {latest_label} "
                "y ahora está dentro del rango de referencia. Reconoce ese avance y anima a mantener los hábitos que ayudaron."
            )
        else:
            notes.append(
                f"Buena señal: {name} mejoró de {previous_label} a {latest_label} "
                "y se está acercando al rango de referencia. Anima a seguir así, sin prometer resultados."
            )

    return notes[:3]


def _build_deterministic_advice(
    metrics_summary: Dict[str, List[Dict[str, Any]]],
    language: str,
    days: int,
) -> str:
    lang = (language or "es").lower()
    is_es = lang.startswith("es")

    flattened: list[tuple[str, Dict[str, Any]]] = []
    for name, values in metrics_summary.items():
        if not values:
            continue
        flattened.append((name, values[0]))

    def _ts(item: tuple[str, Dict[str, Any]]) -> str:
        return str(item[1].get("t") or "")

    flattened.sort(key=_ts, reverse=True)
    total = len(flattened)
    latest_date = _short_iso_date(flattened[0][1].get("t")) if flattened else "-"

    abnormal: list[tuple[str, Dict[str, Any], str]] = []
    normal: list[tuple[str, Dict[str, Any], str]] = []
    no_ref: list[tuple[str, Dict[str, Any], str]] = []
    for name, _latest in flattened:
        status = _classify_metric_latest_status(metrics_summary.get(name, []))
        row = (name, metrics_summary[name][0], status)
        if status in {"low", "high"}:
            abnormal.append(row)
        elif status == "normal":
            normal.append(row)
        else:
            no_ref.append(row)

    focus = (abnormal + normal + no_ref)[:3]
    positive_trend_notes = _build_positive_trend_notes(metrics_summary)

    if is_es:
        lines = [
            "Resumen rápido de tus resultados recientes (sin diagnóstico médico):",
            f"- Métricas revisadas: {total} (últimos {days} días).",
            f"- Fuera de rango: {len(abnormal)}.",
            f"- Fecha más reciente: {latest_date}.",
            "",
            "Hallazgos clave:",
        ]
        if focus:
            for name, latest, status in focus:
                value = latest.get("value")
                value_text = str(latest.get("value_text") or "").strip()
                unit = latest.get("unit") or ""
                if value is not None:
                    value_label = f"{_fmt_num(float(value))}{f' {unit}' if unit else ''}"
                else:
                    value_label = value_text or "-"
                min_v = latest.get("ref_min")
                max_v = latest.get("ref_max")
                if min_v is not None and max_v is not None:
                    ref_label = f"{_fmt_num(float(min_v))}-{_fmt_num(float(max_v))}"
                elif max_v is not None:
                    ref_label = f"< {_fmt_num(float(max_v))}"
                elif min_v is not None:
                    ref_label = f"> {_fmt_num(float(min_v))}"
                else:
                    ref_label = "sin referencia"

                status_label = {
                    "low": "bajo",
                    "high": "alto",
                    "normal": "normal",
                    "no_ref": "sin referencia",
                    "text": "resultado textual",
                    "unknown": "sin referencia",
                }.get(status, "sin referencia")
                lines.append(f"- {name}: {value_label} ({status_label}; ref {ref_label})")
        else:
            lines.append("- No hay suficientes métricas para resumir.")

        if positive_trend_notes:
            lines.extend(["", "Avance positivo:"])
            lines.extend(f"- {note}" for note in positive_trend_notes)

        lines.extend(
            [
                "",
                "Para comentar con tu médico:",
                "- ¿Qué 2-3 métricas conviene vigilar con más frecuencia?",
                "- ¿Qué cambios de hábitos priorizar según estos valores?",
                "- ¿Cuándo repetir control para confirmar tendencia?",
            ]
        )
        return "\n".join(lines)

    lines = [
        "Quick summary of your recent results (not a medical diagnosis):",
        f"- Metrics reviewed: {total} (last {days} days).",
        f"- Out-of-range values: {len(abnormal)}.",
        f"- Most recent date: {latest_date}.",
        "",
        "Key findings:",
    ]
    if focus:
        for name, latest, status in focus:
            value = latest.get("value")
            value_text = str(latest.get("value_text") or "").strip()
            unit = latest.get("unit") or ""
            if value is not None:
                value_label = f"{_fmt_num(float(value))}{f' {unit}' if unit else ''}"
            else:
                value_label = value_text or "-"
            min_v = latest.get("ref_min")
            max_v = latest.get("ref_max")
            if min_v is not None and max_v is not None:
                ref_label = f"{_fmt_num(float(min_v))}-{_fmt_num(float(max_v))}"
            elif max_v is not None:
                ref_label = f"< {_fmt_num(float(max_v))}"
            elif min_v is not None:
                ref_label = f"> {_fmt_num(float(min_v))}"
            else:
                ref_label = "no reference"

            status_label = {
                "low": "low",
                "high": "high",
                "normal": "normal",
                "no_ref": "no reference",
                "text": "text result",
                "unknown": "no reference",
            }.get(status, "no reference")
            lines.append(f"- {name}: {value_label} ({status_label}; ref {ref_label})")
    else:
        lines.append("- Not enough metrics to build a useful summary.")

    if positive_trend_notes:
        lines.extend(["", "Positive progress:"])
        lines.extend(f"- {note}" for note in positive_trend_notes)

    lines.extend(
        [
            "",
            "Discuss with your doctor:",
            "- Which 2-3 metrics should be monitored more closely?",
            "- Which lifestyle changes should be prioritized from these values?",
            "- When should labs be repeated to confirm trend direction?",
        ]
    )
    return "\n".join(lines)


def _is_low_signal_advice(answer: str) -> bool:
    text = (answer or "").strip().lower()
    if not text:
        return True
    low_signal_markers = [
        "no es un diagnostico",
        "no es un diagnóstico",
        "consulta siempre a tu medico",
        "consulta siempre a tu médico",
        "not a medical diagnosis",
        "always discuss with your doctor",
    ]
    if len(text) < 140 and any(marker in text for marker in low_signal_markers):
        return True
    return False


def _build_doctor_chat_context(db: Session, patient: Patient) -> Dict[str, Any]:
    metrics_summary = _summarize_patient_metrics_for_ai(db, patient, days=36500)
    if metrics_summary:
        latest_dates = [
            str(entry.get("t") or "")
            for entries in metrics_summary.values()
            for entry in entries[:1]
            if entry.get("t")
        ]
        latest_ts = max(latest_dates) if latest_dates else None
        metrics_snapshot = []
        for name, entries in sorted(metrics_summary.items()):
            if not entries:
                continue
            latest = entries[0]
            metrics_snapshot.append(
                {
                    "analyte_key": name,
                    "name": name,
                    "value_num": latest.get("value"),
                    "value_text": latest.get("value_text"),
                    "unit": latest.get("unit"),
                    "ref_min": latest.get("ref_min"),
                    "ref_max": latest.get("ref_max"),
                    "date": latest.get("t"),
                }
            )
            if len(metrics_snapshot) >= 20:
                break

        return {
            "patient": {"id": patient.id, "name": patient.full_name},
            "latest_analysis_date": latest_ts,
            "recent_analyses": [{"date": latest_ts, "source": "v2_documents"}] if latest_ts else [],
            "metrics_snapshot": metrics_snapshot,
            "trends": {},
            "egfr": None,
        }

    results = db.query(LabResult).filter(LabResult.patient_id == patient.id).all()
    results.sort(
        key=lambda r: (r.taken_at or r.created_at or dt.datetime.min),
        reverse=True,
    )

    if not results:
        return {
            "patient": {"id": patient.id, "name": patient.full_name},
            "latest_analysis_date": None,
            "recent_analyses": [],
            "metrics_snapshot": [],
            "trends": {},
            "egfr": None,
        }

    latest_ts = results[0].taken_at or results[0].created_at

    recent_analyses: List[Dict[str, Any]] = []
    seen_sources = set()
    for r in results:
        source = r.source_pdf or "unknown"
        if source in seen_sources:
            continue
        seen_sources.add(source)
        ts = r.taken_at or r.created_at
        recent_analyses.append(
            {
                "date": ts.isoformat() if ts else None,
                "source": source,
            }
        )
        if len(recent_analyses) >= 8:
            break

    metrics_snapshot: List[Dict[str, Any]] = []
    seen_metrics = set()
    for r in results:
        name_norm = normalize_analyte_name(r.analyte_name)
        if not name_norm or name_norm in seen_metrics:
            continue
        seen_metrics.add(name_norm)
        ts = r.taken_at or r.created_at
        metrics_snapshot.append(
            {
                "analyte_key": name_norm,
                "name": name_norm,
                "value_num": r.value,
                "value_text": r.value_text,
                "unit": r.unit,
                "ref_min": r.ref_min,
                "ref_max": r.ref_max,
                "date": ts.isoformat() if ts else None,
            }
        )
        if len(metrics_snapshot) >= 20:
            break

    key_tokens = [
        "CREATININA",
        "UREA",
        "BUN",
        "TFG",
        "EGFR",
        "FILTRACION",
        "ALBUMINA",
        "GLUCOSA",
        "COLESTEROL",
        "TRIGLICERIDOS",
        "CRP",
        "PCR",
        "HEMOGLOBINA",
        "PLAQUETAS",
        "POTASIO",
        "SODIO",
    ]
    normalized_names = sorted(seen_metrics)
    key_metric_names = [
        name for name in normalized_names if any(token in name for token in key_tokens)
    ][:12]
    trends = _summarize_metrics(db, patient.id, metric_names=key_metric_names, days=365) if key_metric_names else {}

    egfr_info = None
    for r in results:
        name_norm = normalize_analyte_name(r.analyte_name)
        stage, label = _derive_egfr_stage_label(name_norm, r.unit, r.value)
        if stage:
            egfr_info = {
                "latest_value": r.value,
                "stage": stage,
                "stage_label": label,
            }
            break

    return {
        "patient": {"id": patient.id, "name": patient.full_name},
        "latest_analysis_date": latest_ts.isoformat() if latest_ts else None,
        "recent_analyses": recent_analyses,
        "metrics_snapshot": metrics_snapshot,
        "trends": trends,
        "egfr": egfr_info,
    }


def _summarize_patient_metrics_for_ai(db: Session, patient: Patient, days: int = 180) -> Dict[str, List[Dict[str, Any]]]:
    """Collect the same lab context used by the patient AI chat for a granted patient."""
    metrics_summary = _summarize_metrics_v2(db, user_id=patient.user_id, metric_names=None, days=days)
    if not metrics_summary:
        metrics_summary = _summarize_metrics(db, patient_id=patient.id, metric_names=None, days=days)
    if not metrics_summary and days < 36500:
        metrics_summary = _summarize_metrics_v2(db, user_id=patient.user_id, metric_names=None, days=36500)
    if not metrics_summary and days < 36500:
        metrics_summary = _summarize_metrics(db, patient_id=patient.id, metric_names=None, days=36500)
    return metrics_summary


def _trim_chat_context(context: Dict[str, Any], max_chars: int = 12000) -> Dict[str, Any]:
    serialized = json.dumps(context, ensure_ascii=False)
    if len(serialized) <= max_chars:
        return context

    trimmed = dict(context)
    trimmed["metrics_snapshot"] = (context.get("metrics_snapshot") or [])[:10]
    trimmed["recent_analyses"] = (context.get("recent_analyses") or [])[:5]
    trimmed["trends"] = {}
    serialized = json.dumps(trimmed, ensure_ascii=False)
    if len(serialized) <= max_chars:
        return trimmed

    trimmed["metrics_snapshot"] = (context.get("metrics_snapshot") or [])[:6]
    return trimmed


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
    base_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
    }

    preferred_token_param = "max_tokens"
    model_lc = model.lower()
    if model_lc.startswith(("gpt-5", "o1", "o3", "o4")):
        preferred_token_param = "max_completion_tokens"
    token_params = [preferred_token_param, "max_completion_tokens", "max_tokens"]

    resp = None
    last_error_text = ""
    for token_param in dict.fromkeys(token_params):
        payload = dict(base_payload)
        payload[token_param] = 800
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
        if resp.status_code < 400:
            break

        last_error_text = resp.text
        error_text_lc = last_error_text.lower()
        can_retry_with_other_param = (
            resp.status_code == 400
            and (
                "max_tokens" in error_text_lc
                or "max_completion_tokens" in error_text_lc
            )
        )
        if not can_retry_with_other_param:
            raise HTTPException(status_code=502, detail=f"OpenAI error: {last_error_text}")

    if resp is None or resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"OpenAI error: {last_error_text}")

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, str):
                    chunks.append(item)
                    continue
                if not isinstance(item, dict):
                    continue
                text_value = item.get("text")
                if isinstance(text_value, str):
                    chunks.append(text_value)
                    continue
                if isinstance(text_value, dict):
                    nested_value = text_value.get("value")
                    if isinstance(nested_value, str):
                        chunks.append(nested_value)
            return "\n".join(part for part in chunks if part).strip()
        return str(content)
    except Exception:
        raise HTTPException(status_code=502, detail="Malformed response from OpenAI.")


def _openai_chat_completion_with_history(system_prompt: str, messages: list[dict]) -> str:
    """Call OpenAI chat completion with a full messages list.

    `messages` is a list of {role, content} dicts in chronological order.
    Uses same retry logic as _openai_chat_completion.
    """
    key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    if not key:
        raise HTTPException(status_code=500, detail="OpenAI API key is missing.")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    base_payload = {"model": model, "messages": full_messages, "temperature": 0.4}

    preferred_token_param = "max_tokens"
    model_lc = model.lower()
    if model_lc.startswith(("gpt-5", "o1", "o3", "o4")):
        preferred_token_param = "max_completion_tokens"
    token_params = [preferred_token_param, "max_completion_tokens", "max_tokens"]

    resp = None
    last_error_text = ""
    for token_param in dict.fromkeys(token_params):
        payload = dict(base_payload)
        payload[token_param] = 1500
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
        if resp.status_code < 400:
            break
        last_error_text = resp.text
        error_text_lc = last_error_text.lower()
        can_retry = (resp.status_code == 400 and
                     ("max_tokens" in error_text_lc or "max_completion_tokens" in error_text_lc))
        if not can_retry:
            raise HTTPException(status_code=502, detail=f"OpenAI error: {last_error_text}")

    if resp is None or resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"OpenAI error: {last_error_text}")

    data = resp.json()
    try:
        choice = data["choices"][0]
        content = choice["message"].get("content")
        if not isinstance(content, (str, list)) or not content:
            content = choice["message"].get("refusal") or ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks = [item.get("text", "") if isinstance(item, dict) else str(item) for item in content]
            return "\n".join(c for c in chunks if c).strip()
        return str(content)
    except Exception:
        raise HTTPException(status_code=502, detail="Malformed response from OpenAI.")


def _openai_chat_with_tools(
    system_prompt: str,
    messages: list[dict],
    metrics_summary: dict,
) -> str:
    """Call OpenAI with Function Calling so the AI can request metric details.

    The AI receives a compact one-line summary of every metric and may call
    get_metric_details(metric_names) to get full time-series data for specific
    analytes.  We loop up to 3 times to handle chained tool calls, then force
    a final answer.
    """
    key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    if not key:
        raise HTTPException(status_code=500, detail="OpenAI API key is missing.")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_metric_details",
                "description": (
                    "Obtiene los datos históricos completos (todas las mediciones recientes) "
                    "de una o varias métricas de laboratorio. Úsalo cuando necesites analizar "
                    "la tendencia o el detalle de analitos específicos."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "metric_names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Lista de claves de analito en mayúsculas "
                                "(ej: [\"CREATININE\", \"UREA\", \"POTASSIUM\"])"
                            ),
                        }
                    },
                    "required": ["metric_names"],
                },
            },
        }
    ]

    model_lc = model.lower()
    token_param = "max_completion_tokens" if model_lc.startswith(("gpt-5", "o1", "o3", "o4")) else "max_tokens"

    # Build a case-insensitive lookup so the AI can match even if case differs
    metrics_upper = {k.upper(): v for k, v in metrics_summary.items()}

    current_messages = [{"role": "system", "content": system_prompt}] + list(messages)

    for _ in range(3):
        payload = {
            "model": model,
            "messages": current_messages,
            token_param: 1500,
            "temperature": 0.4,
            "tools": tools,
            "tool_choice": "auto",
        }
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
        if resp.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"OpenAI error: {resp.text}")

        data = resp.json()
        choice = data["choices"][0]
        message = choice["message"]
        finish_reason = choice.get("finish_reason")

        current_messages.append(message)

        if finish_reason != "tool_calls":
            content = message.get("content") or ""
            if isinstance(content, list):
                content = "\n".join(
                    item.get("text", "") if isinstance(item, dict) else str(item)
                    for item in content
                )
            return content.strip()

        for tc in message.get("tool_calls", []):
            fn_name = tc["function"]["name"]
            fn_args = json.loads(tc["function"]["arguments"])

            if fn_name == "get_metric_details":
                requested = [str(n).strip().upper() for n in fn_args.get("metric_names", [])]
                result = {k: metrics_upper[k] for k in requested if k in metrics_upper}
                result_str = json.dumps(result, ensure_ascii=False)
            else:
                result_str = json.dumps({"error": f"Unknown function: {fn_name}"})

            current_messages.append(
                {"role": "tool", "tool_call_id": tc["id"], "content": result_str}
            )

    # Max iterations reached — force a final answer without tools
    payload_final = {
        "model": model,
        "messages": current_messages,
        token_param: 1500,
        "temperature": 0.4,
        "tools": tools,
        "tool_choice": "none",
    }
    resp = requests.post(url, headers=headers, data=json.dumps(payload_final), timeout=120)
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"OpenAI error: {resp.text}")
    content = resp.json()["choices"][0]["message"].get("content") or ""
    return content.strip()


class ChatSessionCreate(BaseModel):
    title: Optional[str] = None


class ChatSessionItem(BaseModel):
    id: int
    title: Optional[str]
    updated_at: Optional[str]
    preview: Optional[str] = None


class ChatSessionMessageItem(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


class AdviceRequest(BaseModel):
    question: str
    metric_names: Optional[List[str]] = None
    days: Optional[int] = 180
    language: Optional[str] = None
    session_id: Optional[int] = None
    persist: bool = True


class AdviceMetric(BaseModel):
    name: str
    value: Optional[float] = None
    unit: Optional[str] = None


class AdviceResponse(BaseModel):
    answer: str
    usedMetrics: List[AdviceMetric]
    disclaimer: bool = True
    session_id: Optional[int] = None


@router.get("/api/chat/sessions", response_model=List[ChatSessionItem])
async def list_chat_sessions(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id, ChatSession.is_archived == False)
        .filter(~ChatSession.title.like("Dame un breve análisis del estado actual%"))
        .filter(~ChatSession.title.like("Dame un breve analisis del estado actual%"))
        .order_by(ChatSession.updated_at.desc())
        .limit(50)
        .all()
    )
    result = []
    for s in sessions:
        last_msg = (
            db.query(ChatMessageRecord)
            .filter(ChatMessageRecord.session_id == s.id)
            .order_by(ChatMessageRecord.created_at.desc())
            .first()
        )
        result.append(ChatSessionItem(
            id=s.id,
            title=s.title,
            updated_at=s.updated_at.isoformat() if s.updated_at else None,
            preview=(last_msg.content[:80] if last_msg else None),
        ))
    return result


@router.post("/api/chat/sessions", response_model=ChatSessionItem)
async def create_chat_session(
    body: ChatSessionCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    session = ChatSession(user_id=user_id, title=body.title or "")
    db.add(session)
    db.flush()  # assign id + defaults without closing the connection
    session_id = session.id
    session_title = session.title
    session_updated_at = session.updated_at
    db.commit()
    return ChatSessionItem(
        id=session_id,
        title=session_title,
        updated_at=session_updated_at.isoformat() if session_updated_at else None,
    )


@router.get("/api/chat/sessions/{session_id}/messages", response_model=List[ChatSessionMessageItem])
async def get_session_messages(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id, ChatSession.user_id == user_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    msgs = (
        db.query(ChatMessageRecord)
        .filter(ChatMessageRecord.session_id == session_id)
        .order_by(ChatMessageRecord.created_at.asc())
        .all()
    )
    return [ChatSessionMessageItem(
        id=m.id, role=m.role, content=m.content,
        created_at=m.created_at.isoformat(),
    ) for m in msgs]


@router.delete("/api/chat/sessions/{session_id}")
async def delete_chat_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id, ChatSession.user_id == user_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.query(ChatMessageRecord).filter(ChatMessageRecord.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"deleted": session_id}


class PatientMemoryItem(BaseModel):
    id: int
    fact: str
    category: str
    created_at: str


@router.get("/api/chat/memory", response_model=List[PatientMemoryItem])
async def list_patient_memory(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    facts = (
        db.query(PatientMemory)
        .filter(PatientMemory.user_id == user_id)
        .order_by(PatientMemory.created_at.desc())
        .all()
    )
    return [PatientMemoryItem(id=f.id, fact=f.fact, category=f.category,
                              created_at=f.created_at.isoformat()) for f in facts]


@router.delete("/api/chat/memory/{memory_id}")
async def delete_patient_memory(
    memory_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    mem = db.query(PatientMemory).filter(
        PatientMemory.id == memory_id, PatientMemory.user_id == user_id
    ).first()
    if not mem:
        raise HTTPException(status_code=404, detail="Memory fact not found")
    db.delete(mem)
    db.commit()
    return {"deleted": memory_id}


@router.post("/api/advice", response_model=AdviceResponse)
async def get_advice(
    req: AdviceRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Generate wellness-style advice based on recent labs with conversation memory."""
    current_user = db.query(User).filter(User.id == user_id).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
    active_subscription = (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id, Subscription.status.in_(("active", "trialing")))
        .first()
    )
    if not active_subscription:
        raise HTTPException(status_code=403, detail="Se requiere una suscripción activa para usar el chat de IA.")

    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    days = req.days or 180
    should_persist = bool(req.persist)

    # ── 1. Session management ──────────────────────────────────────────────
    if should_persist and req.session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == req.session_id,
            ChatSession.user_id == user_id,
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
    elif should_persist:
        session = ChatSession(user_id=user_id, title="")
        db.add(session)
        db.commit()
        db.refresh(session)
    else:
        session = None

    # ── 2. Save user message ───────────────────────────────────────────────
    if should_persist and session is not None:
        db.add(ChatMessageRecord(session_id=session.id, role="user", content=req.question))
        db.commit()

    # ── 3. Load conversation history (last 10 messages) ───────────────────
    if should_persist and session is not None:
        history_records = (
            db.query(ChatMessageRecord)
            .filter(ChatMessageRecord.session_id == session.id)
            .order_by(ChatMessageRecord.created_at.asc())
            .limit(10)
            .all()
        )
        history_messages = [{"role": m.role, "content": m.content} for m in history_records]
    else:
        history_messages = []

    # ── 4. Patient memory ─────────────────────────────────────────────────
    memory_facts = (
        db.query(PatientMemory)
        .filter(PatientMemory.user_id == user_id)
        .order_by(PatientMemory.created_at.desc())
        .limit(20)
        .all()
    )
    if memory_facts:
        memory_lines = [f"- [{f.category}] {f.fact}" for f in memory_facts]
        patient_memory_text = "\n".join(memory_lines)
    else:
        patient_memory_text = "Aún no tienes información guardada sobre este paciente."

    # ── 5. Analyte snapshot (Redis cache) ─────────────────────────────────
    requested_metric_names = req.metric_names or None
    cache_key = f"analyte_snapshot:{user_id}"
    use_snapshot_cache = not requested_metric_names
    r = _get_redis()
    metrics_summary = None
    if r and use_snapshot_cache:
        try:
            cached = r.get(cache_key)
            if cached:
                metrics_summary = json.loads(cached)
        except Exception:
            pass

    if metrics_summary is None:
        metrics_summary = _summarize_metrics_v2(db, user_id=user_id, metric_names=requested_metric_names, days=days)
        if not metrics_summary and patient:
            metrics_summary = _summarize_metrics(db, patient_id=patient.id, metric_names=requested_metric_names, days=days)
        if not metrics_summary and requested_metric_names:
            metrics_summary = _summarize_metrics_v2(db, user_id=user_id, metric_names=None, days=days)
            if not metrics_summary and patient:
                metrics_summary = _summarize_metrics(db, patient_id=patient.id, metric_names=None, days=days)
        if not metrics_summary:
            metrics_summary = _summarize_metrics_v2(db, user_id=user_id, metric_names=None, days=36500)
        if not metrics_summary and patient:
            metrics_summary = _summarize_metrics(db, patient_id=patient.id, metric_names=None, days=36500)
        if r and use_snapshot_cache and metrics_summary:
            try:
                r.setex(cache_key, 3 * 3600, json.dumps(metrics_summary, ensure_ascii=False))
            except Exception:
                pass

    if not metrics_summary:
        raise HTTPException(status_code=400, detail="No lab data available for advice.")
    write_audit_log(
        db,
        actor_user_id=user_id,
        actor_role="patient",
        action="patient_ai_context_built",
        resource_type="chat_session",
        resource_id=session.id if session is not None else None,
        patient_id=patient.id if patient else None,
        metadata={
            "metrics_count": len(metrics_summary),
            "days": days,
            "memory_count": len(memory_facts),
            "session_id": session.id if session is not None else None,
            "persist": should_persist,
        },
    )

    # ── 5b. Build compact summary of ALL metrics for Function Calling ──────
    compact_summary = _build_compact_metrics_summary(metrics_summary)
    positive_trend_notes = _build_positive_trend_notes(metrics_summary)

    # ── 6. Doctor notes ───────────────────────────────────────────────────
    v2_notes = (
        db.query(V2DoctorNote)
        .filter(V2DoctorNote.patient_user_id == user_id, V2DoctorNote.visibility == "patient")
        .order_by(V2DoctorNote.updated_at.desc())
        .limit(5)
        .all()
    )
    notes_lines = []
    for n in v2_notes:
        meta = " · ".join(p for p in [n.analyte_key or "", n.t.isoformat() if n.t else ""] if p)
        notes_lines.append(f"- [{meta}] {n.note}" if meta else f"- {n.note}")
    if patient:
        legacy_notes = (
            db.query(DoctorNote)
            .filter(DoctorNote.patient_id == patient.id)
            .order_by(DoctorNote.created_at.desc())
            .limit(3)
            .all()
        )
        for n in legacy_notes:
            meta_parts = [p for p in [n.metric_name or "", n.metric_time or ""] if p]
            prefix = f"[{' · '.join(meta_parts)}] " if meta_parts else ""
            notes_lines.append(f"- {prefix}{n.text}")

    # ── 7. Build prompts ──────────────────────────────────────────────────
    patient_name = current_user.full_name or "el paciente"
    system_prompt = (
        f"Eres NephroAI, un asistente personal de salud especializado en nefrología y "
        f"nutrición renal. Acompañas al paciente {patient_name} en el seguimiento de sus "
        f"análisis de laboratorio.\n\n"
        "No eres médico, no diagnosticas ni prescribes medicamentos. Pero sí puedes:\n"
        "- Explicar qué significan sus valores de laboratorio en lenguaje sencillo\n"
        "- Dar consejos prácticos de alimentación y estilo de vida\n"
        "- Recordar lo que el paciente ha compartido contigo antes\n"
        "- Notar mejoras o cambios en sus tendencias\n\n"
        "Cuando detectes una mejora real hacia el rango de referencia, incluye una frase breve de ánimo "
        "y refuerzo positivo (por ejemplo: \"Buen progreso\", \"sigue así\"), sin exagerar ni prometer resultados.\n\n"
        "Adapta tu tono y formato según el tipo de pregunta:\n"
        "- Pregunta simple o conversacional → respuesta corta y directa, sin estructura rígida\n"
        "- Pregunta de revisión general → usa estructura clara con puntos clave\n"
        "- Conversación continua → tono cercano, usa el nombre del paciente cuando sea natural\n\n"
        f"Lo que recuerdas del paciente:\n{patient_memory_text}\n\n"
        "Siempre responde en español."
    )

    # ── 6b. Blood pressure readings ───────────────────────────────────────
    bp_records = (
        db.query(BloodPressure)
        .filter(BloodPressure.user_id == user_id)
        .order_by(BloodPressure.measured_at.desc())
        .limit(10)
        .all()
    )
    if bp_records:
        bp_lines = []
        for r in bp_records:
            date_str = r.measured_at.strftime("%Y-%m-%d %H:%M")
            line = f"- {date_str}: {r.systolic}/{r.diastolic} mmHg"
            if r.pulse:
                line += f", pulso {r.pulse} lpm"
            if r.notes:
                line += f" ({r.notes})"
            bp_lines.append(line)
        bp_text = "\n".join(bp_lines)
    else:
        bp_text = None

    user_prompt_parts = [
        f"Pregunta: {req.question}",
        f"Período considerado: últimos {days} días.",
        "Resumen de todos los análisis disponibles del paciente (usa get_metric_details para obtener el historial completo de cualquier métrica):",
        compact_summary,
    ]
    if positive_trend_notes:
        user_prompt_parts.append("Tendencias positivas detectadas para reforzar con tono motivador:")
        user_prompt_parts.extend(f"- {note}" for note in positive_trend_notes)
    if bp_text:
        user_prompt_parts.append("Registros de presión arterial del paciente (más recientes primero):")
        user_prompt_parts.append(bp_text)
    if notes_lines:
        user_prompt_parts.append("Notas del médico (recientes):")
        user_prompt_parts.extend(notes_lines)
    user_prompt = "\n".join(user_prompt_parts)

    # Replace last history entry's content with enriched user_prompt
    if history_messages and history_messages[-1]["role"] == "user":
        history_messages[-1]["content"] = user_prompt
    else:
        history_messages.append({"role": "user", "content": user_prompt})

    # ── 8. Call OpenAI with Function Calling ──────────────────────────────
    answer = _openai_chat_with_tools(system_prompt, history_messages, metrics_summary)
    if isinstance(answer, str):
        answer = answer.strip()
    if not answer or _is_low_signal_advice(answer):
        answer = _build_deterministic_advice(metrics_summary, "es", days)

    # ── 9. Save assistant message ─────────────────────────────────────────
    if should_persist and session is not None:
        db.add(ChatMessageRecord(session_id=session.id, role="assistant", content=answer))
        if not session.title:
            session.title = req.question[:60]
        session.updated_at = dt.datetime.utcnow()
    write_audit_log(
        db,
        actor_user_id=user_id,
        actor_role="patient",
        action="patient_ai_chat_completed",
        resource_type="chat_session",
        resource_id=session.id if session is not None else None,
        patient_id=patient.id if patient else None,
        metadata={
            "metrics_count": len(metrics_summary),
            "reply_chars": len(answer or ""),
            "session_id": session.id if session is not None else None,
            "persist": should_persist,
        },
    )
    db.commit()

    # ── 10. Async memory extraction ───────────────────────────────────────
    from backend.tasks import extract_patient_memory, CELERY_ENABLED as _CELERY_ENABLED
    if should_persist and session is not None:
        if _CELERY_ENABLED:
            extract_patient_memory.delay(session.id, user_id)
        else:
            try:
                from backend.tasks import _run_extract_patient_memory
                _run_extract_patient_memory(session.id, user_id)
            except Exception:
                pass

    # ── 11. Build response ────────────────────────────────────────────────
    used_metrics = [
        AdviceMetric(name=name, value=values[0].get("value"), unit=values[0].get("unit"))
        for name, values in metrics_summary.items()
        if values
    ]
    return AdviceResponse(
        answer=answer,
        usedMetrics=used_metrics,
        disclaimer=True,
        session_id=session.id if session is not None else None,
    )
