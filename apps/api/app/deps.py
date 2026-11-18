import time
from collections import defaultdict

from fastapi import Request
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.errors import AppError
from app.models import Hackathon, HackathonAdmin, Role, User
from app.security import current_user

_hits: dict[str, list[float]] = defaultdict(list)


def rate_limit(request: Request, bucket: str, limit: int = 30, window: float = 600) -> None:
    ip = request.client.host if request.client else "unknown"
    key = f"{bucket}:{ip}"
    now = time.monotonic()
    recent = [stamp for stamp in _hits[key] if now - stamp < window]
    if len(recent) >= limit:
        raise AppError(429, "rate_limited", "Too many attempts. Wait a few minutes and try again.")
    recent.append(now)
    _hits[key] = recent


def check_origin(request: Request, settings: Settings | None = None) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    origin = request.headers.get("origin")
    if not origin:
        return
    settings = settings or get_settings()
    if origin.rstrip("/") != settings.web_origin.rstrip("/"):
        raise AppError(403, "bad_origin", "This request origin is not allowed")


def user_from_request(request: Request, db: Session, settings: Settings | None = None) -> User | None:
    settings = settings or get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    return current_user(db, settings, token)


def require_user(request: Request, db: Session) -> User:
    user = user_from_request(request, db)
    if user is None:
        raise AppError(401, "unauthenticated", "Sign in to continue")
    return user


def require_staff(user: User) -> None:
    if user.role not in {Role.coordinator.value, Role.super_admin.value}:
        raise AppError(403, "forbidden", "This action is limited to coordinators and administrators")


def require_super_admin(user: User) -> None:
    if user.role != Role.super_admin.value:
        raise AppError(403, "forbidden", "This action is limited to super administrators")


def can_edit(db: Session, user: User, hackathon: Hackathon) -> bool:
    if user.role == Role.super_admin.value:
        return True
    if user.role != Role.coordinator.value:
        return False
    return (
        db.query(HackathonAdmin)
        .filter(HackathonAdmin.hackathon_id == hackathon.id, HackathonAdmin.user_id == user.id)
        .first()
        is not None
    )


def require_editor(db: Session, user: User, hackathon: Hackathon) -> None:
    require_staff(user)
    if not can_edit(db, user, hackathon):
        raise AppError(403, "forbidden", "You are not assigned to this hackathon")
