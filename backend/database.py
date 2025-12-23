"""Database models and setup for lab results storage."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship

# Ensure .env is loaded before reading DB_URL so we don't fall back to SQLite accidentally
load_dotenv()

if TYPE_CHECKING:
    from models import ImportJson

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


def get_database_url(default_sqlite: str = "sqlite:///./lab_results.db") -> str:
    """Get database URL from environment or fallback to local SQLite."""
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
    
    for item in import_data.items:
        name_clean = (item.analyte_name or "").strip()
        if not name_clean:
            continue
        if name_clean.upper() in junk_names:
            continue

        ref_min = _coerce_float(getattr(item, "ref_min", None))
        ref_max = _coerce_float(getattr(item, "ref_max", None))
        taken_at = _parse_datetime(item.taken_at) or doc_date

        db_item = LabResult(
            patient_id=patient_db_id,  # Use the actual patient_id from DB
            analyte_name=item.analyte_name,
            value=item.value,
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
