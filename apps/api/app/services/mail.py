"""Outbound mail. Brevo is used when its key is set; Resend remains the fallback."""

import re

import httpx

from app.config import Settings

_FROM = re.compile(r"^\s*(.*?)\s*<([^>]+)>\s*$")


def sender_parts(raw: str) -> tuple[str, str]:
    match = _FROM.match(raw or "")
    if match:
        name = match.group(1).strip().strip('"') or "HackHub"
        return name, match.group(2).strip()
    address = (raw or "").strip()
    return "HackHub", address


def deliver(settings: Settings, to: str, subject: str, text: str) -> tuple[bool, str | None]:
    """Send one message. (False, None) means no provider is configured."""
    if settings.brevo_api_key:
        return _brevo(settings, to, subject, text)
    if settings.resend_api_key:
        return _resend(settings, to, subject, text)
    return False, None


def _brevo(settings: Settings, to: str, subject: str, text: str) -> tuple[bool, str | None]:
    name, address = sender_parts(settings.resend_from)
    try:
        response = httpx.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": settings.brevo_api_key, "accept": "application/json"},
            json={
                "sender": {"name": name, "email": address},
                "to": [{"email": to}],
                "subject": subject,
                "textContent": text,
            },
            timeout=10,
        )
    except httpx.HTTPError as exc:
        return False, str(exc)[:300]
    if response.status_code >= 400:
        return False, response.text[:300]
    return True, None


def _resend(settings: Settings, to: str, subject: str, text: str) -> tuple[bool, str | None]:
    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={"from": settings.resend_from, "to": [to], "subject": subject, "text": text},
            timeout=10,
        )
    except httpx.HTTPError as exc:
        return False, str(exc)[:300]
    if response.status_code >= 400:
        return False, response.text[:300]
    return True, None
