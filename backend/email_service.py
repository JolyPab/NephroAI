"""Transactional email delivery helpers."""

from __future__ import annotations

import logging
import os
import smtplib
import requests
from html import escape
from email.message import EmailMessage
from email.utils import parseaddr
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

RESEND_API_BASE = "https://api.resend.com"


def _public_app_url() -> str:
    configured_url = (os.getenv("APP_PUBLIC_URL") or os.getenv("FRONTEND_PUBLIC_URL") or "").strip()
    if configured_url:
        return configured_url.rstrip("/")
    app_env = (os.getenv("ENV") or os.getenv("APP_ENV") or "development").strip().lower()
    return "https://app.nephroai.ec" if app_env in {"prod", "production"} else "http://localhost:4200"


def _verification_link(email: str) -> str:
    query = urlencode({"mode": "verify", "email": email})
    return f"{_public_app_url()}/auth?{query}"


def _password_reset_link(email: str) -> str:
    query = urlencode({"mode": "reset-verify", "email": email})
    return f"{_public_app_url()}/auth?{query}"


def _welcome_sender() -> str:
    configured = (os.getenv("SMTP_FROM_EMAIL") or "").strip()
    if not configured:
        raise RuntimeError("SMTP_FROM_EMAIL is not configured")
    address = parseaddr(configured)[1]
    if not address:
        raise RuntimeError("SMTP_FROM_EMAIL is invalid")
    return f"NephroAI <{address}>"


def send_subscriber_welcome_email(
    email: str,
    *,
    is_trial: bool,
    idempotency_key: str,
) -> None:
    """Send a subscriber welcome email through Resend with provider idempotency."""
    api_key = (os.getenv("RESEND_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not configured")

    app_url = _public_app_url()
    phase_text = (
        "Tu período de prueba ya comenzó. Puedes explorar NephroAI desde hoy."
        if is_trial
        else "Tu suscripción ya está activa. Gracias por confiar en NephroAI."
    )
    subject = "¡Bienvenido(a) a NephroAI! 💙"
    text_body = (
        "¡Hola!\n\n"
        "Gracias por registrarte y dar este paso con NephroAI.\n\n"
        f"{phase_text}\n\n"
        "Con NephroAI puedes organizar tus análisis de laboratorio, consultar la evolución de "
        "tus resultados y recibir explicaciones claras para acompañar mejor el cuidado de tu salud.\n\n"
        f"Ingresa a la aplicación: {app_url}\n\n"
        "Si necesitas ayuda, responde directamente a este correo. Estaremos encantados de acompañarte.\n\n"
        "Equipo NephroAI"
    )
    html_body = f"""<!doctype html>
<html lang="es">
  <body style="margin:0;background:#f3f8fc;font-family:Arial,sans-serif;color:#17324d">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f3f8fc;padding:32px 12px">
      <tr><td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:600px;background:#ffffff;border-radius:18px;overflow:hidden;box-shadow:0 8px 28px rgba(23,50,77,.10)">
          <tr><td style="background:#e5f3ff;padding:30px 36px">
            <div style="font-size:14px;font-weight:700;color:#2775b6;letter-spacing:.4px">NEPHROAI</div>
            <h1 style="margin:10px 0 0;font-size:28px;line-height:1.25;color:#17324d">¡Te damos la bienvenida! 💙</h1>
          </td></tr>
          <tr><td style="padding:32px 36px;font-size:16px;line-height:1.65">
            <p style="margin:0 0 18px">¡Hola!</p>
            <p style="margin:0 0 18px">Gracias por registrarte y dar este paso con NephroAI.</p>
            <p style="margin:0 0 18px"><strong>{escape(phase_text)}</strong></p>
            <p style="margin:0 0 24px">Con NephroAI puedes organizar tus análisis de laboratorio, consultar la evolución de tus resultados y recibir explicaciones claras para acompañar mejor el cuidado de tu salud.</p>
            <p style="margin:26px 0;text-align:center">
              <a href="{escape(app_url)}" style="display:inline-block;background:#287fc0;color:#ffffff;text-decoration:none;font-weight:700;padding:14px 24px;border-radius:10px">Ir a NephroAI</a>
            </p>
            <p style="margin:24px 0 0">Si necesitas ayuda, responde directamente a este correo. Estaremos encantados de acompañarte.</p>
            <p style="margin:24px 0 0">Un abrazo,<br><strong>Equipo NephroAI</strong></p>
          </td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>"""

    response = requests.post(
        f"{RESEND_API_BASE}/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        },
        json={
            "from": _welcome_sender(),
            "to": [email],
            "subject": subject,
            "text": text_body,
            "html": html_body,
        },
        timeout=20,
    )
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"Resend welcome email failed with status {response.status_code}")


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
        link = _password_reset_link(email)
        body = (
            "Abre esta pagina para continuar con la recuperacion de tu contrasena:\n"
            f"{link}\n\n"
            "Luego usa este codigo:\n\n"
            f"{code}\n\n"
            "El codigo vence en 10 minutos.\n"
            "Si no solicitaste esto, puedes ignorar este correo."
        )
        html_body = f"""
        <div style="font-family:Arial,sans-serif;color:#10202a;line-height:1.5">
          <h2 style="margin:0 0 12px">Restablece tu contrasena en NephroAI</h2>
          <p>Toca el boton para volver a la pantalla de recuperacion.</p>
          <p style="margin:24px 0">
            <a href="{escape(link)}" style="background:#0f766e;color:#ffffff;padding:14px 22px;border-radius:8px;text-decoration:none;font-weight:700;display:inline-block">
              Continuar con la recuperacion
            </a>
          </p>
          <p>Luego ingresa este codigo:</p>
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
              Confirmar mi cuenta
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
