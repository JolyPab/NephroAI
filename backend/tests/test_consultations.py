import asyncio
import datetime as dt

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, DoctorGrant, Patient, User
from backend.main import (
    ConsultationMessageCreate,
    ConsultationThreadCreate,
    ConsultationCallCreate,
    ConsultationCallAction,
    create_consultation_message,
    create_consultation_thread,
    create_consultation_call,
    get_consultation_call_token,
    list_consultation_messages,
    list_consultations,
    mark_consultation_read,
    update_consultation_call,
    update_consultation_permissions,
    ConsultationPermissionsUpdate,
)


def _seed_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    patient_owner = User(
        email="patient-consult@test.local",
        hashed_password="x",
        full_name="Paciente Uno",
        is_active=True,
        is_doctor=False,
    )
    doctor = User(
        email="doctor-consult@test.local",
        hashed_password="x",
        full_name="Dra. Consulta",
        is_active=True,
        is_doctor=True,
    )
    doctor_without_grant = User(
        email="doctor-no-consult@test.local",
        hashed_password="x",
        full_name="Doctor Sin Acceso",
        is_active=True,
        is_doctor=True,
    )
    db.add_all([patient_owner, doctor, doctor_without_grant])
    db.commit()
    db.refresh(patient_owner)
    db.refresh(doctor)
    db.refresh(doctor_without_grant)

    patient = Patient(user_id=patient_owner.id, full_name="Paciente Uno")
    db.add(patient)
    db.commit()
    db.refresh(patient)

    grant = DoctorGrant(
        patient_id=patient.id,
        doctor_id=doctor.id,
        doctor_email=doctor.email,
        can_message=True,
        can_call=False,
        granted_at=dt.datetime(2026, 5, 2, 9, 0, 0),
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)

    return db, patient_owner, patient, doctor, doctor_without_grant, grant


def test_patient_can_list_create_and_message_consultation():
    db, patient_owner, patient, doctor, _doctor_without_grant, grant = _seed_db()
    try:
        consultations = asyncio.run(list_consultations(user_id=patient_owner.id, db=db))
        assert len(consultations) == 1
        assert consultations[0].id is None
        assert consultations[0].status == "not_started"
        assert consultations[0].doctor_email == doctor.email

        thread = asyncio.run(
            create_consultation_thread(
                payload=ConsultationThreadCreate(grant_id=grant.id),
                user_id=patient_owner.id,
                db=db,
            )
        )
        assert thread.id is not None
        assert thread.patient_id == patient.id
        assert thread.doctor_id == doctor.id
        assert thread.can_message is True
        assert thread.can_call is False

        message = asyncio.run(
            create_consultation_message(
                thread_id=thread.id,
                payload=ConsultationMessageCreate(body="Hola doctora"),
                user_id=patient_owner.id,
                db=db,
            )
        )
        assert message.body == "Hola doctora"
        assert message.sender_role == "patient"

        messages = asyncio.run(list_consultation_messages(thread_id=thread.id, user_id=doctor.id, db=db))
        assert len(messages) == 1
        assert messages[0].body == "Hola doctora"

        doctor_consultations = asyncio.run(list_consultations(user_id=doctor.id, db=db))
        assert doctor_consultations[0].unread_count == 1

        read_result = asyncio.run(mark_consultation_read(thread_id=thread.id, user_id=doctor.id, db=db))
        assert read_result["updated"] == 1

        doctor_consultations = asyncio.run(list_consultations(user_id=doctor.id, db=db))
        assert doctor_consultations[0].unread_count == 0
    finally:
        db.close()


def test_doctor_without_grant_cannot_create_consultation():
    db, _patient_owner, patient, _doctor, doctor_without_grant, _grant = _seed_db()
    try:
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                create_consultation_thread(
                    payload=ConsultationThreadCreate(patient_id=patient.id),
                    user_id=doctor_without_grant.id,
                    db=db,
                )
            )
        assert exc.value.status_code == 403
    finally:
        db.close()


def test_call_lifecycle_requires_permission_and_patient_acceptance(monkeypatch):
    db, patient_owner, _patient, doctor, _doctor_without_grant, grant = _seed_db()
    try:
        monkeypatch.setenv("LIVEKIT_URL", "wss://livekit.test")
        monkeypatch.setenv("LIVEKIT_API_KEY", "test-key")
        monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-that-is-long-enough-for-livekit")

        thread = asyncio.run(
            create_consultation_thread(
                payload=ConsultationThreadCreate(grant_id=grant.id),
                user_id=patient_owner.id,
                db=db,
            )
        )

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                create_consultation_call(
                    payload=ConsultationCallCreate(thread_id=thread.id),
                    user_id=doctor.id,
                    db=db,
                )
            )
        assert exc.value.status_code == 403

        updated = asyncio.run(
            update_consultation_permissions(
                grant_id=grant.id,
                payload=ConsultationPermissionsUpdate(can_call=True),
                user_id=patient_owner.id,
                db=db,
            )
        )
        assert updated.can_call is True

        call = asyncio.run(
            create_consultation_call(
                payload=ConsultationCallCreate(thread_id=thread.id),
                user_id=doctor.id,
                db=db,
            )
        )
        assert call.status == "ringing"

        accepted = asyncio.run(
            update_consultation_call(
                call_id=call.id,
                payload=ConsultationCallAction(action="accept"),
                user_id=patient_owner.id,
                db=db,
            )
        )
        assert accepted.status == "accepted"
        assert accepted.accepted_at is not None

        ended = asyncio.run(
            update_consultation_call(
                call_id=call.id,
                payload=ConsultationCallAction(action="end"),
                user_id=doctor.id,
                db=db,
            )
        )
        assert ended.status == "ended"
        assert ended.ended_at is not None
    finally:
        db.close()


def test_livekit_token_issued_for_active_call(monkeypatch):
    db, patient_owner, _patient, doctor, _doctor_without_grant, grant = _seed_db()
    try:
        monkeypatch.setenv("LIVEKIT_URL", "wss://livekit.test")
        monkeypatch.setenv("LIVEKIT_API_KEY", "test-key")
        monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-that-is-long-enough-for-livekit")

        asyncio.run(
            update_consultation_permissions(
                grant_id=grant.id,
                payload=ConsultationPermissionsUpdate(can_call=True),
                user_id=patient_owner.id,
                db=db,
            )
        )
        thread = asyncio.run(
            create_consultation_thread(
                payload=ConsultationThreadCreate(grant_id=grant.id),
                user_id=patient_owner.id,
                db=db,
            )
        )
        call = asyncio.run(
            create_consultation_call(
                payload=ConsultationCallCreate(thread_id=thread.id),
                user_id=doctor.id,
                db=db,
            )
        )

        token_response = asyncio.run(get_consultation_call_token(call_id=call.id, user_id=doctor.id, db=db))
        assert token_response.server_url == "wss://livekit.test"
        assert token_response.room == call.livekit_room
        assert token_response.token
    finally:
        db.close()


def test_call_start_requires_livekit_configuration(monkeypatch):
    db, patient_owner, _patient, doctor, _doctor_without_grant, grant = _seed_db()
    try:
        monkeypatch.delenv("LIVEKIT_URL", raising=False)
        monkeypatch.delenv("LIVEKIT_API_KEY", raising=False)
        monkeypatch.delenv("LIVEKIT_API_SECRET", raising=False)

        asyncio.run(
            update_consultation_permissions(
                grant_id=grant.id,
                payload=ConsultationPermissionsUpdate(can_call=True),
                user_id=patient_owner.id,
                db=db,
            )
        )
        thread = asyncio.run(
            create_consultation_thread(
                payload=ConsultationThreadCreate(grant_id=grant.id),
                user_id=patient_owner.id,
                db=db,
            )
        )

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                create_consultation_call(
                    payload=ConsultationCallCreate(thread_id=thread.id),
                    user_id=doctor.id,
                    db=db,
                )
            )
        assert exc.value.status_code == 503
    finally:
        db.close()
