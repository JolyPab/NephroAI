"""Inbound email routes for Resend receiving webhooks."""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import html
import json
import logging
import os
from typing import Any

import requests
from fastapi import APIRouter, HTTPException, Request, status

router = APIRouter(prefix="/api/email", tags=["email"])
logger = logging.getLogger(__name__)

RESEND_API_BASE = "https://api.resend.com"
MAX_FORWARD_ATTACHMENT_BYTES = 25 * 1024 * 1024


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _resend_api_key() -> str:
    api_key = (os.getenv("RESEND_API_KEY") or "").strip()
    if not api_key:
        smtp_password = (os.getenv("SMTP_PASSWORD") or "").strip()
        if smtp_password.startswith("re_"):
            api_key = smtp_password
    if not api_key:
        raise HTTPException(status_code=500, detail="RESEND_API_KEY is not configured.")
    return api_key


def _decode_svix_secret(secret: str) -> bytes:
    value = secret.strip()
    if value.startswith("whsec_"):
        value = value.split("_", 1)[1]
    try:
        return base64.b64decode(value)
    except Exception:
        return value.encode("utf-8")


def _svix_signatures(header_value: str) -> list[str]:
    signatures: list[str] = []
    for item in header_value.split():
        try:
            version, signature = item.split(",", 1)
        except ValueError:
            continue
        if version == "v1" and signature:
            signatures.append(signature)
    return signatures


def _verify_resend_webhook(payload: bytes, headers: dict[str, str]) -> None:
    webhook_secret = (os.getenv("RESEND_WEBHOOK_SECRET") or "").strip()
    if not webhook_secret:
        raise HTTPException(status_code=500, detail="RESEND_WEBHOOK_SECRET is not configured.")

    svix_id = headers.get("svix-id") or headers.get("Svix-Id")
    svix_timestamp = headers.get("svix-timestamp") or headers.get("Svix-Timestamp")
    svix_signature = headers.get("svix-signature") or headers.get("Svix-Signature")
    if not svix_id or not svix_timestamp or not svix_signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Resend webhook headers.")

    try:
        timestamp = int(svix_timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Resend webhook timestamp.") from exc

    tolerance_seconds = int((os.getenv("RESEND_WEBHOOK_TOLERANCE_SECONDS") or "300").strip())
    now = int(dt.datetime.now(dt.timezone.utc).timestamp())
    if abs(now - timestamp) > tolerance_seconds:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stale Resend webhook timestamp.")

    signed_payload = f"{svix_id}.{svix_timestamp}.".encode("utf-8") + payload
    expected = base64.b64encode(
        hmac.new(_decode_svix_secret(webhook_secret), signed_payload, hashlib.sha256).digest()
    ).decode("utf-8")

    if not any(hmac.compare_digest(expected, signature) for signature in _svix_signatures(svix_signature)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Resend webhook signature.")


def _resend_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_resend_api_key()}",
        "Content-Type": "application/json",
    }


def _get_received_email(email_id: str) -> dict[str, Any]:
    response = requests.get(
        f"{RESEND_API_BASE}/emails/receiving/{email_id}",
        headers=_resend_headers(),
        timeout=20,
    )
    if response.status_code >= 400:
        logger.error("Resend received email fetch failed: %s %s", response.status_code, response.text[:500])
        raise HTTPException(status_code=502, detail="Could not fetch received email from Resend.")
    return response.json()


def _download_attachment(email_id: str, attachment_id: str) -> dict[str, Any] | None:
    metadata_response = requests.get(
        f"{RESEND_API_BASE}/emails/receiving/{email_id}/attachments/{attachment_id}",
        headers=_resend_headers(),
        timeout=20,
    )
    if metadata_response.status_code >= 400:
        logger.warning("Resend attachment metadata fetch failed: %s", metadata_response.status_code)
        return None

    metadata = metadata_response.json()
    download_url = metadata.get("download_url")
    size = int(metadata.get("size") or 0)
    if not download_url or size > MAX_FORWARD_ATTACHMENT_BYTES:
        return None

    attachment_response = requests.get(download_url, timeout=30)
    if attachment_response.status_code >= 400:
        logger.warning("Resend attachment download failed: %s", attachment_response.status_code)
        return None

    content = base64.b64encode(attachment_response.content).decode("ascii")
    return {
        "filename": metadata.get("filename") or "attachment",
        "content": content,
        "content_type": metadata.get("content_type") or "application/octet-stream",
    }


def _build_forward_email(received_email: dict[str, Any]) -> dict[str, Any]:
    forward_to = (os.getenv("RESEND_INBOUND_FORWARD_TO") or "").strip()
    if not forward_to:
        raise HTTPException(status_code=500, detail="RESEND_INBOUND_FORWARD_TO is not configured.")

    forward_from = (
        os.getenv("RESEND_INBOUND_FORWARD_FROM")
        or os.getenv("SMTP_FROM_EMAIL")
        or "NephroAI <noreply@nephroai.ec>"
    ).strip()
    original_from = received_email.get("from") or "unknown"
    original_to = ", ".join(received_email.get("to") or [])
    original_subject = received_email.get("subject") or "(sin asunto)"
    original_text = received_email.get("text") or ""
    original_html = received_email.get("html")

    escaped_text = html.escape(original_text)
    body_html = original_html or f"<pre style=\"white-space:pre-wrap\">{escaped_text}</pre>"
    html_body = f"""
    <p><strong>Mensaje recibido en NephroAI</strong></p>
    <p>
      <strong>De:</strong> {html.escape(str(original_from))}<br>
      <strong>Para:</strong> {html.escape(original_to)}<br>
      <strong>Fecha:</strong> {html.escape(str(received_email.get("created_at") or ""))}
    </p>
    <hr>
    {body_html}
    """

    text_body = (
        "Mensaje recibido en NephroAI\n\n"
        f"De: {original_from}\n"
        f"Para: {original_to}\n"
        f"Fecha: {received_email.get('created_at') or ''}\n\n"
        f"{original_text or '[El mensaje original contiene solo HTML]'}"
    )

    payload: dict[str, Any] = {
        "from": forward_from,
        "to": [email.strip() for email in forward_to.split(",") if email.strip()],
        "subject": f"[NephroAI] {original_subject}",
        "html": html_body,
        "text": text_body,
        "reply_to": [original_from],
    }

    if _env_bool("RESEND_INBOUND_FORWARD_ATTACHMENTS", default=True):
        attachments = []
        for attachment in received_email.get("attachments") or []:
            attachment_id = attachment.get("id")
            email_id = received_email.get("id")
            if not attachment_id or not email_id:
                continue
            downloaded = _download_attachment(str(email_id), str(attachment_id))
            if downloaded:
                attachments.append(downloaded)
        if attachments:
            payload["attachments"] = attachments

    return payload


def _send_forward_email(payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        f"{RESEND_API_BASE}/emails",
        headers=_resend_headers(),
        data=json.dumps(payload),
        timeout=20,
    )
    if response.status_code >= 400:
        logger.error("Resend forward failed: %s %s", response.status_code, response.text[:500])
        raise HTTPException(status_code=502, detail="Could not forward inbound email.")
    return response.json()


@router.post("/resend/inbound")
async def resend_inbound_webhook(request: Request):
    payload = await request.body()
    _verify_resend_webhook(payload, dict(request.headers))

    try:
        event = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload.") from exc

    if event.get("type") != "email.received":
        return {"received": True, "ignored": True}

    email_id = ((event.get("data") or {}).get("email_id") or "").strip()
    if not email_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing received email id.")

    received_email = _get_received_email(email_id)
    forward_response = _send_forward_email(_build_forward_email(received_email))
    logger.info(
        "Forwarded inbound Resend email %s to %s",
        email_id,
        os.getenv("RESEND_INBOUND_FORWARD_TO", ""),
    )
    return {"received": True, "forwarded": True, "forward_id": forward_response.get("id")}
