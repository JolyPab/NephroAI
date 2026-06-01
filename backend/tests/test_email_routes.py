import asyncio
import base64
import datetime as dt
import hashlib
import hmac
import json

import pytest
from fastapi import HTTPException

from backend import email_routes


class _FakeRequest:
    def __init__(self, payload: bytes, headers: dict[str, str]):
        self._payload = payload
        self.headers = headers

    async def body(self):
        return self._payload


def _signed_headers(payload: bytes, secret: bytes) -> dict[str, str]:
    svix_id = "msg_test_123"
    svix_timestamp = str(int(dt.datetime.now(dt.timezone.utc).timestamp()))
    signed_payload = f"{svix_id}.{svix_timestamp}.".encode("utf-8") + payload
    signature = base64.b64encode(hmac.new(secret, signed_payload, hashlib.sha256).digest()).decode("utf-8")
    return {
        "svix-id": svix_id,
        "svix-timestamp": svix_timestamp,
        "svix-signature": f"v1,{signature}",
    }


def test_resend_inbound_webhook_forwards_received_email(monkeypatch):
    secret = b"test-webhook-secret"
    payload = json.dumps({"type": "email.received", "data": {"email_id": "email_123"}}).encode("utf-8")
    forwarded_payloads = []

    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", f"whsec_{base64.b64encode(secret).decode('utf-8')}")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("RESEND_INBOUND_FORWARD_TO", "picoyamid@gmail.com")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "NephroAI <noreply@nephroai.ec>")
    monkeypatch.setenv("RESEND_INBOUND_FORWARD_ATTACHMENTS", "false")
    monkeypatch.setattr(
        email_routes,
        "_get_received_email",
        lambda _email_id: {
            "id": "email_123",
            "from": "Paciente <patient@example.com>",
            "to": ["info@nephroai.ec"],
            "created_at": "2026-06-01T10:00:00Z",
            "subject": "Consulta",
            "text": "Hola, quiero informacion.",
            "html": None,
            "attachments": [],
        },
    )

    def _fake_send_forward_email(forward_payload):
        forwarded_payloads.append(forward_payload)
        return {"id": "sent_123"}

    monkeypatch.setattr(email_routes, "_send_forward_email", _fake_send_forward_email)

    response = asyncio.run(
        email_routes.resend_inbound_webhook(_FakeRequest(payload, _signed_headers(payload, secret)))
    )

    assert response == {"received": True, "forwarded": True, "forward_id": "sent_123"}
    assert forwarded_payloads[0]["to"] == ["picoyamid@gmail.com"]
    assert forwarded_payloads[0]["reply_to"] == ["Paciente <patient@example.com>"]
    assert forwarded_payloads[0]["subject"] == "[NephroAI] Consulta"
    assert "Hola, quiero informacion." in forwarded_payloads[0]["text"]


def test_resend_inbound_webhook_rejects_bad_signature(monkeypatch):
    payload = json.dumps({"type": "email.received", "data": {"email_id": "email_123"}}).encode("utf-8")
    headers = _signed_headers(payload, b"correct-secret")

    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", f"whsec_{base64.b64encode(b'wrong-secret').decode('utf-8')}")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(email_routes.resend_inbound_webhook(_FakeRequest(payload, headers)))

    assert exc_info.value.status_code == 400
