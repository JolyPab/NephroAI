"""Email delivery helpers for verification codes."""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def send_verification_code_email(email: str, code: str) -> None:
    """
    Send a verification code email.

    If SMTP is not configured, logs the code and returns successfully.
    This keeps local/dev environments working without external email setup.
    """
    smtp_host = (os.getenv("SMTP_HOST") or "").strip()
    smtp_port = int((os.getenv("SMTP_PORT") or "587").strip())
    smtp_user = (os.getenv("SMTP_USERNAME") or "").strip()
    smtp_password = (os.getenv("SMTP_PASSWORD") or "").strip()
    smtp_from = (os.getenv("SMTP_FROM_EMAIL") or smtp_user or "no-reply@localhost").strip()
    smtp_use_tls = (os.getenv("SMTP_USE_TLS") or "true").strip().lower() in {"1", "true", "yes"}
    smtp_require = (os.getenv("SMTP_REQUIRE_DELIVERY") or "false").strip().lower() in {"1", "true", "yes"}
    app_env = (os.getenv("ENV") or os.getenv("APP_ENV") or "development").strip().lower()
    allow_dev_fallback = app_env not in {"prod", "production"} and not smtp_require

    subject = "NephroAI - verification code"
    body = (
        "Use this code to verify your email:\n\n"
        f"{code}\n\n"
        "The code expires in 10 minutes.\n"
        "If you did not request this, you can ignore this email."
    )

    if not smtp_host:
        logger.warning(
            "SMTP not configured. Verification code for %s: %s",
            email,
            code,
        )
        if smtp_require:
            raise RuntimeError("SMTP is not configured")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = email
    msg.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            if smtp_use_tls:
                server.starttls()
            if smtp_user:
                server.login(smtp_user, smtp_password)
            server.send_message(msg)
    except (OSError, smtplib.SMTPException):
        if not allow_dev_fallback:
            raise
        logger.warning(
            "SMTP delivery failed in %s. Verification code for %s: %s",
            app_env,
            email,
            code,
            exc_info=True,
        )
