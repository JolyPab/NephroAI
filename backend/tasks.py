"""Celery tasks for PDF processing."""

import os
import json
import hashlib
from typing import Optional

try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    Celery = None
    CELERY_AVAILABLE = False

from backend.database import SessionLocal, UploadStatus, save_parsed_records, ChatMessageRecord, PatientMemory
from backend.pdf_parser import extract_raw_text
from backend.parsing.pipeline import coerce_raw_text, parse_with_ocr_fallback




def _get_celery_broker_url() -> Optional[str]:
    return os.getenv("CELERY_BROKER_URL")


def _get_celery_result_backend() -> Optional[str]:
    return os.getenv("CELERY_RESULT_BACKEND") or os.getenv("RESULT_BACKEND")


CELERY_BROKER_URL = _get_celery_broker_url()
CELERY_RESULT_BACKEND = _get_celery_result_backend()
CELERY_CONFIGURED = bool(CELERY_BROKER_URL and CELERY_RESULT_BACKEND)
CELERY_ENABLED = CELERY_AVAILABLE and CELERY_CONFIGURED

if CELERY_ENABLED:
    celery = Celery(
        "medic",
        broker=CELERY_BROKER_URL,
        backend=CELERY_RESULT_BACKEND,
    )
    celery.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
    )
else:
    celery = None


def _run_process_pdf_task(file_id: int):
    """Process a saved PDF by UploadStatus id."""
    session = SessionLocal()
    try:
        status: Optional[UploadStatus] = session.query(UploadStatus).get(file_id)
        if not status:
            return

        status.status = "processing"
        status.error_message = None
        session.commit()

        # Read PDF bytes from disk
        try:
            with open(status.file_path, "rb") as f:
                pdf_bytes = f.read()
        except Exception as e:
            status.status = "error"
            status.error_message = f"File read error: {e}"
            session.commit()
            return

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
            document_hash = hashlib.sha256(pdf_bytes).hexdigest()
            file_name = os.path.basename(status.file_path)
            prefix = f"{status.id}_"
            if file_name.startswith(prefix):
                file_name = file_name[len(prefix):]
            save_parsed_records(
                session,
                status.patient_id,
                parse_result["records"],
                file_name,
                document_hash,
            )
            status.status = "done"
            status.error_message = None
        except Exception as e:
            status.status = "error"
            status.error_message = str(e)
        finally:
            session.commit()
    finally:
        session.close()


def _run_extract_patient_memory(session_id: int, user_id: int) -> None:
    """Extract patient facts from the last exchange and save to PatientMemory."""
    from backend.main import _openai_chat_completion  # import here to avoid circular
    session = SessionLocal()
    try:
        msgs = (
            session.query(ChatMessageRecord)
            .filter(ChatMessageRecord.session_id == session_id)
            .order_by(ChatMessageRecord.created_at.desc())
            .limit(2)
            .all()
        )
        if len(msgs) < 2:
            return
        msgs = list(reversed(msgs))
        exchange = f"Paciente: {msgs[0].content}\nAsistente: {msgs[1].content}"

        existing = session.query(PatientMemory).filter(PatientMemory.user_id == user_id).all()
        existing_facts = "\n".join(f"- {m.fact}" for m in existing) if existing else "Ninguno."

        system = "Eres un extractor de hechos médicos. Responde solo con JSON válido."
        user_prompt = (
            f"Analiza este intercambio y extrae hechos nuevos que valga la pena recordar sobre el paciente: "
            f"datos médicos, preferencias, o recomendaciones dadas. "
            f"No dupliques hechos ya existentes.\n\n"
            f"Hechos ya guardados:\n{existing_facts}\n\n"
            f"Intercambio:\n{exchange}\n\n"
            f"Devuelve un JSON array con objetos {{\"fact\": str, \"category\": str}} "
            f"donde category es 'medical', 'preference', o 'recommendation'. "
            f"Si no hay nada nuevo, devuelve []."
        )
        raw = _openai_chat_completion(system, user_prompt)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]
        facts = json.loads(raw.strip())
        if not isinstance(facts, list):
            return
        for item in facts:
            if not isinstance(item, dict):
                continue
            fact = item.get("fact", "").strip()
            category = item.get("category", "medical").strip()
            if not fact or category not in ("medical", "preference", "recommendation"):
                continue
            session.add(PatientMemory(
                user_id=user_id, fact=fact, category=category, source_session_id=session_id
            ))
        session.commit()
    except Exception:
        pass
    finally:
        session.close()


if CELERY_ENABLED:

    @celery.task(name="process_pdf_task")
    def process_pdf_task(file_id: int):
        return _run_process_pdf_task(file_id)

    @celery.task(name="extract_patient_memory")
    def extract_patient_memory(session_id: int, user_id: int):
        return _run_extract_patient_memory(session_id, user_id)

else:

    def _missing_celery() -> None:
        raise RuntimeError(
            "Celery is not configured. Set CELERY_BROKER_URL and CELERY_RESULT_BACKEND or use sync mode."
        )

    class _CeleryTaskStub:
        def delay(self, *args, **kwargs):
            _missing_celery()

        def __call__(self, *args, **kwargs):
            return _run_process_pdf_task(*args, **kwargs)

    class _ExtractMemoryTaskStub:
        def delay(self, *args, **kwargs):
            _missing_celery()

        def __call__(self, *args, **kwargs):
            return _run_extract_patient_memory(*args, **kwargs)

    process_pdf_task = _CeleryTaskStub()
    extract_patient_memory = _ExtractMemoryTaskStub()
