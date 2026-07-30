"""Usage entitlements shared by uploads, billing status and the patient AI chat."""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import os

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import AiUsagePeriod, Subscription, User


ACTIVE_SUBSCRIPTION_STATUSES = ("active", "trialing")
DEFAULT_AI_MONTHLY_LIMIT = 20
DEFAULT_AI_TRIAL_LIMIT = 5
DEFAULT_AI_CHART_DAILY_LIMIT = 5


def _positive_env_int(name: str, default: int) -> int:
    try:
        return max(1, int((os.getenv(name) or str(default)).strip()))
    except (TypeError, ValueError):
        return default


def active_subscription_for_user(db: Session, user_id: int) -> Subscription | None:
    return (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status.in_(ACTIVE_SUBSCRIPTION_STATUSES),
        )
        .order_by(Subscription.id.desc())
        .first()
    )


@dataclass(frozen=True)
class UploadAllowance:
    limit: int
    used: int
    remaining: int
    has_subscription: bool
    can_upload: bool


def get_upload_allowance(db: Session, user_id: int) -> UploadAllowance:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return UploadAllowance(limit=0, used=0, remaining=0, has_subscription=False, can_upload=False)
    limit = max(0, int(user.free_upload_limit or 0))
    used = min(limit, max(0, int(user.free_uploads_used or 0)))
    remaining = max(0, limit - used)
    subscribed = active_subscription_for_user(db, user_id) is not None
    return UploadAllowance(
        limit=limit,
        used=used,
        remaining=remaining,
        has_subscription=subscribed,
        can_upload=subscribed or remaining > 0 or bool(user.is_doctor),
    )


def reserve_free_upload(db: Session, user_id: int) -> UploadAllowance | None:
    """Atomically reserve one free upload and return the updated allowance."""
    updated = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.free_uploads_used < User.free_upload_limit,
        )
        .update(
            {User.free_uploads_used: User.free_uploads_used + 1},
            synchronize_session=False,
        )
    )
    db.commit()
    if updated != 1:
        return None
    return get_upload_allowance(db, user_id)


def refund_free_upload(db: Session, user_id: int) -> None:
    db.query(User).filter(
        User.id == user_id,
        User.free_uploads_used > 0,
    ).update(
        {User.free_uploads_used: User.free_uploads_used - 1},
        synchronize_session=False,
    )
    db.commit()


@dataclass(frozen=True)
class AiAllowance:
    limit: int
    used: int
    remaining: int
    reset_at: dt.datetime | None
    period_key: str | None
    subscription_id: int | None
    is_trial: bool


def _next_month_start(now: dt.datetime) -> dt.datetime:
    if now.month == 12:
        return dt.datetime(now.year + 1, 1, 1)
    return dt.datetime(now.year, now.month + 1, 1)


def _ai_period(
    subscription: Subscription,
    now: dt.datetime,
) -> tuple[str, dt.datetime, dt.datetime | None, int, bool]:
    if subscription.status == "trialing":
        start = subscription.period_start or subscription.created_at or now
        end = subscription.trial_end or subscription.period_end
        return (
            f"trial:{subscription.id}",
            start,
            end,
            _positive_env_int("AI_TRIAL_MESSAGE_LIMIT", DEFAULT_AI_TRIAL_LIMIT),
            True,
        )
    start = dt.datetime(now.year, now.month, 1)
    return (
        f"month:{start:%Y-%m}",
        start,
        _next_month_start(now),
        _positive_env_int("AI_MONTHLY_MESSAGE_LIMIT", DEFAULT_AI_MONTHLY_LIMIT),
        False,
    )


def get_ai_allowance(
    db: Session,
    user_id: int,
    *,
    now: dt.datetime | None = None,
) -> AiAllowance:
    current = now or dt.datetime.utcnow()
    subscription = active_subscription_for_user(db, user_id)
    if subscription is None:
        return AiAllowance(
            limit=0,
            used=0,
            remaining=0,
            reset_at=None,
            period_key=None,
            subscription_id=None,
            is_trial=False,
        )
    period_key, _start, end, limit, is_trial = _ai_period(subscription, current)
    usage = (
        db.query(AiUsagePeriod)
        .filter(
            AiUsagePeriod.user_id == user_id,
            AiUsagePeriod.period_key == period_key,
        )
        .first()
    )
    used = max(0, int(usage.messages_used or 0)) if usage else 0
    return AiAllowance(
        limit=limit,
        used=used,
        remaining=max(0, limit - used),
        reset_at=end,
        period_key=period_key,
        subscription_id=subscription.id if subscription else None,
        is_trial=is_trial,
    )


def _ensure_ai_usage_row(
    db: Session,
    *,
    user_id: int,
    period_key: str,
    period_start: dt.datetime,
    period_end: dt.datetime | None,
) -> None:
    existing = (
        db.query(AiUsagePeriod.id)
        .filter(
            AiUsagePeriod.user_id == user_id,
            AiUsagePeriod.period_key == period_key,
        )
        .first()
    )
    if existing:
        return
    db.add(
        AiUsagePeriod(
            user_id=user_id,
            period_key=period_key,
            period_start=period_start,
            period_end=period_end,
            messages_used=0,
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()


def reserve_ai_message(
    db: Session,
    user_id: int,
    *,
    now: dt.datetime | None = None,
) -> AiAllowance | None:
    """Atomically reserve one chat message; return None when the allowance is exhausted."""
    current = now or dt.datetime.utcnow()
    subscription = active_subscription_for_user(db, user_id)
    if subscription is None:
        return None
    period_key, start, end, limit, _is_trial = _ai_period(subscription, current)
    if not _reserve_usage_period(
        db,
        user_id=user_id,
        period_key=period_key,
        period_start=start,
        period_end=end,
        limit=limit,
        now=current,
    ):
        return None
    return get_ai_allowance(db, user_id, now=current)


def _reserve_usage_period(
    db: Session,
    *,
    user_id: int,
    period_key: str,
    period_start: dt.datetime,
    period_end: dt.datetime | None,
    limit: int,
    now: dt.datetime,
) -> bool:
    _ensure_ai_usage_row(
        db,
        user_id=user_id,
        period_key=period_key,
        period_start=period_start,
        period_end=period_end,
    )
    updated = (
        db.query(AiUsagePeriod)
        .filter(
            AiUsagePeriod.user_id == user_id,
            AiUsagePeriod.period_key == period_key,
            AiUsagePeriod.messages_used < limit,
        )
        .update(
            {
                AiUsagePeriod.messages_used: AiUsagePeriod.messages_used + 1,
                AiUsagePeriod.updated_at: now,
            },
            synchronize_session=False,
        )
    )
    db.commit()
    return updated == 1


def reserve_chart_advice(
    db: Session,
    user_id: int,
    *,
    now: dt.datetime | None = None,
) -> AiAllowance | None:
    """Reserve one non-persistent chart insight under a separate daily cap."""
    current = now or dt.datetime.utcnow()
    subscription = active_subscription_for_user(db, user_id)
    if subscription is None:
        return None
    start = dt.datetime(current.year, current.month, current.day)
    end = start + dt.timedelta(days=1)
    limit = _positive_env_int("AI_CHART_DAILY_LIMIT", DEFAULT_AI_CHART_DAILY_LIMIT)
    period_key = f"chart:{start:%Y-%m-%d}"
    if not _reserve_usage_period(
        db,
        user_id=user_id,
        period_key=period_key,
        period_start=start,
        period_end=end,
        limit=limit,
        now=current,
    ):
        return None
    return get_chart_allowance(db, user_id, now=current)


def get_chart_allowance(
    db: Session,
    user_id: int,
    *,
    now: dt.datetime | None = None,
) -> AiAllowance:
    current = now or dt.datetime.utcnow()
    subscription = active_subscription_for_user(db, user_id)
    start = dt.datetime(current.year, current.month, current.day)
    end = start + dt.timedelta(days=1)
    limit = _positive_env_int("AI_CHART_DAILY_LIMIT", DEFAULT_AI_CHART_DAILY_LIMIT)
    period_key = f"chart:{start:%Y-%m-%d}"
    usage = (
        db.query(AiUsagePeriod)
        .filter(
            AiUsagePeriod.user_id == user_id,
            AiUsagePeriod.period_key == period_key,
        )
        .first()
    )
    used = int(usage.messages_used or 0) if usage else 0
    return AiAllowance(
        limit=limit,
        used=used,
        remaining=max(0, limit - used),
        reset_at=end,
        period_key=period_key,
        subscription_id=subscription.id if subscription else None,
        is_trial=bool(subscription and subscription.status == "trialing"),
    )


def refund_ai_message(db: Session, user_id: int, period_key: str | None) -> None:
    if not period_key:
        return
    db.query(AiUsagePeriod).filter(
        AiUsagePeriod.user_id == user_id,
        AiUsagePeriod.period_key == period_key,
        AiUsagePeriod.messages_used > 0,
    ).update(
        {
            AiUsagePeriod.messages_used: AiUsagePeriod.messages_used - 1,
            AiUsagePeriod.updated_at: dt.datetime.utcnow(),
        },
        synchronize_session=False,
    )
    db.commit()
