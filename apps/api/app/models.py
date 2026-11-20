import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Role(str, enum.Enum):
    student = "student"
    coordinator = "coordinator"
    super_admin = "super_admin"


class Lifecycle(str, enum.Enum):
    draft = "draft"
    published = "published"
    postponed = "postponed"
    cancelled = "cancelled"
    archived = "archived"
    completed = "completed"


PUBLIC_LIFECYCLES = (Lifecycle.published.value, Lifecycle.postponed.value, Lifecycle.completed.value)

TRANSITIONS: dict[str, set[str]] = {
    Lifecycle.draft.value: {Lifecycle.published.value},
    Lifecycle.published.value: {
        Lifecycle.postponed.value,
        Lifecycle.cancelled.value,
        Lifecycle.archived.value,
        Lifecycle.completed.value,
    },
    Lifecycle.postponed.value: {
        Lifecycle.published.value,
        Lifecycle.cancelled.value,
        Lifecycle.archived.value,
    },
    Lifecycle.completed.value: {Lifecycle.archived.value, Lifecycle.published.value},
    Lifecycle.cancelled.value: {Lifecycle.draft.value},
    Lifecycle.archived.value: {Lifecycle.draft.value},
}


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("phone_country", "phone", name="uq_users_phone"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(80))
    last_name: Mapped[str | None] = mapped_column(String(80))
    phone_country: Mapped[str | None] = mapped_column(String(8))
    phone: Mapped[str | None] = mapped_column(String(20))
    university: Mapped[str | None] = mapped_column(String(200))
    batch: Mapped[str | None] = mapped_column(String(40))
    niat_id: Mapped[str | None] = mapped_column(String(16), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(200))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    avatar_url: Mapped[str | None] = mapped_column(String(1000))
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=Role.student.value)
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    sessions: Mapped[list["Session"]] = relationship(back_populates="user")


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    email: Mapped[str] = mapped_column(String(320), primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verified_token_hash: Mapped[str | None] = mapped_column(String(64))
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="sessions")


class Hackathon(Base):
    __tablename__ = "hackathons"
    __table_args__ = (
        CheckConstraint(
            "lifecycle in ('draft','published','postponed','cancelled','archived','completed')",
            name="ck_hackathons_lifecycle",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    organiser: Mapped[str] = mapped_column(String(200), nullable=False)
    organiser_logo_url: Mapped[str | None] = mapped_column(String(1000))
    short_description: Mapped[str | None] = mapped_column(String(400))
    description: Mapped[str | None] = mapped_column(Text)
    problem_statements: Mapped[str | None] = mapped_column(Text)
    official_website: Mapped[str | None] = mapped_column(String(1000))
    banner_url: Mapped[str | None] = mapped_column(String(1000))
    difficulty: Mapped[str | None] = mapped_column(String(32))
    participation_type: Mapped[str | None] = mapped_column(String(32))
    min_team_size: Mapped[int | None] = mapped_column(Integer)
    max_team_size: Mapped[int | None] = mapped_column(Integer)
    eligibility: Mapped[str | None] = mapped_column(Text)
    academic_year: Mapped[str | None] = mapped_column(String(120))
    degree_requirements: Mapped[str | None] = mapped_column(Text)
    geographic_restrictions: Mapped[str | None] = mapped_column(Text)
    other_eligibility: Mapped[str | None] = mapped_column(Text)
    mode: Mapped[str | None] = mapped_column(String(32))
    venue: Mapped[str | None] = mapped_column(String(300))
    location: Mapped[str | None] = mapped_column(String(300))
    event_duration: Mapped[str | None] = mapped_column(String(120))
    registration_url: Mapped[str | None] = mapped_column(String(1000))
    registration_opens_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    registration_closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    registration_instructions: Mapped[str | None] = mapped_column(Text)
    submission_url: Mapped[str | None] = mapped_column(String(1000))
    submission_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    required_deliverables: Mapped[str | None] = mapped_column(Text)
    submission_instructions: Mapped[str | None] = mapped_column(Text)
    prize_pool: Mapped[str | None] = mapped_column(String(200))
    first_prize: Mapped[str | None] = mapped_column(String(200))
    second_prize: Mapped[str | None] = mapped_column(String(200))
    third_prize: Mapped[str | None] = mapped_column(String(200))
    special_awards: Mapped[str | None] = mapped_column(Text)
    certificates: Mapped[str | None] = mapped_column(Text)
    internships: Mapped[str | None] = mapped_column(Text)
    other_rewards: Mapped[str | None] = mapped_column(Text)
    preparation_guidelines: Mapped[str | None] = mapped_column(Text)
    lifecycle: Mapped[str] = mapped_column(String(32), nullable=False, default=Lifecycle.draft.value, index=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Kolkata")
    featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    milestones: Mapped[list["Milestone"]] = relationship(
        back_populates="hackathon", cascade="all, delete-orphan", order_by="Milestone.position"
    )
    members: Mapped[list["HackathonMember"]] = relationship(
        back_populates="hackathon", cascade="all, delete-orphan"
    )
    categories: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=sql_text("'[]'::jsonb"))
    labels: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=sql_text("'[]'::jsonb"))
    internal: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=sql_text("'{}'::jsonb"))
    section_states: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=sql_text("'{}'::jsonb")
    )
    tracks: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=sql_text("'[]'::jsonb"))
    deliverables: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default=sql_text("'[]'::jsonb")
    )
    prizes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=sql_text("'[]'::jsonb"))
    judging_criteria: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default=sql_text("'[]'::jsonb")
    )
    faqs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=sql_text("'[]'::jsonb"))
    resources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=sql_text("'[]'::jsonb"))
    announcements: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default=sql_text("'[]'::jsonb")
    )
    queries: Mapped[list["StudentQuery"]] = relationship(
        back_populates="hackathon", cascade="all, delete-orphan", order_by="StudentQuery.created_at"
    )


class Milestone(Base):
    __tablename__ = "milestones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    hackathon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    visibility: Mapped[str] = mapped_column(String(16), nullable=False, default="public")
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    hackathon: Mapped[Hackathon] = relationship(back_populates="milestones")


class HackathonHistory(Base):
    __tablename__ = "hackathon_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    hackathon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    previous: Mapped[dict | None] = mapped_column(JSONB)
    new: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(80))
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB)
    ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


SECTION_KEYS = (
    "eligibility",
    "participation",
    "themes",
    "submission",
    "prizes",
    "judging",
    "preparation",
    "dates",
)
INFO_STATES = ("confirmed", "not_announced", "not_specified", "awaiting_confirmation", "not_applicable")
VERIFICATION_STATES = ("unverified", "verified", "needs_review")


class StudentQuery(Base):
    __tablename__ = "queries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    hackathon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    responses: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=sql_text("'[]'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    hackathon: Mapped[Hackathon] = relationship(back_populates="queries")
    author: Mapped[User | None] = relationship(foreign_keys=[author_id])
    assignee: Mapped[User | None] = relationship(foreign_keys=[assignee_id])


class HackathonMember(Base):
    __tablename__ = "hackathon_members"
    __table_args__ = (
        CheckConstraint(
            "stance IS NULL OR stance IN ('registered', 'missed')",
            name="ck_hackathon_members_stance",
        ),
        CheckConstraint(
            "is_admin OR followed_at IS NOT NULL OR bookmarked_at IS NOT NULL OR stance IS NOT NULL OR interested_at IS NOT NULL",
            name="ck_hackathon_members_active",
        ),
    )

    hackathon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sql_text("false"))
    followed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    bookmarked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stance: Mapped[str | None] = mapped_column(String(16))
    interested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    hackathon: Mapped[Hackathon] = relationship(back_populates="members")
    user: Mapped[User] = relationship()


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    in_app: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ExtraNotification(Base):
    __tablename__ = "extra_notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    hackathon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    hackathon: Mapped[Hackathon] = relationship()


class NotificationJob(Base):
    __tablename__ = "notification_jobs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_notification_jobs_key"),
        CheckConstraint("status in ('pending','cancelled','done')", name="ck_notification_jobs_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    hackathon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    milestone_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    announcement_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    notice_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("extra_notifications.id", ondelete="SET NULL")
    )
    offset_days: Mapped[int | None] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    hackathon_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("hackathons.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notification_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    detail: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
