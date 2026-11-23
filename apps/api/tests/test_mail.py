from types import SimpleNamespace

from app.services.mail import deliver


def test_resend_sends_when_its_key_is_set(monkeypatch):
    captured = {}

    class Response:
        status_code = 200
        text = ""

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr("app.services.mail.httpx.post", fake_post)
    settings = SimpleNamespace(
        resend_api_key="re_test",
        resend_from="HackHub <notifications@example.com>",
    )
    sent, detail = deliver(settings, "student@example.com", "Your HackHub verification code", "code 123456")
    assert sent is True
    assert detail is None
    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["headers"]["Authorization"] == "Bearer re_test"
    assert captured["json"] == {
        "from": "HackHub <notifications@example.com>",
        "to": ["student@example.com"],
        "subject": "Your HackHub verification code",
        "text": "code 123456",
    }


def test_deliver_skips_when_resend_is_not_configured():
    settings = SimpleNamespace(resend_api_key="", resend_from="HackHub <onboarding@resend.dev>")
    sent, detail = deliver(settings, "student@example.com", "Subject", "Body")
    assert sent is False
    assert detail is None
