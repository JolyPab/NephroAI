"""Stripe Billing routes for NephroAI subscriptions."""

from __future__ import annotations

import datetime as dt
import os
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user_id
from backend.database import Payment, SessionLocal, Subscription, User

try:
    import stripe
except Exception:  # pragma: no cover - exercised only when dependency is missing.
    stripe = None  # type: ignore[assignment]


router = APIRouter(prefix="/api/billing", tags=["billing"])

ACTIVE_STRIPE_STATUSES = {"active", "trialing"}
PAST_DUE_STRIPE_STATUSES = {"past_due", "unpaid"}
CANCELED_STRIPE_STATUSES = {"canceled", "incomplete_expired"}
_configured_stripe_secret_key: str | None = None


class BillingConfigResponse(BaseModel):
    publishable_key: str
    price_id: str


class BillingSubscriptionResponse(BaseModel):
    status: str
    provider: str | None = None
    current_period_end: str | None = None


class CheckoutSessionRequest(BaseModel):
    interval: str = "monthly"

class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str


class PortalSessionResponse(BaseModel):
    portal_url: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _stripe_client():
    global _configured_stripe_secret_key
    if stripe is None:
        raise HTTPException(status_code=500, detail="Stripe SDK is not installed.")
    secret_key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
    if not secret_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY is not configured.")
    if _configured_stripe_secret_key != secret_key:
        stripe.api_key = secret_key
        _configured_stripe_secret_key = secret_key
    return stripe


def _app_base_url(request: Request = None) -> str:
    if request:
        return str(request.base_url).rstrip("/")
    url = (os.getenv("APP_PUBLIC_URL") or "").strip()
    if not url:
        url = (os.getenv("FRONTEND_PUBLIC_URL") or "").strip()
    if not url:
        env = (os.getenv("ENV") or os.getenv("APP_ENV") or "development").lower()
        url = "https://app.nephroai.ec" if env in ("prod", "production") else "http://localhost:4200"
    return url.rstrip("/")


def _stripe_price_id(interval: str = "monthly") -> str:
    env_var = "STRIPE_PRICE_ID_YEARLY" if interval == "yearly" else "STRIPE_PRICE_ID_MONTHLY"
    price_id = (os.getenv(env_var) or "").strip()
    if not price_id:
        price_id = (os.getenv("STRIPE_PRICE_ID") or "").strip()
    if not price_id:
        raise HTTPException(status_code=500, detail=f"{env_var} is not configured.")
    return price_id


def _stripe_publishable_key() -> str:
    return (os.getenv("STRIPE_PUBLISHABLE_KEY") or "").strip()


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _timestamp_to_datetime(value: Any) -> Optional[dt.datetime]:
    if value is None:
        return None
    try:
        return dt.datetime.utcfromtimestamp(int(value))
    except (TypeError, ValueError, OSError):
        return None


def _map_subscription_status(stripe_status: str | None) -> str:
    if stripe_status in ACTIVE_STRIPE_STATUSES:
        return "active"
    if stripe_status in PAST_DUE_STRIPE_STATUSES:
        return "past_due"
    if stripe_status in CANCELED_STRIPE_STATUSES:
        return "canceled"
    return "inactive"


def _find_or_create_subscription(
    db: Session,
    *,
    user_id: int,
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
) -> Subscription:
    query = db.query(Subscription)
    subscription = None
    if stripe_subscription_id:
        subscription = query.filter(Subscription.stripe_subscription_id == stripe_subscription_id).first()
    if subscription is None and stripe_customer_id:
        subscription = query.filter(
            Subscription.user_id == user_id,
            Subscription.stripe_customer_id == stripe_customer_id,
        ).first()
    if subscription is None:
        subscription = query.filter(Subscription.user_id == user_id).order_by(Subscription.id.desc()).first()
    if subscription is None:
        subscription = Subscription(user_id=user_id)
        db.add(subscription)

    if stripe_customer_id:
        subscription.stripe_customer_id = stripe_customer_id
    if stripe_subscription_id:
        subscription.stripe_subscription_id = stripe_subscription_id
    subscription.updated_at = dt.datetime.utcnow()
    return subscription


def _sync_subscription_from_stripe_object(db: Session, subscription_obj: Any, user_id: int | None = None) -> None:
    stripe_subscription_id = _get_value(subscription_obj, "id")
    stripe_customer_id = _get_value(subscription_obj, "customer")
    metadata = _get_value(subscription_obj, "metadata", {}) or {}
    if user_id is None:
        raw_user_id = _get_value(metadata, "user_id")
        if raw_user_id:
            try:
                user_id = int(raw_user_id)
            except (TypeError, ValueError):
                user_id = None
    if user_id is None and stripe_customer_id:
        existing = db.query(Subscription).filter(Subscription.stripe_customer_id == stripe_customer_id).first()
        user_id = existing.user_id if existing else None
    if user_id is None:
        return

    subscription = _find_or_create_subscription(
        db,
        user_id=user_id,
        stripe_customer_id=stripe_customer_id,
        stripe_subscription_id=stripe_subscription_id,
    )
    subscription.status = _map_subscription_status(_get_value(subscription_obj, "status"))
    subscription.plan_id = _get_value(_get_value(subscription_obj, "plan", {}), "id") or _stripe_price_id()
    subscription.period_start = _timestamp_to_datetime(_get_value(subscription_obj, "current_period_start"))
    subscription.period_end = _timestamp_to_datetime(_get_value(subscription_obj, "current_period_end"))


def _record_invoice_payment(db: Session, invoice_obj: Any, status_value: str) -> None:
    invoice_id = _get_value(invoice_obj, "id")
    if not invoice_id:
        return
    stripe_subscription_id = _get_value(invoice_obj, "subscription")
    subscription = None
    if stripe_subscription_id:
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_subscription_id,
        ).first()
    raw_user_id = _get_value(_get_value(invoice_obj, "metadata", {}) or {}, "user_id")
    if subscription is None and raw_user_id:
        try:
            subscription = db.query(Subscription).filter(Subscription.user_id == int(raw_user_id)).first()
        except (TypeError, ValueError):
            subscription = None
    if subscription is None:
        return

    payment = db.query(Payment).filter(Payment.stripe_invoice_id == invoice_id).first()
    if payment is None:
        payment = Payment(user_id=subscription.user_id, stripe_invoice_id=invoice_id)
        db.add(payment)

    payment.user_id = subscription.user_id
    payment.subscription_id = subscription.id
    payment.status = status_value
    payment.currency = (_get_value(invoice_obj, "currency") or "mxn").upper()
    payment.amount = (_get_value(invoice_obj, "amount_paid") or _get_value(invoice_obj, "amount_due") or 0) / 100
    payment.stripe_payment_id = _get_value(invoice_obj, "payment_intent")


@router.get("/config", response_model=BillingConfigResponse)
async def billing_config():
    return BillingConfigResponse(
        publishable_key=_stripe_publishable_key(),
        price_id=_stripe_price_id(),
    )


@router.get("/subscription", response_model=BillingSubscriptionResponse)
async def get_subscription(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    subscription = db.query(Subscription).filter(Subscription.user_id == user_id).order_by(Subscription.id.desc()).first()
    if subscription is None:
        return BillingSubscriptionResponse(status="inactive")
    return BillingSubscriptionResponse(
        status=subscription.status,
        provider="stripe" if subscription.stripe_subscription_id else "paypal" if subscription.paypal_subscription_id else None,
        current_period_end=subscription.period_end.isoformat() if subscription.period_end else None,
    )


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: Request,
    request_data: CheckoutSessionRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    stripe_client = _stripe_client()
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(Subscription).filter(Subscription.user_id == user_id).order_by(Subscription.id.desc()).first()
    customer_id = existing.stripe_customer_id if existing else None
    if not customer_id:
        customer = stripe_client.Customer.create(
            email=user.email,
            name=user.full_name,
            metadata={"user_id": str(user_id)},
        )
        customer_id = _get_value(customer, "id")

    session = stripe_client.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": _stripe_price_id(request_data.interval), "quantity": 1}],
        success_url=f"{_app_base_url(request)}/patient/profile?checkout=success",
        cancel_url=f"{_app_base_url(request)}/patient/profile?checkout=canceled",
        client_reference_id=str(user_id),
        subscription_data={"metadata": {"user_id": str(user_id)}},
        metadata={"user_id": str(user_id)},
        allow_promotion_codes=True,
        adaptive_pricing={"enabled": False},
        locale="es",
    )

    subscription = _find_or_create_subscription(db, user_id=user_id, stripe_customer_id=customer_id)
    subscription.plan_id = _stripe_price_id(request_data.interval)
    if subscription.status != "active":
        subscription.status = "inactive"
    payment = Payment(
        user_id=user_id,
        subscription=subscription,
        status="pending",
        currency="MXN",
        stripe_checkout_session_id=_get_value(session, "id"),
    )
    db.add(payment)
    db.commit()

    return CheckoutSessionResponse(checkout_url=_get_value(session, "url"), session_id=_get_value(session, "id"))


@router.post("/portal-session", response_model=PortalSessionResponse)
async def create_portal_session(
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    stripe_client = _stripe_client()
    subscription = db.query(Subscription).filter(Subscription.user_id == user_id).order_by(Subscription.id.desc()).first()
    if subscription is None or not subscription.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No active Stripe customer found.")
    session = stripe_client.billing_portal.Session.create(
        customer=subscription.stripe_customer_id,
        return_url=f"{_app_base_url(request)}/patient/profile",
    )
    return PortalSessionResponse(portal_url=_get_value(session, "url"))


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    stripe_client = _stripe_client()
    webhook_secret = (os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    if not webhook_secret:
        raise HTTPException(status_code=500, detail="STRIPE_WEBHOOK_SECRET is not configured.")

    try:
        event = stripe_client.Webhook.construct_event(payload, signature, webhook_secret)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe webhook.") from exc

    event_type = _get_value(event, "type")
    obj = _get_value(_get_value(event, "data", {}) or {}, "object", {})

    if event_type == "checkout.session.completed":
        raw_user_id = _get_value(_get_value(obj, "metadata", {}) or {}, "user_id") or _get_value(obj, "client_reference_id")
        try:
            user_id = int(raw_user_id)
        except (TypeError, ValueError):
            user_id = None
        stripe_subscription_id = _get_value(obj, "subscription")
        stripe_customer_id = _get_value(obj, "customer")
        if user_id is not None:
            subscription = _find_or_create_subscription(
                db,
                user_id=user_id,
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
            )
            subscription.plan_id = _get_value(_get_value(obj, "plan", {}), "id") or _stripe_price_id()
            subscription.status = "active"
            payment = db.query(Payment).filter(Payment.stripe_checkout_session_id == _get_value(obj, "id")).first()
            if payment:
                payment.status = "completed"
    elif event_type in {"customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"}:
        _sync_subscription_from_stripe_object(db, obj)
    elif event_type == "invoice.paid":
        _record_invoice_payment(db, obj, "completed")
    elif event_type == "invoice.payment_failed":
        _record_invoice_payment(db, obj, "failed")
        stripe_subscription_id = _get_value(obj, "subscription")
        if stripe_subscription_id:
            subscription = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == stripe_subscription_id,
            ).first()
            if subscription:
                subscription.status = "past_due"

    db.commit()
    return {"received": True}
