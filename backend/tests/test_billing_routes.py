import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend import billing_routes
from backend import email_service
from backend.database import Base, Payment, SubscriberWelcomeEmail, Subscription, User


def _setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return session_local()


class _FakeCustomer:
    @staticmethod
    def create(**_kwargs):
        return {"id": "cus_test_123"}


class _FakeCheckoutSession:
    last_kwargs = None

    @staticmethod
    def create(**kwargs):
        _FakeCheckoutSession.last_kwargs = kwargs
        assert kwargs["mode"] == "subscription"
        assert kwargs["line_items"][0]["price"] == "price_test_123"
        assert kwargs["metadata"]["user_id"] == "1"
        return {"id": "cs_test_123", "url": "https://checkout.stripe.test/session"}


class _FakeSubscription:
    status = "trialing"

    @staticmethod
    def retrieve(subscription_id):
        assert subscription_id == "sub_test_123"
        return {
            "id": subscription_id,
            "customer": "cus_test_123",
            "status": _FakeSubscription.status,
            "metadata": {"user_id": "1"},
            "plan": {"id": "price_test_123"},
            "current_period_start": 1782777600,
            "current_period_end": 1783382400,
            "trial_start": 1782777600,
            "trial_end": 1783382400,
        }


class _FakePortalSession:
    @staticmethod
    def create(**kwargs):
        assert kwargs["customer"] == "cus_test_123"
        return {"url": "https://billing.stripe.test/session"}


class _FakeWebhook:
    event = {}

    @classmethod
    def construct_event(cls, _payload, _signature, _secret):
        return cls.event


class _FakeStripe:
    api_key = None
    Customer = _FakeCustomer
    Subscription = _FakeSubscription

    class checkout:
        Session = _FakeCheckoutSession

    class billing_portal:
        Session = _FakePortalSession

    Webhook = _FakeWebhook


class _FakeRequest:
    headers = {"stripe-signature": "test-signature"}

    async def body(self):
        return b"{}"


def test_create_checkout_session_records_pending_subscription(monkeypatch):
    db = _setup_db()
    db.add(User(id=1, email="patient@example.com", hashed_password="hash", full_name="Paciente Uno"))
    db.commit()

    monkeypatch.setattr(billing_routes, "stripe", _FakeStripe)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("STRIPE_PRICE_ID_MONTHLY", "price_test_123")
    monkeypatch.setenv("STRIPE_PRICE_ID", "price_test_123")
    monkeypatch.setenv("APP_PUBLIC_URL", "https://app.nephroai.ec")

    response = asyncio.run(billing_routes.create_checkout_session(request=None, request_data=billing_routes.CheckoutSessionRequest(interval="monthly"), user_id=1, db=db))

    assert response.checkout_url == "https://checkout.stripe.test/session"
    subscription = db.query(Subscription).one()
    assert subscription.user_id == 1
    assert subscription.stripe_customer_id == "cus_test_123"
    assert subscription.plan_id == "price_test_123"
    assert _FakeCheckoutSession.last_kwargs["subscription_data"]["trial_period_days"] == 7
    assert _FakeCheckoutSession.last_kwargs["adaptive_pricing"] == {"enabled": False}
    payment = db.query(Payment).one()
    assert payment.status == "pending"
    assert payment.currency == "USD"
    assert payment.stripe_checkout_session_id == "cs_test_123"
    db.close()


def test_webhook_checkout_completed_marks_subscription_trialing(monkeypatch):
    db = _setup_db()
    db.add(User(id=1, email="patient@example.com", hashed_password="hash", full_name="Paciente Uno"))
    db.add(Subscription(user_id=1, stripe_customer_id="cus_test_123", status="inactive"))
    db.add(Payment(user_id=1, status="pending", stripe_checkout_session_id="cs_test_123"))
    db.commit()

    _FakeWebhook.event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "customer": "cus_test_123",
                "subscription": "sub_test_123",
                "client_reference_id": "1",
                "metadata": {"user_id": "1"},
                "status": "complete",
                "payment_status": "no_payment_required",
            }
        },
    }
    monkeypatch.setattr(billing_routes, "stripe", _FakeStripe)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_fake")
    monkeypatch.setenv("STRIPE_PRICE_ID", "price_test_123")
    sent = []
    monkeypatch.setattr(
        billing_routes,
        "send_subscriber_welcome_email",
        lambda email, **kwargs: sent.append((email, kwargs)),
    )

    response = asyncio.run(billing_routes.stripe_webhook(_FakeRequest(), db=db))

    assert response == {"received": True}
    subscription = db.query(Subscription).one()
    assert subscription.status == "trialing"
    assert subscription.stripe_subscription_id == "sub_test_123"
    assert subscription.trial_end is not None
    assert subscription.trial_used_at is not None
    payment = db.query(Payment).one()
    assert payment.status == "completed"
    assert sent == [("patient@example.com", {"is_trial": True, "idempotency_key": "subscriber-welcome-sub_test_123"})]
    assert db.query(SubscriberWelcomeEmail).one().status == "sent"
    db.close()


def test_webhook_sends_welcome_for_active_subscription_without_trial(monkeypatch):
    db = _setup_db()
    db.add(User(id=1, email="patient@example.com", hashed_password="hash", full_name="Paciente Uno"))
    db.add(Subscription(user_id=1, stripe_customer_id="cus_test_123", status="inactive"))
    db.commit()
    _FakeSubscription.status = "active"
    _FakeWebhook.event = {
        "type": "checkout.session.completed",
        "data": {"object": {
            "id": "cs_active", "customer": "cus_test_123", "subscription": "sub_test_123",
            "client_reference_id": "1", "metadata": {"user_id": "1"},
            "status": "complete", "payment_status": "paid",
        }},
    }
    sent = []
    monkeypatch.setattr(billing_routes, "stripe", _FakeStripe)
    monkeypatch.setattr(billing_routes, "send_subscriber_welcome_email", lambda email, **kwargs: sent.append((email, kwargs)))
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_fake")
    monkeypatch.setenv("STRIPE_PRICE_ID", "price_test_123")

    asyncio.run(billing_routes.stripe_webhook(_FakeRequest(), db=db))

    assert db.query(Subscription).one().status == "active"
    assert sent[0][1]["is_trial"] is False
    assert db.query(SubscriberWelcomeEmail).one().status == "sent"
    _FakeSubscription.status = "trialing"
    db.close()


def test_webhook_replay_does_not_repeat_welcome(monkeypatch):
    db = _setup_db()
    db.add(User(id=1, email="patient@example.com", hashed_password="hash", full_name="Paciente Uno"))
    db.add(Subscription(user_id=1, stripe_customer_id="cus_test_123", status="inactive"))
    db.commit()
    _FakeSubscription.status = "trialing"
    _FakeWebhook.event = {
        "type": "checkout.session.completed",
        "data": {"object": {
            "id": "cs_replay", "customer": "cus_test_123", "subscription": "sub_test_123",
            "client_reference_id": "1", "metadata": {"user_id": "1"},
            "status": "complete", "payment_status": "no_payment_required",
        }},
    }
    sent = []
    monkeypatch.setattr(billing_routes, "stripe", _FakeStripe)
    monkeypatch.setattr(billing_routes, "send_subscriber_welcome_email", lambda email, **kwargs: sent.append(kwargs))
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_fake")
    monkeypatch.setenv("STRIPE_PRICE_ID", "price_test_123")

    asyncio.run(billing_routes.stripe_webhook(_FakeRequest(), db=db))
    asyncio.run(billing_routes.stripe_webhook(_FakeRequest(), db=db))

    assert len(sent) == 1
    assert db.query(SubscriberWelcomeEmail).count() == 1
    db.close()


def test_webhook_does_not_send_for_unsuccessful_checkout(monkeypatch):
    db = _setup_db()
    db.add(User(id=1, email="patient@example.com", hashed_password="hash", full_name="Paciente Uno"))
    db.add(Subscription(user_id=1, stripe_customer_id="cus_test_123", status="inactive"))
    db.add(Payment(user_id=1, status="pending", stripe_checkout_session_id="cs_unpaid"))
    db.commit()
    _FakeSubscription.status = "active"
    _FakeWebhook.event = {
        "type": "checkout.session.completed",
        "data": {"object": {
            "id": "cs_unpaid", "customer": "cus_test_123", "subscription": "sub_test_123",
            "client_reference_id": "1", "metadata": {"user_id": "1"},
            "status": "complete", "payment_status": "unpaid",
        }},
    }
    sent = []
    monkeypatch.setattr(billing_routes, "stripe", _FakeStripe)
    monkeypatch.setattr(billing_routes, "send_subscriber_welcome_email", lambda *args, **kwargs: sent.append(kwargs))
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_fake")
    monkeypatch.setenv("STRIPE_PRICE_ID", "price_test_123")

    asyncio.run(billing_routes.stripe_webhook(_FakeRequest(), db=db))

    assert sent == []
    assert db.query(SubscriberWelcomeEmail).count() == 0
    assert db.query(Payment).one().status == "pending"
    _FakeSubscription.status = "trialing"
    db.close()


def test_resend_error_retries_with_same_idempotency_key(monkeypatch):
    db = _setup_db()
    db.add(User(id=1, email="patient@example.com", hashed_password="hash", full_name="Paciente Uno"))
    db.add(Subscription(user_id=1, stripe_customer_id="cus_test_123", status="inactive"))
    db.commit()
    _FakeSubscription.status = "trialing"
    _FakeWebhook.event = {
        "type": "checkout.session.completed",
        "data": {"object": {
            "id": "cs_retry", "customer": "cus_test_123", "subscription": "sub_test_123",
            "client_reference_id": "1", "metadata": {"user_id": "1"},
            "status": "complete", "payment_status": "no_payment_required",
        }},
    }
    keys = []
    def flaky_send(_email, **kwargs):
        keys.append(kwargs["idempotency_key"])
        if len(keys) == 1:
            raise RuntimeError("network timeout")
    monkeypatch.setattr(billing_routes, "stripe", _FakeStripe)
    monkeypatch.setattr(billing_routes, "send_subscriber_welcome_email", flaky_send)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_fake")
    monkeypatch.setenv("STRIPE_PRICE_ID", "price_test_123")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(billing_routes.stripe_webhook(_FakeRequest(), db=db))
    assert exc.value.status_code == 503
    assert db.query(SubscriberWelcomeEmail).one().status == "pending"

    asyncio.run(billing_routes.stripe_webhook(_FakeRequest(), db=db))

    assert keys == ["subscriber-welcome-sub_test_123", "subscriber-welcome-sub_test_123"]
    delivery = db.query(SubscriberWelcomeEmail).one()
    assert delivery.status == "sent"
    assert delivery.attempt_count == 2
    db.close()


def test_welcome_email_uses_configured_sender_and_spanish_multipart_content(monkeypatch):
    captured = {}
    class _Response:
        status_code = 200
    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return _Response()
    monkeypatch.setattr(email_service.requests, "post", fake_post)
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "info@example.test")
    monkeypatch.setenv("APP_PUBLIC_URL", "https://app.example.test")

    email_service.send_subscriber_welcome_email(
        "patient@example.test",
        is_trial=True,
        idempotency_key="subscriber-welcome-sub_test_123",
    )

    assert captured["headers"]["Idempotency-Key"] == "subscriber-welcome-sub_test_123"
    assert captured["json"]["from"] == "NephroAI <info@example.test>"
    assert captured["json"]["to"] == ["patient@example.test"]
    assert captured["json"]["subject"] == "¡Bienvenido(a) a NephroAI! 💙"
    assert "período de prueba" in captured["json"]["text"]
    assert "https://app.example.test" in captured["json"]["html"]
    assert "Equipo NephroAI" in captured["json"]["text"]


def test_checkout_does_not_repeat_trial_after_it_was_used(monkeypatch):
    db = _setup_db()
    db.add(User(id=1, email="patient@example.com", hashed_password="hash", full_name="Paciente Uno"))
    db.add(
        Subscription(
            user_id=1,
            stripe_customer_id="cus_test_123",
            status="canceled",
            trial_used_at=billing_routes.dt.datetime.utcnow(),
        )
    )
    db.commit()

    monkeypatch.setattr(billing_routes, "stripe", _FakeStripe)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("STRIPE_PRICE_ID_MONTHLY", "price_test_123")

    asyncio.run(
        billing_routes.create_checkout_session(
            request=None,
            request_data=billing_routes.CheckoutSessionRequest(interval="monthly"),
            user_id=1,
            db=db,
        )
    )

    assert "trial_period_days" not in _FakeCheckoutSession.last_kwargs["subscription_data"]
    db.close()


def test_checkout_rejects_user_with_active_subscription(monkeypatch):
    db = _setup_db()
    db.add(User(id=1, email="patient@example.com", hashed_password="hash", full_name="Paciente Uno"))
    db.add(Subscription(user_id=1, status="active"))
    db.commit()

    monkeypatch.setattr(billing_routes, "stripe", _FakeStripe)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            billing_routes.create_checkout_session(
                request=None,
                request_data=billing_routes.CheckoutSessionRequest(interval="monthly"),
                user_id=1,
                db=db,
            )
        )

    assert exc.value.status_code == 409
    assert "suscripción activa" in exc.value.detail
    db.close()


def test_create_portal_session_uses_existing_customer(monkeypatch):
    db = _setup_db()
    db.add(User(id=1, email="patient@example.com", hashed_password="hash", full_name="Paciente Uno"))
    db.add(Subscription(user_id=1, stripe_customer_id="cus_test_123", status="active"))
    db.commit()

    monkeypatch.setattr(billing_routes, "stripe", _FakeStripe)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("APP_PUBLIC_URL", "https://app.nephroai.ec")

    response = asyncio.run(billing_routes.create_portal_session(request=None, user_id=1, db=db))

    assert response.portal_url == "https://billing.stripe.test/session"
    db.close()
