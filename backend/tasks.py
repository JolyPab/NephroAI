"""Celery tasks for PDF processing."""

import os
from typing import Optional

from celery import Celery

from database import SessionLocal, UploadStatus, save_import_to_db
from vision_parser import parse_pdf_vision


def _get_redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://redis:6379/0")


celery = Celery("medic", broker=_get_redis_url(), backend=_get_redis_url())
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


@celery.task(name="process_pdf_task")
def process_pdf_task(file_id: int):
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
            import_data = parse_pdf_vision(pdf_bytes)
            import_data.patient_id = status.patient_id
            import_data.source_pdf = os.path.basename(status.file_path)
            save_import_to_db(session, import_data, status.patient_id)
            status.status = "done"
            status.error_message = None
        except Exception as e:
            status.status = "error"
            status.error_message = str(e)
        finally:
            session.commit()
    finally:
        session.close()
