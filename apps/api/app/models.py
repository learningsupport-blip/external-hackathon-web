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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1000))
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=Role.student.value)
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    sessions: Mapped[list["Session"]] = relationship(back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="sessions")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)

    hackathons: Mapped[list["Hackathon"]] = relationship(
        secondary="hackathon_categories", back_populates="categories"
    )


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("slug", "kind", name="uq_tags_slug_kind"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)

    hackathons: Mapped[list["Hackathon"]] = relationship(secondary="hackathon_tags", back_populates="tags")


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

    categories: Mapped[list[Category]] = relationship(
        secondary="hackathon_categories", back_populates="hackathons"
    )
    tags: Mapped[list[Tag]] = relationship(secondary="hackathon_tags", back_populates="hackathons")
    milestones: Mapped[list["Milestone"]] = relationship(
        back_populates="hackathon", cascade="all, delete-orphan", order_by="Milestone.position"
    )
    resources: Mapped[list["Resource"]] = relationship(
        back_populates="hackathon", cascade="all, delete-orphan", order_by="Resource.position"
    )
    internal: Mapped["HackathonInternal | None"] = relationship(
        back_populates="hackathon", cascade="all, delete-orphan", uselist=False
    )
    admins: Mapped[list["HackathonAdmin"]] = relationship(
        back_populates="hackathon", cascade="all, delete-orphan"
    )
    tracks: Mapped[list["Track"]] = relationship(
        back_populates="hackathon", cascade="all, delete-orphan", order_by="Track.position"
    )
    deliverables: Mapped[list["Deliverable"]] = relationship(
        back_populates="hackathon", cascade="all, delete-orphan", order_by="Deliverable.position"
    )
    prizes: Mapped[list["Prize"]] = relationship(
        back_populates="hackathon", cascade="all, delete-orphan", order_by="Prize.position"
    )
    judging_criteria: Mapped[list["JudgingCriterion"]] = relationship(
        back_populates="hackathon", cascade="all, delete-orphan", order_by="JudgingCriterion.position"
    )
    faqs: Mapped[list["Faq"]] = relationship(
        back_populates="hackathon", cascade="all, delete-orphan", order_by="Faq.position"
    )
    announcements: Mapped[list["Announcement"]] = relationship(
        back_populates="hackathon", cascade="all, delete-orphan", order_by="Announcement.position"
    )
    section_states: Mapped[list["SectionState"]] = relationship(
        back_populates="hackathon", cascade="all, delete-orphan"
    )
    queries: Mapped[list["StudentQuery"]] = relationship(
        back_populates="hackathon", cascade="all, delete-orphan", order_by="StudentQuery.created_at"
    )
    followers: Mapped[list["HackathonFollower"]] = relationship(
        back_populates="hackathon", cascade="all, delete-orphan"
    )


class HackathonInternal(Base):
    __tablename__ = "hackathon_internal"

    hackathon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True
    )
    internal_notes: Mapped[str | None] = mapped_column(Text)
    tracking_status: Mapped[str | None] = mapped_column(String(80))
    administrative_comments: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unverified")
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_urls: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    hackathon: Mapped[Hackathon] = relationship(back_populates="internal")


class HackathonCategory(Base):
    __tablename__ = "hackathon_categories"

    hackathon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )


class HackathonTag(Base):
    __tablename__ = "hackathon_tags"

    hackathon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)


class HackathonAdmin(Base):
    __tablename__ = "hackathon_admins"
    __table_args__ = (UniqueConstraint("hackathon_id", "user_id", name="uq_hackathon_admins_pair"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    hackathon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    hackathon: Mapped[Hackathon] = relationship(back_populates="admins")
    user: Mapped[User] = relationship()


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


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    hackathon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False, default="other")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    hackathon: Mapped[Hackathon] = relationship(back_populates="resources")


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


class _Child:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    hackathon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Track(_Child, Base):
    __tablename__ = "tracks"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    requirements: Mapped[str | None] = mapped_column(Text)

    hackathon: Mapped[Hackathon] = relationship(back_populates="tracks")


class Deliverable(_Child, Base):
    __tablename__ = "deliverables"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    hackathon: Mapped[Hackathon] = relationship(back_populates="deliverables")


class Prize(_Child, Base):
    __tablename__ = "prizes"

    label: Mapped[str] = mapped_column(String(200), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)

    hackathon: Mapped[Hackathon] = relationship(back_populates="prizes")


class JudgingCriterion(_Child, Base):
    __tablename__ = "judging_criteria"
    __table_args__ = (CheckConstraint("weight IS NULL OR (weight >= 0 AND weight <= 100)", name="ck_judging_weight"),)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    weight: Mapped[int | None] = mapped_column(Integer)

    hackathon: Mapped[Hackathon] = relationship(back_populates="judging_criteria")


class Faq(_Child, Base):
    __tablename__ = "faqs"

    question: Mapped[str] = mapped_column(String(300), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    hackathon: Mapped[Hackathon] = relationship(back_populates="faqs")


class Announcement(_Child, Base):
    __tablename__ = "announcements"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    hackathon: Mapped[Hackathon] = relationship(back_populates="announcements")


class SectionState(Base):
    __tablename__ = "section_states"
    __table_args__ = (
        CheckConstraint(
            "section in ('eligibility','participation','themes','submission','prizes','judging','preparation','dates')",
            name="ck_section_states_section",
        ),
        CheckConstraint(
            "state in ('confirmed','not_announced','not_specified','awaiting_confirmation','not_applicable')",
            name="ck_section_states_state",
        ),
    )

    hackathon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True
    )
    section: Mapped[str] = mapped_column(String(32), primary_key=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="not_specified")

    hackathon: Mapped[Hackathon] = relationship(back_populates="section_states")


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    hackathon: Mapped[Hackathon] = relationship(back_populates="queries")
    author: Mapped[User | None] = relationship(foreign_keys=[author_id])
    assignee: Mapped[User | None] = relationship(foreign_keys=[assignee_id])
    responses: Mapped[list["QueryResponse"]] = relationship(
        back_populates="query", cascade="all, delete-orphan", order_by="QueryResponse.created_at"
    )


class QueryResponse(Base):
    __tablename__ = "query_responses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    query_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    official: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    query: Mapped[StudentQuery] = relationship(back_populates="responses")


class HackathonFollower(Base):
    __tablename__ = "hackathon_followers"
    __table_args__ = (UniqueConstraint("hackathon_id", "user_id", name="uq_hackathon_followers_pair"),)

    hackathon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    hackathon: Mapped[Hackathon] = relationship(back_populates="followers")
    user: Mapped[User] = relationship()


class HackathonBookmark(Base):
    __tablename__ = "hackathon_bookmarks"
    __table_args__ = (UniqueConstraint("hackathon_id", "user_id", name="uq_hackathon_bookmarks_pair"),)

    hackathon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    hackathon: Mapped[Hackathon] = relationship()
    user: Mapped[User] = relationship()


class HackathonStance(Base):
    __tablename__ = "hackathon_stances"
    __table_args__ = (
        UniqueConstraint("hackathon_id", "user_id", name="uq_hackathon_stances_pair"),
        CheckConstraint("stance in ('registered', 'missed')", name="ck_hackathon_stances_stance"),
    )

    hackathon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    stance: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    hackathon: Mapped[Hackathon] = relationship()
    user: Mapped[User] = relationship()


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    in_app: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


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
