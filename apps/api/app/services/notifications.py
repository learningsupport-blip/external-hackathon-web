from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.config import Settings, get_settings
from app.services.mail import deliver
from app.documents import items
from app.models import (
    PUBLIC_LIFECYCLES,
    ExtraNotification,
    Hackathon,
    HackathonMember,
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
        db.scalars(
            select(HackathonMember.user_id).where(
                HackathonMember.hackathon_id == hackathon_id, HackathonMember.followed_at.is_not(None)
            )
        ).all()
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


def event_deadline(hackathon: Hackathon, now: datetime | None = None) -> datetime | None:
    if hackathon.submission_deadline:
        return hackathon.submission_deadline
    if hackathon.registration_closes_at:
        return hackathon.registration_closes_at
    now = now or datetime.now(UTC)
    moments = []
    for milestone in hackathon.milestones:
        if milestone.visibility != "public":
            continue
        when = milestone.ends_at or milestone.starts_at
        if when:
            moments.append(when)
    if not moments:
        return None
    future = [item for item in moments if item >= now]
    return min(future) if future else max(moments)


def clear_interest_job(db: Session, hackathon_id, user_id) -> None:
    db.execute(
        update(NotificationJob)
        .where(
            NotificationJob.hackathon_id == hackathon_id,
            NotificationJob.user_id == user_id,
            NotificationJob.kind == "interest",
            NotificationJob.status == "pending",
        )
        .values(status="cancelled")
    )


def schedule_interest(db: Session, hackathon: Hackathon, user_id) -> None:
    deadline = event_deadline(hackathon)
    now = datetime.now(UTC)
    active = hackathon.lifecycle in {Lifecycle.published.value, Lifecycle.postponed.value}
    if deadline is None or deadline <= now or not active:
        clear_interest_job(db, hackathon.id, user_id)
        return
    run_at = deadline - timedelta(days=3)
    if run_at <= now:
        run_at = now
    key = f"{user_id}:interest:{hackathon.id}"
    existing = db.scalar(select(NotificationJob).where(NotificationJob.idempotency_key == key))
    if existing is None:
        db.add(
            NotificationJob(
                user_id=user_id,
                hackathon_id=hackathon.id,
                offset_days=3,
                version=1,
                kind="interest",
                idempotency_key=key,
                run_at=run_at,
                status="pending",
            )
        )
        return
    if existing.status == "done":
        return
    existing.status = "pending"
    existing.run_at = run_at
    existing.offset_days = 3
    existing.kind = "interest"


def reschedule_interest(db: Session, hackathon: Hackathon) -> None:
    user_ids = db.scalars(
        select(HackathonMember.user_id).where(
            HackathonMember.hackathon_id == hackathon.id, HackathonMember.interested_at.is_not(None)
        )
    ).all()
    for user_id in user_ids:
        schedule_interest(db, hackathon, user_id)


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


def send_extra(db: Session, actor: User, hackathon: Hackathon, title: str, body: str) -> ExtraNotification:
    notice = ExtraNotification(
        hackathon_id=hackathon.id,
        title=title.strip(),
        body=body.strip(),
        created_by=actor.id,
    )
    db.add(notice)
    db.flush()
    settings = get_settings()
    now = datetime.now(UTC)
    delivered = f"{notice.body}\n\nOpen it on HackHub: {_portal_link(hackathon)}"
    for user in _students(db):
        job = NotificationJob(
            user_id=user.id,
            hackathon_id=hackathon.id,
            notice_id=notice.id,
            version=1,
            kind="extra",
            idempotency_key=f"{user.id}:extra:{notice.id}",
            run_at=now,
            status="pending",
        )
        db.add(job)
        db.flush()
        _deliver(db, settings, job, title=notice.title, body=delivered)
    return notice


def list_extra(db: Session, actor: User) -> list[ExtraNotification]:
    stmt = select(ExtraNotification).join(Hackathon, Hackathon.id == ExtraNotification.hackathon_id)
    if actor.role != Role.super_admin.value:
        stmt = stmt.join(HackathonMember, HackathonMember.hackathon_id == ExtraNotification.hackathon_id).where(
            HackathonMember.user_id == actor.id, HackathonMember.is_admin.is_(True)
        )
    rows = db.scalars(
        stmt.options(selectinload(ExtraNotification.hackathon)).order_by(ExtraNotification.created_at.desc()).limit(50)
    ).unique().all()
    return list(rows)


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


def _announcement(hackathon: Hackathon | None, announcement_id):
    if hackathon is None or announcement_id is None:
        return None
    for item in items(hackathon, "announcements"):
        if item.id == announcement_id:
            return item
    return None


def schedule_announcement(db: Session, hackathon: Hackathon, announcement) -> None:
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
    if not settings.brevo_api_key and not settings.resend_api_key:
        return "skipped", "No email provider configured"
    sent, detail = deliver(settings, user.email, title, body)
    if sent:
        return "sent", None
    return "failed", detail or "The email could not be sent"


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
        announcement = _announcement(hackathon, job.announcement_id)
        title = announcement.title if announcement else "Hackathon update"
        return f"{name}: {title}", announcement.body if announcement else "A followed hackathon was updated."
    if job.kind == "extra":
        notice = db.get(ExtraNotification, job.notice_id) if job.notice_id else None
        if notice is None:
            return f"{name}: update", f"Open it on HackHub: {link}"
        return notice.title, f"{notice.body}\n\nOpen it on HackHub: {link}"
    if job.kind == "interest":
        return (
            f"{name}: deadline coming up",
            f"The deadline for {name} is within three days.\n\nOpen it on HackHub: {link}",
        )
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
