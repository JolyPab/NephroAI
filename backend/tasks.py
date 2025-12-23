"""Background-like tasks for PDF processing."""

import os
from typing import Optional

from database import SessionLocal, UploadStatus, save_import_to_db
from vision_parser import parse_pdf_vision


class _TaskWrapper:
    """Lightweight stub to mimic Celery-style .delay interface."""

    def __init__(self, func):
        self.func = func

    def delay(self, *args, **kwargs):
        return self.func(*args, **kwargs)


def _process_pdf_task(file_id: int):
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


process_pdf_task = _TaskWrapper(_process_pdf_task)
