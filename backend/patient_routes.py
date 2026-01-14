"""Patient routes."""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from backend.database import Patient, SessionLocal
from backend.auth import get_current_user_id

router = APIRouter(prefix="/api/patients", tags=["patients"])


# Pydantic models
class PatientCreate(BaseModel):
    full_name: str
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None


class PatientResponse(BaseModel):
    id: int
    full_name: str
    date_of_birth: Optional[datetime]
    gender: Optional[str]
    created_at: datetime


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[PatientResponse])
async def get_my_patients(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get current user's patients."""
    patients = db.query(Patient).filter(Patient.user_id == user_id).all()
    return patients


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient_data: PatientCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Create new patient for current user."""
    db_patient = Patient(
        user_id=user_id,
        full_name=patient_data.full_name,
        date_of_birth=patient_data.date_of_birth,
        gender=patient_data.gender
    )
    
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    
    return db_patient


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get patient by ID (must belong to current user)."""
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.user_id == user_id
    ).first()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    return patient

