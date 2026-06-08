import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend import billing_routes
from backend.database import Base, Payment, Subscription, User


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
    @staticmethod
    def create(**kwargs):
        assert kwargs["mode"] == "subscription"
        assert kwargs["line_items"][0]["price"] == "price_test_123"
        assert kwargs["metadata"]["user_id"] == "1"
        return {"id": "cs_test_123", "url": "https://checkout.stripe.test/session"}


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

    response = asyncio.run(billing_routes.create_checkout_session(request_data=billing_routes.CheckoutSessionRequest(interval="monthly"), user_id=1, db=db))

    assert response.checkout_url == "https://checkout.stripe.test/session"
    subscription = db.query(Subscription).one()
    assert subscription.user_id == 1
    assert subscription.stripe_customer_id == "cus_test_123"
    assert subscription.plan_id == "price_test_123"
    payment = db.query(Payment).one()
    assert payment.status == "pending"
    assert payment.stripe_checkout_session_id == "cs_test_123"
    db.close()


def test_webhook_checkout_completed_marks_subscription_active(monkeypatch):
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
            }
        },
    }
    monkeypatch.setattr(billing_routes, "stripe", _FakeStripe)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_fake")
    monkeypatch.setenv("STRIPE_PRICE_ID", "price_test_123")

    response = asyncio.run(billing_routes.stripe_webhook(_FakeRequest(), db=db))

    assert response == {"received": True}
    subscription = db.query(Subscription).one()
    assert subscription.status == "active"
    assert subscription.stripe_subscription_id == "sub_test_123"
    payment = db.query(Payment).one()
    assert payment.status == "completed"
    db.close()


def test_create_portal_session_uses_existing_customer(monkeypatch):
    db = _setup_db()
    db.add(User(id=1, email="patient@example.com", hashed_password="hash", full_name="Paciente Uno"))
    db.add(Subscription(user_id=1, stripe_customer_id="cus_test_123", status="active"))
    db.commit()

    monkeypatch.setattr(billing_routes, "stripe", _FakeStripe)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("APP_PUBLIC_URL", "https://app.nephroai.ec")

    response = asyncio.run(billing_routes.create_portal_session(user_id=1, db=db))

    assert response.portal_url == "https://billing.stripe.test/session"
    db.close()
