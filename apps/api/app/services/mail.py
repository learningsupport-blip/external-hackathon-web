"""Outbound mail through Resend. Set RESEND_FROM to an address on the verified domain."""

import httpx

from app.config import Settings


def deliver(settings: Settings, to: str, subject: str, text: str) -> tuple[bool, str | None]:
    """Send one message. (False, None) means Resend is not configured."""
    if not settings.resend_api_key:
        return False, None
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
