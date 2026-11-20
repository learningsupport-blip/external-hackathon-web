import time
from datetime import UTC, datetime, timedelta

from starlette.requests import Request

from test_core import create_hackathon, login


def _request(host: str) -> Request:
    return Request({"type": "http", "method": "POST", "headers": [], "client": (host, 1234)})


def test_private_import_urls_are_rejected():
    from app.errors import AppError
    from app.services.importing import assert_public_http_url

    for url in ("http://127.0.0.1/admin", "http://10.1.1.1/secret", "http://localhost/hack", "http://169.254.169.254/"):
        try:
            assert_public_http_url(url)
        except AppError as exc:
            assert exc.status_code == 422
            assert exc.code == "blocked_url"
            continue
        raise AssertionError(f"{url} was accepted")


def test_failed_update_keeps_the_saved_description(client):
    login(client, "admin@hackhub.test")
    created = create_hackathon(client, name="Rollback Cup")
    saved = client.patch(
        f"/api/v1/admin/hackathons/{created['id']}",
        json={"short_description": "Keep this"},
    )
    assert saved.status_code == 200, saved.text
    rejected = client.patch(
        f"/api/v1/admin/hackathons/{created['id']}",
        json={"short_description": "This must not stick", "min_team_size": 8, "max_team_size": 2},
    )
    assert rejected.status_code == 422
    again = client.get(f"/api/v1/admin/hackathons/{created['id']}")
    assert again.status_code == 200
    assert again.json()["short_description"] == "Keep this"


def test_rate_limit_forgets_expired_visitors():
    from app.deps import _hits, rate_limit

    _hits.clear()
    rate_limit(_request("203.0.113.8"), "leak-check", limit=5, window=0.05)
    assert "leak-check:203.0.113.8" in _hits
    time.sleep(0.06)
    rate_limit(_request("203.0.113.9"), "leak-check", limit=5, window=0.05)
    assert "leak-check:203.0.113.8" not in _hits
    assert "leak-check:203.0.113.9" in _hits
    _hits.pop("leak-check:203.0.113.9", None)


def test_expired_sessions_and_codes_are_removed():
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models import EmailVerification, Session as DbSession, User
    from app.services.accounts import purge_expired

    db = SessionLocal()
    try:
        user = User(email="expired@example.com", name="Expired")
        db.add(user)
        db.flush()
        db.add(
            DbSession(
                user_id=user.id,
                token_hash="a" * 64,
                expires_at=datetime.now(UTC) - timedelta(minutes=1),
            )
        )
        db.add(
            EmailVerification(
                email="expired@example.com",
                code_hash="b" * 64,
                expires_at=datetime.now(UTC) - timedelta(minutes=1),
            )
        )
        db.commit()
        purge_expired(db)
        db.commit()
        assert db.scalar(select(DbSession).where(DbSession.token_hash == "a" * 64)) is None
        assert db.get(EmailVerification, "expired@example.com") is None
        assert db.scalar(select(User).where(User.email == "expired@example.com")) is not None
    finally:
        db.close()
