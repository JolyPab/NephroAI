"""Email delivery helpers for verification codes."""

from __future__ import annotations

import logging
import os
import smtplib
from html import escape
from email.message import EmailMessage
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


def _public_app_url() -> str:
    configured_url = (os.getenv("APP_PUBLIC_URL") or os.getenv("FRONTEND_PUBLIC_URL") or "").strip()
    if configured_url:
        return configured_url.rstrip("/")
    app_env = (os.getenv("ENV") or os.getenv("APP_ENV") or "development").strip().lower()
    return "https://app.nephroai.ec" if app_env in {"prod", "production"} else "http://localhost:4200"


def _verification_link(email: str) -> str:
    query = urlencode({"mode": "verify", "email": email})
    return f"{_public_app_url()}/auth?{query}"


def send_verification_code_email(email: str, code: str, purpose: str = "email_verification") -> None:
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

    is_reset = purpose == "password_reset"
    subject = "NephroAI - codigo de verificacion"
    if is_reset:
        body = (
            "Usa este codigo para restablecer tu contrasena:\n\n"
            f"{code}\n\n"
            "El codigo vence en 10 minutos.\n"
            "Si no solicitaste esto, puedes ignorar este correo."
        )
        html_body = f"""
        <div style="font-family:Arial,sans-serif;color:#10202a;line-height:1.5">
          <h2 style="margin:0 0 12px">Restablece tu contrasena en NephroAI</h2>
          <p>Usa este codigo para continuar:</p>
          <p style="font-size:28px;letter-spacing:8px;font-weight:700;margin:20px 0">{escape(code)}</p>
          <p>El codigo vence en 10 minutos. Si no solicitaste esto, puedes ignorar este correo.</p>
        </div>
        """
    else:
        link = _verification_link(email)
        body = (
            "Gracias por registrarte en NephroAI.\n\n"
            "1. Abre esta pagina para volver a la verificacion:\n"
            f"{link}\n\n"
            "2. Ingresa este codigo:\n\n"
            f"{code}\n\n"
            "El codigo vence en 10 minutos.\n"
            "Si no solicitaste esto, puedes ignorar este correo."
        )
        html_body = f"""
        <div style="font-family:Arial,sans-serif;color:#10202a;line-height:1.5">
          <h2 style="margin:0 0 12px">Confirma tu correo en NephroAI</h2>
          <p>Gracias por registrarte. Toca el boton para volver a la pantalla de verificacion.</p>
          <p style="margin:24px 0">
            <a href="{escape(link)}" style="background:#0f766e;color:#ffffff;padding:14px 22px;border-radius:8px;text-decoration:none;font-weight:700;display:inline-block">
              Abrir verificacion
            </a>
          </p>
          <p>Luego ingresa este codigo:</p>
          <p style="font-size:28px;letter-spacing:8px;font-weight:700;margin:20px 0">{escape(code)}</p>
          <p>El codigo vence en 10 minutos. Si no solicitaste esto, puedes ignorar este correo.</p>
        </div>
        """

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
    msg.add_alternative(html_body, subtype="html")

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
