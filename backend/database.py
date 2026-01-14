"""Database models and setup for lab results storage."""

from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING
import os
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    ForeignKey,
    Boolean,
    inspect,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship

from backend.analyte_utils import normalize_analyte_name, analyte_key
# Ensure .env is loaded before reading DB_URL so we don't fall back to SQLite accidentally
load_dotenv()

if TYPE_CHECKING:
    from backend.models import ImportJson

Base = declarative_base()


class User(Base):
    """User model for authentication."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_doctor = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    patients = relationship("Patient", back_populates="user", foreign_keys="Patient.user_id")


class Patient(Base):
    """Patient model linked to User."""
    
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    full_name = Column(String, nullable=False)
    date_of_birth = Column(DateTime, nullable=True)
    gender = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="patients", foreign_keys=[user_id])
    lab_results = relationship("LabResult", back_populates="patient")
    grants = relationship("DoctorGrant", back_populates="patient")
    doctor_notes = relationship("DoctorNote", back_populates="patient")


class LabResult(Base):
    """SQLAlchemy model for lab results table."""
    
    __tablename__ = "lab_results"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    analyte_name = Column(String, nullable=False)
    value = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    material = Column(String, nullable=True)
    taken_at = Column(DateTime, nullable=True)
    ref_range = Column(String, nullable=True)
    ref_min = Column(Float, nullable=True)
    ref_max = Column(Float, nullable=True)
    source_pdf = Column(String, nullable=True)
    value_text = Column(String, nullable=True)
    document_hash = Column(String, nullable=True, index=True)
    series_key = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    patient = relationship("Patient", back_populates="lab_results")


class DoctorGrant(Base):
    """Access grant from patient to doctor (by email)."""

    __tablename__ = "doctor_grants"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    doctor_email = Column(String, nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("Patient", back_populates="grants", foreign_keys=[patient_id])
    doctor = relationship("User", foreign_keys=[doctor_id])


class DoctorNote(Base):
    """Notes left by doctor for a patient."""

    __tablename__ = "doctor_notes"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    metric_name = Column(String, nullable=True, index=True)
    metric_time = Column(String, nullable=True, index=True)  # ISO string of measurement time
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("Patient", back_populates="doctor_notes", foreign_keys=[patient_id])
    doctor = relationship("User", foreign_keys=[doctor_id])


class UploadStatus(Base):
    """Track background PDF processing uploads."""

    __tablename__ = "upload_status"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    file_path = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")  # pending, processing, done, error
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient = relationship("Patient", foreign_keys=[patient_id])

class Subscription(Base):
    """Paid subscription for a user."""

    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="inactive")  # active, canceled, past_due
    plan_id = Column(String, nullable=True)
    paypal_subscription_id = Column(String, nullable=True, unique=True, index=True)
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id])


class Payment(Base):
    """Payment records for subscriptions."""

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True, index=True)
    amount = Column(Float, nullable=True)
    currency = Column(String, nullable=True, default="USD")
    status = Column(String, nullable=False, default="pending")  # pending, completed, failed, refunded
    paypal_payment_id = Column(String, nullable=True, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id])
    subscription = relationship("Subscription", foreign_keys=[subscription_id])


def get_database_url(default_sqlite: Optional[str] = None) -> str:
    """Get database URL from environment or fallback to local SQLite."""
    if default_sqlite is None:
        db_path = (Path(__file__).resolve().parent / "lab_results.db").as_posix()
        default_sqlite = f"sqlite:///{db_path}"
    return (
        os.getenv("DATABASE_URL")
        or os.getenv("DB_URL")
        or default_sqlite
    )


def create_db_engine(database_url: str):
    """Create SQLAlchemy engine."""
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(database_url, connect_args=connect_args)


def get_session_factory(engine):
    """Get session factory for database."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(engine):
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    added_columns = ensure_lab_results_columns(engine)
    if added_columns:
        print(f"[DB] added columns: {', '.join(added_columns)}")


def ensure_lab_results_columns(engine) -> list[str]:
    """Add missing lab_results columns without full migrations."""
    try:
        inspector = inspect(engine)
        if "lab_results" not in inspector.get_table_names():
            return []
        existing = {col["name"] for col in inspector.get_columns("lab_results")}
        additions: list[tuple[str, str]] = []
        if "value_text" not in existing:
            additions.append(("value_text", "TEXT"))
        if "document_hash" not in existing:
            additions.append(("document_hash", "TEXT"))
        if "series_key" not in existing:
            additions.append(("series_key", "TEXT"))
        if "ref_min" not in existing:
            additions.append(("ref_min", "REAL"))
        if "ref_max" not in existing:
            additions.append(("ref_max", "REAL"))

        if not additions:
            return []

        with engine.begin() as conn:
            for name, col_type in additions:
                conn.execute(text(f"ALTER TABLE lab_results ADD COLUMN {name} {col_type}"))
        return [name for name, _ in additions]
    except Exception as exc:
        print(f"[WARN] Could not ensure lab_results columns: {exc}")
        return []


# Create default engine and session factory
_engine = create_db_engine(get_database_url())
SessionLocal = get_session_factory(_engine)


def save_import_to_db(session: Session, import_data: "ImportJson", patient_db_id: int) -> int:
    """
    Save ImportJson to database.
    
    Args:
        session: SQLAlchemy session
        import_data: ImportJson object with items to save
        patient_db_id: Database ID of the patient (int)
        
    Returns:
        Number of items saved
    """
    items_count = 0
    source_pdf = import_data.source_pdf

    def _parse_datetime(value) -> Optional[datetime]:
        """Parse datetime from various inputs; return None on failure."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        # Try dateutil if available
        try:
            from dateutil import parser as date_parser  # type: ignore
        except Exception:
            date_parser = None

        if isinstance(value, str):
            val = value.strip()
            if not val:
                return None
            if date_parser:
                try:
                    return date_parser.parse(val)
                except Exception:
                    pass
            try:
                return datetime.fromisoformat(val)
            except Exception:
                return None
        return None

    junk_names = {
        "RESPONSABLE DE LABORATORIO",
        "RESPONSABLE DE SUCURSAL",
        "OTROS",
        "OTROS:",
    }
    
    def _coerce_float(value) -> Optional[float]:
        """Try to coerce incoming ref_min/ref_max to float, otherwise None."""
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            try:
                return float(str(value).replace(",", "."))
            except Exception:
                return None
    
    # Document-level date (use first item with taken_at if present)
    doc_date = None
    for item in import_data.items:
        parsed_dt = _parse_datetime(item.taken_at)
        if parsed_dt:
            doc_date = parsed_dt
            break
    
    seen = set()

    for item in import_data.items:
        name_clean = normalize_analyte_name(item.analyte_name)
        if not name_clean:
            continue
        if name_clean in junk_names:
            continue

        ref_min = _coerce_float(getattr(item, "ref_min", None))
        ref_max = _coerce_float(getattr(item, "ref_max", None))
        taken_at = _parse_datetime(item.taken_at) or doc_date
        taken_at_iso = taken_at.isoformat() if taken_at else ""

        key = analyte_key(
            name_clean,
            item.value,
            item.value_text,
            item.unit,
            item.material,
            taken_at_iso,
        )
        if key in seen:
            continue
        seen.add(key)

        db_item = LabResult(
            patient_id=patient_db_id,  # Use the actual patient_id from DB
            analyte_name=name_clean,
            value=item.value,
            value_text=item.value_text,
            unit=item.unit,
            material=item.material,
            taken_at=taken_at,
            ref_range=item.ref_range,
            ref_min=ref_min,
            ref_max=ref_max,
            source_pdf=source_pdf,
        )
        session.add(db_item)
        items_count += 1
    
    session.commit()
    return items_count


def _normalize_series_field(value: Optional[str]) -> str:
    if not value:
        return ""
    text_value = str(value).replace("\u00a0", " ").strip()
    if not text_value:
        return ""
    text_value = " ".join(text_value.split()).upper()
    text_value = text_value.rstrip(":").strip()
    return text_value


def build_series_key(record: dict) -> str:
    name = normalize_analyte_name(record.get("test_name_raw"))
    if not name:
        return ""
    specimen = _normalize_series_field(record.get("specimen"))
    section = _normalize_series_field(record.get("section"))
    unit_value = record.get("unit_norm") or record.get("unit_raw") or ""
    unit_value = _normalize_series_field(unit_value)
    return "|".join([name, specimen, unit_value, section])


def save_parsed_records(
    session: Session,
    patient_id: int,
    records: list[dict],
    source_pdf: Optional[str],
    document_hash: Optional[str],
) -> int:
    if not records:
        return 0

    def _coerce_datetime(value) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
            try:
                return datetime(int(value.year), int(value.month), int(value.day))
            except Exception:
                return None
        if isinstance(value, str):
            val = value.strip()
            if not val:
                return None
            try:
                return datetime.fromisoformat(val)
            except Exception:
                return None
        return None

    existing_keys = set()
    if document_hash:
        rows = (
            session.query(
                LabResult.series_key,
                LabResult.value,
                LabResult.value_text,
                LabResult.ref_min,
                LabResult.ref_max,
            )
            .filter(
                LabResult.patient_id == patient_id,
                LabResult.document_hash == document_hash,
            )
            .all()
        )
        for row in rows:
            series_key = row[0]
            if not series_key:
                continue
            if row[1] is not None:
                value_key = ("num", float(row[1]))
            else:
                vt = (row[2] or "").strip() or None
                value_key = ("text", vt)
            existing_keys.add((series_key, value_key, row[3], row[4]))

    inserted = 0
    seen_keys = set()

    for record in records:
        name_clean = normalize_analyte_name(record.get("test_name_raw"))
        if not name_clean:
            continue

        series_key = build_series_key(record)
        if not series_key:
            continue
        unit_value = record.get("unit_norm") or record.get("unit_raw")
        ref_min = record.get("ref_min")
        ref_max = record.get("ref_max")
        if ref_min is not None and ref_max is not None:
            ref_range = f"{ref_min} a {ref_max}"
        else:
            ref_range = None
        value_num = record.get("value_num", None)
        value_text = record.get("value_text") or record.get("value_cat") or record.get("value")
        taken_at = _coerce_datetime(record.get("taken_at"))
        if value_num is not None:
            value_key = ("num", float(value_num))
        else:
            vt = (value_text or "").strip() or None
            value_key = ("text", vt)
        dedup_key = (series_key, value_key, ref_min, ref_max)
        if dedup_key in existing_keys or dedup_key in seen_keys:
            continue

        db_item = LabResult(
            patient_id=patient_id,
            analyte_name=name_clean,
            value=value_num if value_num is not None else None,
            value_text=value_text if value_num is None else None,
            unit=unit_value,
            material=record.get("specimen"),
            taken_at=taken_at,
            ref_range=ref_range,
            ref_min=ref_min,
            ref_max=ref_max,
            source_pdf=source_pdf,
            document_hash=document_hash,
            series_key=series_key,
        )
        session.add(db_item)
        seen_keys.add(dedup_key)
        inserted += 1

    session.commit()
    return inserted
