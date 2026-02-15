import asyncio
import datetime as dt

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, DoctorGrant, Patient, User, V2Document, V2Metric
from backend.main import (
    get_v2_doctor_patient_series,
    list_v2_doctor_patient_analytes,
    list_v2_doctor_patients,
)


def _seed_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    patient_owner = User(
        email="patient-owner@test.local",
        hashed_password="x",
        full_name="Patient Owner",
        is_active=True,
        is_doctor=False,
    )
    doctor_with_grant = User(
        email="doctor-with@test.local",
        hashed_password="x",
        full_name="Doctor With Grant",
        is_active=True,
        is_doctor=True,
    )
    doctor_without_grant = User(
        email="doctor-without@test.local",
        hashed_password="x",
        full_name="Doctor Without Grant",
        is_active=True,
        is_doctor=True,
    )
    db.add_all([patient_owner, doctor_with_grant, doctor_without_grant])
    db.commit()
    db.refresh(patient_owner)
    db.refresh(doctor_with_grant)
    db.refresh(doctor_without_grant)

    patient = Patient(user_id=patient_owner.id, full_name="Patient Card Name")
    db.add(patient)
    db.commit()
    db.refresh(patient)

    grant = DoctorGrant(
        patient_id=patient.id,
        doctor_id=doctor_with_grant.id,
        doctor_email=doctor_with_grant.email,
        granted_at=dt.datetime(2026, 1, 10, 8, 30, 0),
    )
    db.add(grant)

    document = V2Document(
        user_id=patient_owner.id,
        document_hash="hash-1",
        source_filename="report.pdf",
        analysis_date=dt.datetime(2026, 1, 9, 9, 0, 0),
    )
    db.add(document)
    db.flush()
    db.add(
        V2Metric(
            document_id=document.id,
            analyte_key="ALT_SERUM",
            raw_name="ALT",
            specimen="serum",
            context="random",
            value_numeric=36.0,
            value_text=None,
            unit="U/L",
            reference_json={"type": "max", "threshold": 41},
            page=1,
            evidence="ALT 36 U/L <41",
        )
    )
    db.commit()

    return db, patient_owner, patient, doctor_with_grant, doctor_without_grant


def test_v2_doctor_with_grant_can_fetch_patient_analytes_and_series():
    db, _patient_owner, patient, doctor_with_grant, _doctor_without_grant = _seed_db()
    try:
        patients = asyncio.run(list_v2_doctor_patients(user_id=doctor_with_grant.id, db=db))
        assert len(patients) == 1
        assert patients[0].patient_id == patient.id
        assert patients[0].latest_analysis_date is not None

        analytes = asyncio.run(
            list_v2_doctor_patient_analytes(patient_id=patient.id, user_id=doctor_with_grant.id, db=db)
        )
        assert len(analytes) == 1
        assert analytes[0].analyte_key == "ALT_SERUM"
        assert analytes[0].last_value_numeric == 36.0

        series = asyncio.run(
            get_v2_doctor_patient_series(
                patient_id=patient.id,
                analyte_key="ALT_SERUM",
                user_id=doctor_with_grant.id,
                db=db,
            )
        )
        assert series["series_type"] == "numeric"
        assert series["unit"] == "U/L"
        assert len(series["points"]) == 1
        assert series["points"][0]["y"] == 36.0
    finally:
        db.close()


def test_v2_doctor_without_grant_gets_403():
    db, _patient_owner, patient, _doctor_with_grant, doctor_without_grant = _seed_db()
    try:
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                list_v2_doctor_patient_analytes(
                    patient_id=patient.id,
                    user_id=doctor_without_grant.id,
                    db=db,
                )
            )
        assert exc.value.status_code == 403

        with pytest.raises(HTTPException) as exc_series:
            asyncio.run(
                get_v2_doctor_patient_series(
                    patient_id=patient.id,
                    analyte_key="ALT_SERUM",
                    user_id=doctor_without_grant.id,
                    db=db,
                )
            )
        assert exc_series.value.status_code == 403
    finally:
        db.close()


def test_v2_non_doctor_cannot_list_doctor_patients():
    db, patient_owner, _patient, _doctor_with_grant, _doctor_without_grant = _seed_db()
    try:
        with pytest.raises(HTTPException) as exc:
            asyncio.run(list_v2_doctor_patients(user_id=patient_owner.id, db=db))
        assert exc.value.status_code == 403
    finally:
        db.close()
