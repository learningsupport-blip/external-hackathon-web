from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import (
    PUBLIC_LIFECYCLES,
    Announcement,
    Hackathon,
    HackathonFollower,
    Lifecycle,
    Milestone,
    Notification,
    NotificationDelivery,
    NotificationJob,
    NotificationPreference,
    Role,
    User,
)

OFFSETS = (7, 3, 1)


def _prefs(db: Session, user_id) -> NotificationPreference:
    row = db.get(NotificationPreference, user_id)
    if row is None:
        return NotificationPreference(user_id=user_id, in_app=True, email=True)
    return row


def _followers(db: Session, hackathon_id) -> list:
    return list(
        db.scalars(select(HackathonFollower.user_id).where(HackathonFollower.hackathon_id == hackathon_id)).all()
    )


def cancel_milestone_jobs(db: Session, milestone_id) -> None:
    db.execute(
        update(NotificationJob)
        .where(NotificationJob.milestone_id == milestone_id, NotificationJob.status == "pending")
        .values(status="cancelled")
    )


def cancel_hackathon_jobs(db: Session, hackathon_id) -> None:
    db.execute(
        update(NotificationJob)
        .where(NotificationJob.hackathon_id == hackathon_id, NotificationJob.status == "pending")
        .values(status="cancelled")
    )


def cancel_user_jobs(db: Session, hackathon_id, user_id) -> None:
    db.execute(
        update(NotificationJob)
        .where(
            NotificationJob.hackathon_id == hackathon_id,
            NotificationJob.user_id == user_id,
            NotificationJob.status == "pending",
        )
        .values(status="cancelled")
    )


def _insert_job(db: Session, **fields) -> None:
    existing = db.scalar(select(NotificationJob).where(NotificationJob.idempotency_key == fields["idempotency_key"]))
    if existing is None:
        db.add(NotificationJob(**fields))
        return
    if existing.status == "cancelled":
        existing.status = "pending"
        existing.run_at = fields["run_at"]


def _schedule_one(db: Session, hackathon: Hackathon, milestone: Milestone, user_id) -> None:
    when = milestone.starts_at or milestone.ends_at
    if when is None or not milestone.reminder_enabled or milestone.visibility != "public":
        return
    if hackathon.lifecycle not in {PUBLIC_LIFECYCLES[0], PUBLIC_LIFECYCLES[1]}:
        return
    now = datetime.now(UTC)
    for offset in OFFSETS:
        run_at = when - timedelta(days=offset)
        if run_at <= now:
            continue
        _insert_job(
            db,
            user_id=user_id,
            hackathon_id=hackathon.id,
            milestone_id=milestone.id,
            offset_days=offset,
            version=milestone.version,
            kind="reminder",
            idempotency_key=f"{user_id}:{milestone.id}:{offset}:{milestone.version}",
            run_at=run_at,
            status="pending",
        )


def schedule_milestone(db: Session, hackathon: Hackathon, milestone: Milestone) -> None:
    cancel_milestone_jobs(db, milestone.id)
    for user_id in _followers(db, hackathon.id):
        _schedule_one(db, hackathon, milestone, user_id)


def schedule_for_user(db: Session, hackathon: Hackathon, user_id) -> None:
    for milestone in hackathon.milestones:
        _schedule_one(db, hackathon, milestone, user_id)


def on_lifecycle(db: Session, hackathon: Hackathon, previous: str | None = None) -> None:
    if hackathon.lifecycle in {PUBLIC_LIFECYCLES[0], PUBLIC_LIFECYCLES[1]}:
        for milestone in hackathon.milestones:
            schedule_milestone(db, hackathon, milestone)
        if previous == Lifecycle.draft.value and hackathon.lifecycle == Lifecycle.published.value:
            announce_published(db, hackathon)
            for milestone in hackathon.milestones:
                announce_meeting(db, hackathon, milestone)
        return
    cancel_hackathon_jobs(db, hackathon.id)


def _students(db: Session) -> list[User]:
    return list(db.scalars(select(User).where(User.role == Role.student.value).order_by(User.created_at)).all())


def _portal_link(hackathon: Hackathon) -> str:
    origin = get_settings().web_origin.rstrip("/")
    return f"{origin}/hackathons/{hackathon.slug}"


def _when_label(hackathon: Hackathon, moment: datetime | None) -> str:
    if moment is None:
        return "a time still to be confirmed"
    try:
        zone = ZoneInfo(hackathon.timezone or "UTC")
    except Exception:
        zone = ZoneInfo("UTC")
    local = moment.astimezone(zone)
    return local.strftime("%d %b %Y, %I:%M %p")


def announce_published(db: Session, hackathon: Hackathon) -> None:
    summary = (hackathon.short_description or "A new hackathon is on the portal.").strip()
    announce_students(
        db,
        hackathon,
        kind="published",
        title=f"New hackathon: {hackathon.name}",
        body=f"{summary}\n\nOpen it on HackHub: {_portal_link(hackathon)}",
        key=f"published:{hackathon.id}",
    )


def announce_meeting(db: Session, hackathon: Hackathon, milestone: Milestone) -> None:
    if milestone.type != "meeting" or milestone.visibility != "public":
        return
    if hackathon.lifecycle not in {Lifecycle.published.value, Lifecycle.postponed.value}:
        return
    when = milestone.starts_at or milestone.ends_at
    if when is None:
        return
    detail = (milestone.description or "").strip()
    body = f"{milestone.title} is scheduled for {_when_label(hackathon, when)} ({hackathon.timezone})."
    if detail:
        body = f"{body}\n{detail}"
    body = f"{body}\n\nOpen it on HackHub: {_portal_link(hackathon)}"
    announce_students(
        db,
        hackathon,
        kind="meeting",
        title=f"{hackathon.name}: meeting scheduled",
        body=body,
        key=f"meeting:{milestone.id}:{milestone.version}",
    )


def announce_students(db: Session, hackathon: Hackathon, *, kind: str, title: str, body: str, key: str) -> None:
    settings = get_settings()
    now = datetime.now(UTC)
    for user in _students(db):
        idempotency_key = f"{user.id}:{key}"
        job = db.scalar(select(NotificationJob).where(NotificationJob.idempotency_key == idempotency_key))
        if job is not None and job.status == "done":
            continue
        if job is None:
            job = NotificationJob(
                user_id=user.id,
                hackathon_id=hackathon.id,
                version=1,
                kind=kind,
                idempotency_key=idempotency_key,
                run_at=now,
                status="pending",
            )
            db.add(job)
            db.flush()
        else:
            job.status = "pending"
            job.run_at = now
            job.kind = kind
        _deliver(db, settings, job, title=title, body=body)


def get_preferences(db: Session, user: User) -> NotificationPreference:
    row = db.get(NotificationPreference, user.id)
    if row is None:
        return NotificationPreference(user_id=user.id, in_app=True, email=True)
    return row


def save_preferences(db: Session, user: User, *, in_app: bool, email: bool) -> NotificationPreference:
    row = db.get(NotificationPreference, user.id)
    if row is None:
        row = NotificationPreference(user_id=user.id, in_app=in_app, email=email)
        db.add(row)
        return row
    row.in_app = in_app
    row.email = email
    return row


def schedule_announcement(db: Session, hackathon: Hackathon, announcement: Announcement) -> None:
    if announcement.published_at is None or hackathon.lifecycle not in PUBLIC_LIFECYCLES:
        return
    for user_id in _followers(db, hackathon.id):
        _insert_job(
            db,
            user_id=user_id,
            hackathon_id=hackathon.id,
            announcement_id=announcement.id,
            version=1,
            kind="announcement",
            idempotency_key=f"{user_id}:announcement:{announcement.id}",
            run_at=announcement.published_at,
            status="pending",
        )


def _email(settings: Settings, user: User, title: str, body: str) -> tuple[str, str | None]:
    if not settings.resend_api_key:
        return "skipped", "No email provider configured"
    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={"from": settings.resend_from, "to": [user.email], "subject": title, "text": body},
            timeout=10,
        )
    except httpx.HTTPError as exc:
        return "failed", str(exc)[:300]
    if response.status_code >= 400:
        return "failed", response.text[:300]
    return "sent", None


def _message(db: Session, job: NotificationJob) -> tuple[str, str]:
    hackathon = db.get(Hackathon, job.hackathon_id)
    name = hackathon.name if hackathon else "A hackathon"
    link = _portal_link(hackathon) if hackathon else get_settings().web_origin
    if job.kind == "published" and hackathon:
        summary = (hackathon.short_description or "A new hackathon is on the portal.").strip()
        return f"New hackathon: {name}", f"{summary}\n\nOpen it on HackHub: {link}"
    if job.kind == "meeting":
        milestone = db.get(Milestone, job.milestone_id) if job.milestone_id else None
        label = milestone.title if milestone else "A meeting"
        when = _when_label(hackathon, (milestone.starts_at or milestone.ends_at) if milestone else None) if hackathon else ""
        return f"{name}: meeting scheduled", f"{label} is scheduled for {when}.\n\nOpen it on HackHub: {link}"
    if job.kind == "announcement":
        announcement = db.get(Announcement, job.announcement_id) if job.announcement_id else None
        title = announcement.title if announcement else "Hackathon update"
        return f"{name}: {title}", announcement.body if announcement else "A followed hackathon was updated."
    milestone = db.get(Milestone, job.milestone_id) if job.milestone_id else None
    label = milestone.title if milestone else "A deadline"
    return f"{name}: {label} in {job.offset_days} days", f"{label} is {job.offset_days} days away."


def _deliver(db: Session, settings: Settings, job: NotificationJob, title: str | None = None, body: str | None = None) -> None:
    prefs = _prefs(db, job.user_id)
    if title is None or body is None:
        title, body = _message(db, job)
    if prefs.in_app:
        db.add(Notification(user_id=job.user_id, hackathon_id=job.hackathon_id, title=title, body=body))
        db.add(NotificationDelivery(job_id=job.id, channel="in_app", status="sent"))
    if prefs.email:
        user = db.get(User, job.user_id)
        status, detail = _email(settings, user, title, body) if user else ("skipped", "User missing")
        db.add(NotificationDelivery(job_id=job.id, channel="email", status=status, detail=detail))
    job.status = "done"


def list_for_user(db: Session, user_id) -> list[Notification]:
    return list(
        db.scalars(
            select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc()).limit(50)
        ).all()
    )


def mark_read(db: Session, user_id, notification_id) -> Notification:
    row = db.scalar(select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id))
    if row is None:
        from app.errors import AppError

        raise AppError(404, "not_found", "Notification not found")
    if row.read_at is None:
        row.read_at = datetime.now(UTC)
    return row


def tick(db: Session, settings: Settings, limit: int = 50) -> int:
    now = datetime.now(UTC)
    jobs = list(
        db.scalars(
            select(NotificationJob)
            .where(NotificationJob.status == "pending", NotificationJob.run_at <= now)
            .order_by(NotificationJob.run_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
    )
    for job in jobs:
        _deliver(db, settings, job)
    return len(jobs)
