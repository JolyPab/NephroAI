"""Small, shared authorization helpers for the internal admin surface."""

import os

from fastapi import HTTPException, status


def admin_emails() -> set[str]:
    """Return the normalized allow-list configured in ``ADMIN_EMAILS``."""
    return {
        email.strip().lower()
        for email in (os.getenv("ADMIN_EMAILS") or "").split(",")
        if email.strip()
    }


def is_admin_email(email: str | None) -> bool:
    return bool(email) and email.strip().lower() in admin_emails()


def require_admin_email(email: str | None) -> None:
    if not is_admin_email(email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
