from types import SimpleNamespace

from app.services.mail import deliver, sender_parts


def test_sender_parts_split_a_named_address():
    assert sender_parts("HackHub <learning.support@nxtwave.co.in>") == (
        "HackHub",
        "learning.support@nxtwave.co.in",
    )


def test_brevo_sends_when_its_key_is_set(monkeypatch):
    captured = {}

    class Response:
        status_code = 201
        text = ""

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr("app.services.mail.httpx.post", fake_post)
    settings = SimpleNamespace(
        brevo_api_key="xkeysib-test",
        resend_api_key="re_test",
        resend_from="HackHub <learning.support@nxtwave.co.in>",
    )
    sent, detail = deliver(settings, "student@example.com", "Your HackHub verification code", "code 123456")
    assert sent is True
    assert detail is None
    assert captured["url"] == "https://api.brevo.com/v3/smtp/email"
    assert captured["headers"]["api-key"] == "xkeysib-test"
    assert captured["json"]["sender"] == {"name": "HackHub", "email": "learning.support@nxtwave.co.in"}
    assert captured["json"]["to"] == [{"email": "student@example.com"}]
    assert captured["json"]["textContent"] == "code 123456"


def test_resend_is_the_fallback_without_a_brevo_key(monkeypatch):
    captured = {}

    class Response:
        status_code = 200
        text = ""

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        return Response()

    monkeypatch.setattr("app.services.mail.httpx.post", fake_post)
    settings = SimpleNamespace(
        brevo_api_key="",
        resend_api_key="re_test",
        resend_from="HackHub <onboarding@resend.dev>",
    )
    sent, detail = deliver(settings, "learning.support@nxtwave.co.in", "Subject", "Body")
    assert sent is True
    assert detail is None
    assert captured["url"] == "https://api.resend.com/emails"
