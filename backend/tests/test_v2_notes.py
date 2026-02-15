import asyncio
import datetime as dt

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, DoctorGrant, Patient, User
from backend.main import (
    list_v2_doctor_patient_notes,
    list_v2_patient_notes,
    upsert_v2_doctor_patient_note,
)
from backend.v2.schemas import V2UpsertDoctorNoteRequest


def _seed_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    patient_owner = User(
        email="patient-notes@test.local",
        hashed_password="x",
        full_name="Patient Notes",
        is_active=True,
        is_doctor=False,
    )
    doctor = User(
        email="doctor-notes@test.local",
        hashed_password="x",
        full_name="Doctor Notes",
        is_active=True,
        is_doctor=True,
    )
    doctor_without_grant = User(
        email="doctor-no-grant@test.local",
        hashed_password="x",
        full_name="Doctor No Grant",
        is_active=True,
        is_doctor=True,
    )
    db.add_all([patient_owner, doctor, doctor_without_grant])
    db.commit()
    db.refresh(patient_owner)
    db.refresh(doctor)
    db.refresh(doctor_without_grant)

    patient = Patient(user_id=patient_owner.id, full_name="Patient Card")
    db.add(patient)
    db.commit()
    db.refresh(patient)

    grant = DoctorGrant(
        patient_id=patient.id,
        doctor_id=doctor.id,
        doctor_email=doctor.email,
        granted_at=dt.datetime(2026, 1, 11, 9, 0, 0),
    )
    db.add(grant)
    db.commit()

    return db, patient_owner, patient, doctor, doctor_without_grant


def test_v2_doctor_note_upsert_and_patient_read():
    db, patient_owner, patient, doctor, _doctor_without_grant = _seed_db()
    try:
        point_time = dt.datetime(2026, 1, 10, 8, 0, 0)
        payload = V2UpsertDoctorNoteRequest(
            analyte_key="ALT_SERUM",
            t=point_time,
            note="Please repeat in 2 weeks",
        )

        upserted = asyncio.run(
            upsert_v2_doctor_patient_note(
                patient_id=patient.id,
                payload=payload,
                user_id=doctor.id,
                db=db,
            )
        )
        assert upserted.analyte_key == "ALT_SERUM"
        assert upserted.note == "Please repeat in 2 weeks"
        assert upserted.doctor_id == doctor.id
        assert upserted.doctor_name == doctor.full_name

        doctor_notes = asyncio.run(
            list_v2_doctor_patient_notes(
                patient_id=patient.id,
                analyte_key="ALT_SERUM",
                user_id=doctor.id,
                db=db,
            )
        )
        assert len(doctor_notes) == 1
        assert doctor_notes[0].note == "Please repeat in 2 weeks"

        patient_notes = asyncio.run(
            list_v2_patient_notes(
                analyte_key="ALT_SERUM",
                user_id=patient_owner.id,
                db=db,
            )
        )
        assert len(patient_notes) == 1
        assert patient_notes[0].note == "Please repeat in 2 weeks"
        assert patient_notes[0].doctor_name == doctor.full_name
    finally:
        db.close()


def test_v2_doctor_notes_without_grant_forbidden():
    db, _patient_owner, patient, _doctor, doctor_without_grant = _seed_db()
    try:
        payload = V2UpsertDoctorNoteRequest(
            analyte_key="ALT_SERUM",
            t=dt.datetime(2026, 1, 10, 8, 0, 0),
            note="No access",
        )
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                upsert_v2_doctor_patient_note(
                    patient_id=patient.id,
                    payload=payload,
                    user_id=doctor_without_grant.id,
                    db=db,
                )
            )
        assert exc.value.status_code == 403
    finally:
        db.close()


def test_v2_patient_cannot_write_doctor_note():
    db, patient_owner, patient, _doctor, _doctor_without_grant = _seed_db()
    try:
        payload = V2UpsertDoctorNoteRequest(
            analyte_key="ALT_SERUM",
            t=dt.datetime(2026, 1, 10, 8, 0, 0),
            note="Patient should not write",
        )
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                upsert_v2_doctor_patient_note(
                    patient_id=patient.id,
                    payload=payload,
                    user_id=patient_owner.id,
                    db=db,
                )
            )
        assert exc.value.status_code == 403
    finally:
        db.close()
