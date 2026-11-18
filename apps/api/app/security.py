import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import AppError
from app.models import AuditLog, Role, Session as DbSession, User

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def client_ip(request_client: str | None) -> str | None:
    return request_client


def write_audit(
    db: Session,
    *,
    action: str,
    actor_id=None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict | None = None,
    ip: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata,
            ip=ip,
        )
    )


def _domain_allowed(settings: Settings, email: str) -> bool:
    allowed = settings.allowed_domain_set
    if not allowed:
        return True
    domain = email.split("@")[-1].lower()
    return domain in allowed


def upsert_user(db: Session, settings: Settings, *, email: str, name: str, avatar_url: str | None, google_sub: str | None) -> User:
    email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if google_sub:
        by_sub = db.scalar(select(User).where(User.google_sub == google_sub))
        if by_sub and user and by_sub.id != user.id:
            raise AppError(409, "account_conflict", "This Google account is already linked to another user")
        user = user or by_sub
    if user is None:
        if email not in settings.admin_email_set and not _domain_allowed(settings, email):
            raise AppError(403, "domain_not_allowed", "This email domain is not allowed to join")
        user = User(email=email, name=name.strip() or email.split("@")[0], avatar_url=avatar_url, google_sub=google_sub)
        if email in settings.admin_email_set:
            user.role = Role.super_admin.value
        db.add(user)
        db.flush()
        return user
    user.name = name.strip() or user.name
    if avatar_url:
        user.avatar_url = avatar_url
    if google_sub:
        user.google_sub = google_sub
    if email in settings.admin_email_set and user.role == Role.student.value:
        user.role = Role.super_admin.value
    return user


def start_session(db: Session, settings: Settings, user: User, response: Response) -> None:
    token = secrets.token_urlsafe(32)
    db.add(
        DbSession(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC) + timedelta(days=settings.session_ttl_days),
        )
    )
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        path="/",
    )


def clear_session(db: Session, settings: Settings, token: str | None, response: Response) -> None:
    if token:
        row = db.scalar(select(DbSession).where(DbSession.token_hash == hash_token(token)))
        if row:
            db.delete(row)
    response.delete_cookie(settings.session_cookie_name, path="/")


def current_user(db: Session, settings: Settings, token: str | None) -> User | None:
    if not token:
        return None
    row = db.scalar(select(DbSession).where(DbSession.token_hash == hash_token(token)))
    if row is None or row.expires_at <= datetime.now(UTC):
        return None
    return db.get(User, row.user_id)


def google_auth_url(settings: Settings, state: str) -> str:
    if not settings.google_client_id or not settings.google_client_secret:
        raise AppError(503, "oauth_unconfigured", "Google sign-in is not configured")
    query = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        }
    )
    return f"{GOOGLE_AUTH}?{query}"


def google_userinfo(settings: Settings, code: str) -> dict:
    response = httpx.post(
        GOOGLE_TOKEN,
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    if response.status_code != 200:
        raise AppError(401, "oauth_failed", "Google did not accept the sign-in")
    access = response.json().get("access_token")
    if not access:
        raise AppError(401, "oauth_failed", "Google did not return an access token")
    info = httpx.get(GOOGLE_USERINFO, headers={"Authorization": f"Bearer {access}"}, timeout=15)
    if info.status_code != 200:
        raise AppError(401, "oauth_failed", "Google did not return a profile")
    payload = info.json()
    if not payload.get("email") or not payload.get("email_verified"):
        raise AppError(403, "email_unverified", "A verified Google email is required")
    return payload


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or "hackathon"
