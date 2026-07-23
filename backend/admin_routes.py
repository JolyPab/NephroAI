"""Read-only operational analytics for NephroAI administrators."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.admin_auth import require_admin_email
from backend.database import (
    AnalyticsEvent,
    AuditLog,
    ChatSession,
    Payment,
    Subscription,
    User,
    V2Document,
)
from backend.deps import get_current_user, get_db


router = APIRouter(prefix="/api/admin", tags=["admin"])


def _period_bounds(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    if date_to < date_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_to must be on or after date_from.",
        )
    if (date_to - date_from).days > 90:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The maximum period is 90 days.",
        )
    return datetime.combine(date_from, time.min), datetime.combine(date_to + timedelta(days=1), time.min)


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    visible = local[:2] if len(local) > 1 else local[:1]
    return f"{visible}***@{domain}" if domain else f"{visible}***"


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() + "Z" if value else None


def _admin_user(user: User = Depends(get_current_user)) -> User:
    require_admin_email(user.email)
    return user


@router.get("/access")
async def admin_access(_: User = Depends(_admin_user)):
    return {"allowed": True}


@router.get("/overview")
async def admin_overview(
    date_from: date = Query(...),
    date_to: date = Query(...),
    _: User = Depends(_admin_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    start, end = _period_bounds(date_from, date_to)
    new_users = (
        db.query(User)
        .filter(User.created_at >= start, User.created_at < end)
        .order_by(User.created_at.desc())
        .all()
    )
    new_user_ids = [user.id for user in new_users]

    first_uploads: dict[int, datetime] = {}
    first_chats: dict[int, datetime] = {}
    latest_subscriptions: dict[int, Subscription] = {}
    checkout_user_ids: set[int] = set()

    if new_user_ids:
        first_uploads = {
            user_id: first_at
            for user_id, first_at in (
                db.query(V2Document.user_id, func.min(V2Document.created_at))
                .filter(V2Document.user_id.in_(new_user_ids))
                .group_by(V2Document.user_id)
                .all()
            )
        }
        first_chats = {
            user_id: first_at
            for user_id, first_at in (
                db.query(ChatSession.user_id, func.min(ChatSession.created_at))
                .filter(ChatSession.user_id.in_(new_user_ids))
                .group_by(ChatSession.user_id)
                .all()
            )
        }
        for subscription in (
            db.query(Subscription)
            .filter(Subscription.user_id.in_(new_user_ids))
            .order_by(Subscription.user_id, Subscription.created_at.desc())
            .all()
        ):
            latest_subscriptions.setdefault(subscription.user_id, subscription)
        checkout_user_ids = {
            user_id
            for (user_id,) in (
                db.query(Payment.user_id)
                .filter(
                    Payment.user_id.in_(new_user_ids),
                    Payment.created_at >= start,
                    Payment.created_at < end,
                )
                .distinct()
                .all()
            )
        }

    activated_ids = set(first_uploads) | set(first_chats)
    verified_ids = {user.id for user in new_users if user.email_verified_at is not None}
    new_subscriber_ids = {
        subscription.user_id
        for subscription in latest_subscriptions.values()
        if subscription.status in {"active", "trialing"}
        and subscription.created_at >= start
        and subscription.created_at < end
    }

    landing_visitors = (
        db.query(func.count(func.distinct(AnalyticsEvent.anonymous_id)))
        .filter(
            AnalyticsEvent.event_name == "landing_view",
            AnalyticsEvent.created_at >= start,
            AnalyticsEvent.created_at < end,
        )
        .scalar()
        or 0
    )
    auth_visitors = (
        db.query(func.count(func.distinct(AnalyticsEvent.anonymous_id)))
        .filter(
            AnalyticsEvent.event_name == "auth_view",
            AnalyticsEvent.created_at >= start,
            AnalyticsEvent.created_at < end,
        )
        .scalar()
        or 0
    )

    series: dict[date, dict[str, int]] = defaultdict(
        lambda: {"registered": 0, "verified": 0, "activated": 0}
    )
    cursor = date_from
    while cursor <= date_to:
        series[cursor]
        cursor += timedelta(days=1)
    for user in new_users:
        bucket = series[user.created_at.date()]
        bucket["registered"] += 1
        bucket["verified"] += int(user.id in verified_ids)
        bucket["activated"] += int(user.id in activated_ids)

    revenue = {
        currency or "USD": float(amount or 0)
        for currency, amount in (
            db.query(Payment.currency, func.sum(Payment.amount))
            .filter(
                Payment.status == "completed",
                Payment.created_at >= start,
                Payment.created_at < end,
            )
            .group_by(Payment.currency)
            .all()
        )
    }
    errors_15m = (
        db.query(func.count(AuditLog.id))
        .filter(
            AuditLog.status != "success",
            AuditLog.created_at >= datetime.utcnow() - timedelta(minutes=15),
        )
        .scalar()
        or 0
    )
    last_event_at = db.query(func.max(AnalyticsEvent.created_at)).scalar()

    recent_users = []
    for user in new_users[:30]:
        subscription = latest_subscriptions.get(user.id)
        recent_users.append(
            {
                "id": user.id,
                "email": _mask_email(user.email),
                "registeredAt": _iso(user.created_at),
                "verifiedAt": _iso(user.email_verified_at),
                "firstUploadAt": _iso(first_uploads.get(user.id)),
                "firstChatAt": _iso(first_chats.get(user.id)),
                "subscription": subscription.status if subscription else "none",
            }
        )

    return {
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "totals": {
            "users": db.query(func.count(User.id)).scalar() or 0,
            "activeSubscriptions": (
                db.query(func.count(func.distinct(Subscription.user_id)))
                .filter(Subscription.status.in_(["active", "trialing"]))
                .scalar()
                or 0
            ),
            "revenue": revenue,
        },
        "funnel": {
            "visitors": landing_visitors,
            "access": auth_visitors,
            "registered": len(new_users),
            "verified": len(verified_ids),
            "activated": len(activated_ids),
            "checkout": len(checkout_user_ids),
            "subscriptions": len(new_subscriber_ids),
        },
        "series": [
            {"date": day.isoformat(), **values}
            for day, values in sorted(series.items())
        ],
        "recentUsers": recent_users,
        "system": {
            "database": "ok",
            "errors15m": errors_15m,
            "generatedAt": _iso(datetime.utcnow()),
            "lastEventAt": _iso(last_event_at),
            "trackingSince": _iso(db.query(func.min(AnalyticsEvent.created_at)).scalar()),
        },
    }
