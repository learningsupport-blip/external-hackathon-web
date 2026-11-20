"""Email codes and student account creation."""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.orm import Session

from app.accounts import BATCHES, COUNTRIES, UNIVERSITIES
from app.config import Settings
from app.errors import AppError
from app.models import EmailVerification, Role, Session as DbSession, User
from app.security import hash_password, hash_token, verify_password
from app.services.mail import deliver

CODE_MINUTES = 10
TOKEN_MINUTES = 30
MAX_ATTEMPTS = 5


def signup_options() -> dict:
    return {
        "countries": [{"code": code, "dial": dial, "label": f"{dial} {code}"} for code, dial in COUNTRIES],
        "universities": list(UNIVERSITIES),
        "batches": list(BATCHES),
    }


def purge_expired(db: Session) -> None:
    now = datetime.now(UTC)
    db.execute(delete(DbSession).where(DbSession.expires_at <= now))
    db.execute(
        delete(EmailVerification).where(
            or_(
                and_(EmailVerification.token_expires_at.is_(None), EmailVerification.expires_at <= now),
                and_(EmailVerification.token_expires_at.is_not(None), EmailVerification.token_expires_at <= now),
            )
        )
    )


def request_code(db: Session, settings: Settings, email: str) -> str | None:
    purge_expired(db)
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise AppError(409, "account_exists", "An account with this email already exists. Sign in instead.")
    code = f"{secrets.randbelow(1_000_000):06d}"
    row = db.get(EmailVerification, email)
    if row is None:
        row = EmailVerification(email=email, code_hash=hash_token(f"{email}:{code}"), expires_at=datetime.now(UTC))
        db.add(row)
    row.code_hash = hash_token(f"{email}:{code}")
    row.expires_at = datetime.now(UTC) + timedelta(minutes=CODE_MINUTES)
    row.attempts = 0
    row.verified_token_hash = None
    row.token_expires_at = None
    db.flush()
    sent = _send(settings, email, code)
    if settings.app_env == "development" and not sent:
        return code
    return None


def confirm_code(db: Session, email: str, code: str) -> str:
    row = db.get(EmailVerification, email)
    if row is None or row.expires_at <= datetime.now(UTC):
        raise AppError(400, "code_expired", "That code has expired. Request a new one.")
    if row.attempts >= MAX_ATTEMPTS:
        raise AppError(429, "too_many_attempts", "Too many incorrect codes. Request a new one.")
    if row.code_hash != hash_token(f"{email}:{code}"):
        row.attempts += 1
        raise AppError(401, "invalid_code", "That code does not match. Check the email and try again.")
    token = secrets.token_urlsafe(32)
    row.verified_token_hash = hash_token(token)
    row.token_expires_at = datetime.now(UTC) + timedelta(minutes=TOKEN_MINUTES)
    db.flush()
    return token


def register_user(db: Session, payload) -> User:
    _check_choice(payload.phone_country, {code for code, _dial in COUNTRIES}, "Choose a country code")
    if payload.phone_country == "IN" and len(payload.phone) != 10:
        raise AppError(422, "invalid_phone", "Enter a 10-digit mobile number")
    _check_choice(payload.university, set(UNIVERSITIES), "Select a university from the list")
    _check_choice(payload.batch, set(BATCHES), "Select a batch")
    row = db.get(EmailVerification, payload.email)
    if (
        row is None
        or row.verified_token_hash != hash_token(payload.verification_token)
        or row.token_expires_at is None
        or row.token_expires_at <= datetime.now(UTC)
    ):
        raise AppError(403, "email_unverified", "Verify your email before creating an account")
    if db.scalar(select(User.id).where(User.email == payload.email)):
        raise AppError(409, "account_exists", "An account with this email already exists. Sign in instead.")
    if db.scalar(select(User.id).where(User.niat_id == payload.niat_id)):
        raise AppError(409, "niat_id_taken", "This NIAT ID is already registered")
    taken_phone = db.scalar(
        select(User.id).where(User.phone_country == payload.phone_country, User.phone == payload.phone)
    )
    if taken_phone:
        raise AppError(409, "phone_taken", "This mobile number is already registered")
    user = User(
        email=payload.email,
        name=f"{payload.first_name} {payload.last_name}",
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone_country=payload.phone_country,
        phone=payload.phone,
        university=payload.university,
        batch=payload.batch,
        niat_id=payload.niat_id,
        password_hash=hash_password(payload.password),
        email_verified_at=datetime.now(UTC),
        role=Role.student.value,
    )
    db.add(user)
    db.delete(row)
    db.flush()
    return user


def login_user(db: Session, email: str, password: str) -> User:
    purge_expired(db)
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash):
        raise AppError(401, "invalid_login", "Email or password is incorrect")
    return user


def _check_choice(value: str, allowed: set[str], message: str) -> None:
    if value not in allowed:
        raise AppError(422, "invalid_choice", message)


def _send(settings: Settings, email: str, code: str) -> bool:
    if not settings.brevo_api_key and not settings.resend_api_key:
        if settings.app_env == "development":
            return False
        raise AppError(503, "email_unconfigured", "Email delivery is not configured")
    sent, _detail = deliver(
        settings,
        email,
        "Your HackHub verification code",
        f"Your HackHub verification code is {code}. It expires in {CODE_MINUTES} minutes.",
    )
    if sent:
        return True
    if settings.app_env == "development":
        return False
    raise AppError(502, "email_failed", "The verification email could not be sent")
