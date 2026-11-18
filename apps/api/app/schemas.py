import re
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator

DIFFICULTIES = {"beginner", "intermediate", "advanced"}
PARTICIPATION = {"individual", "team", "both"}
MODES = {"online", "offline", "hybrid"}
MILESTONE_TYPES = {
    "registration_opens",
    "registration_closes",
    "team_formation",
    "idea_submission",
    "prototype_submission",
    "round_one",
    "round_two",
    "final_submission",
    "grand_finale",
    "results",
    "workshop",
    "meeting",
    "other",
}
VISIBILITIES = {"public", "internal"}
RESOURCE_KINDS = {"guidelines", "rulebook", "problem_statement", "template", "video", "reference", "other"}
TAG_KINDS = {"tag", "theme", "technology"}
LIFECYCLES = {"draft", "published", "postponed", "cancelled", "archived", "completed"}
SECTION_KEYS = {"eligibility", "participation", "themes", "submission", "prizes", "judging", "preparation", "dates"}
INFO_STATES = {"confirmed", "not_announced", "not_specified", "awaiting_confirmation", "not_applicable"}
VERIFICATION_STATES = {"unverified", "verified", "needs_review"}


def _email(value: str) -> str:
    cleaned = value.strip().lower()
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", cleaned) is None:
        raise ValueError("Enter an email address")
    return cleaned


def _blank(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _http_url(value: str | None) -> str | None:
    value = _blank(value)
    if value is None:
        return None
    if not value.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")
    return value


def _timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Unknown timezone") from exc
    return value


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        raise ValueError("Timestamp must include a timezone offset")
    return value


class UserOut(BaseModel):
    id: UUID
    email: str
    name: str
    avatar_url: str | None
    role: str


class DevLoginIn(BaseModel):
    email: str
    name: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def email_ok(cls, value: str) -> str:
        return _email(value)


class CreateUserIn(BaseModel):
    email: str
    name: str = Field(min_length=1, max_length=200)
    role: str

    @field_validator("email")
    @classmethod
    def email_ok(cls, value: str) -> str:
        return _email(value)

    @field_validator("role")
    @classmethod
    def role_ok(cls, value: str) -> str:
        if value not in {"student", "coordinator"}:
            raise ValueError("Role must be student or coordinator")
        return value


class LabelIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    kind: str

    @field_validator("kind")
    @classmethod
    def kind_ok(cls, value: str) -> str:
        if value not in TAG_KINDS:
            raise ValueError("Unknown label kind")
        return value


class LabelOut(BaseModel):
    id: UUID
    name: str
    slug: str
    kind: str


class CategoryOut(BaseModel):
    id: UUID
    name: str
    slug: str


class MilestoneIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    type: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    visibility: str = "public"
    reminder_enabled: bool = True
    position: int | None = Field(default=None, ge=0, le=1000)

    @field_validator("type")
    @classmethod
    def type_ok(cls, value: str) -> str:
        if value not in MILESTONE_TYPES:
            raise ValueError("Unknown milestone type")
        return value

    @field_validator("visibility")
    @classmethod
    def visibility_ok(cls, value: str) -> str:
        if value not in VISIBILITIES:
            raise ValueError("Visibility must be public or internal")
        return value

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        return _blank(value)

    @field_validator("starts_at", "ends_at")
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        return _aware(value)

    def check_range(self) -> None:
        if self.starts_at and self.ends_at and self.ends_at < self.starts_at:
            raise ValueError("End must be after start")


class MilestoneOut(BaseModel):
    id: UUID
    title: str
    description: str | None
    type: str
    starts_at: datetime | None
    ends_at: datetime | None
    visibility: str
    reminder_enabled: bool
    version: int
    position: int


class ResourceIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    url: str
    kind: str = "other"
    position: int | None = Field(default=None, ge=0, le=1000)

    @field_validator("url")
    @classmethod
    def url_ok(cls, value: str) -> str:
        cleaned = _http_url(value)
        if cleaned is None:
            raise ValueError("URL is required")
        return cleaned

    @field_validator("kind")
    @classmethod
    def kind_ok(cls, value: str) -> str:
        if value not in RESOURCE_KINDS:
            raise ValueError("Unknown resource kind")
        return value


class ResourceOut(BaseModel):
    id: UUID
    title: str
    url: str
    kind: str
    position: int


class TrackIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    requirements: str | None = None
    position: int | None = Field(default=None, ge=0, le=1000)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("requirements")
    @classmethod
    def strip_requirements(cls, value: str | None) -> str | None:
        return _blank(value)


class TrackOut(BaseModel):
    id: UUID
    name: str
    requirements: str | None
    position: int


class DeliverableIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    detail: str | None = None
    required: bool = True
    position: int | None = Field(default=None, ge=0, le=1000)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return value.strip()

    @field_validator("detail")
    @classmethod
    def strip_detail(cls, value: str | None) -> str | None:
        return _blank(value)


class DeliverableOut(BaseModel):
    id: UUID
    title: str
    detail: str | None
    required: bool
    position: int


class PrizeIn(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    detail: str | None = None
    position: int | None = Field(default=None, ge=0, le=1000)

    @field_validator("label")
    @classmethod
    def strip_label(cls, value: str) -> str:
        return value.strip()

    @field_validator("detail")
    @classmethod
    def strip_detail(cls, value: str | None) -> str | None:
        return _blank(value)


class PrizeOut(BaseModel):
    id: UUID
    label: str
    detail: str | None
    position: int


class JudgingIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    detail: str | None = None
    weight: int | None = Field(default=None, ge=0, le=100)
    position: int | None = Field(default=None, ge=0, le=1000)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return value.strip()

    @field_validator("detail")
    @classmethod
    def strip_detail(cls, value: str | None) -> str | None:
        return _blank(value)


class JudgingOut(BaseModel):
    id: UUID
    title: str
    detail: str | None
    weight: int | None
    position: int


class FaqIn(BaseModel):
    question: str = Field(min_length=1, max_length=300)
    answer: str = Field(min_length=1)
    position: int | None = Field(default=None, ge=0, le=1000)

    @field_validator("question", "answer")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class FaqOut(BaseModel):
    id: UUID
    question: str
    answer: str
    position: int


class AnnouncementIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)
    published_at: datetime | None = None
    position: int | None = Field(default=None, ge=0, le=1000)

    @field_validator("title", "body")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("published_at")
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        return _aware(value)


class AnnouncementOut(BaseModel):
    id: UUID
    title: str
    body: str
    published_at: datetime | None
    position: int


class SectionStateIn(BaseModel):
    section: str
    state: str

    @field_validator("section")
    @classmethod
    def section_ok(cls, value: str) -> str:
        if value not in SECTION_KEYS:
            raise ValueError("Unknown section")
        return value

    @field_validator("state")
    @classmethod
    def state_ok(cls, value: str) -> str:
        if value not in INFO_STATES:
            raise ValueError("Unknown information state")
        return value


class SectionStateOut(BaseModel):
    section: str
    state: str


class SectionStatesIn(BaseModel):
    states: list[SectionStateIn] = Field(min_length=1)


class StanceIn(BaseModel):
    stance: str

    @field_validator("stance")
    @classmethod
    def stance_ok(cls, value: str) -> str:
        if value not in {"registered", "missed"}:
            raise ValueError("Stance must be registered or missed")
        return value


class StanceOut(BaseModel):
    hackathon_slug: str
    stance: str


class QueryIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    is_public: bool = False

    @field_validator("body")
    @classmethod
    def strip_body(cls, value: str) -> str:
        return value.strip()


class QueryResponseIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)

    @field_validator("body")
    @classmethod
    def strip_body(cls, value: str) -> str:
        return value.strip()


class QueryResponseOut(BaseModel):
    id: UUID
    body: str
    official: bool
    created_at: datetime


class QueryOut(BaseModel):
    id: UUID
    body: str
    is_public: bool
    status: str
    created_at: datetime
    responses: list[QueryResponseOut]


class NotificationPreferenceOut(BaseModel):
    in_app: bool
    email: bool


class NotificationPreferenceIn(BaseModel):
    in_app: bool
    email: bool


class NotificationOut(BaseModel):
    id: UUID
    hackathon_id: UUID | None
    title: str
    body: str
    read_at: datetime | None
    created_at: datetime


class QueryPatch(BaseModel):
    status: str | None = None
    assignee_id: UUID | None = None

    @field_validator("status")
    @classmethod
    def status_ok(cls, value: str | None) -> str | None:
        if value is not None and value not in {"open", "answered", "closed"}:
            raise ValueError("Unknown question status")
        return value


class AdminQueryOut(BaseModel):
    id: UUID
    hackathon_id: UUID
    hackathon_name: str
    hackathon_slug: str
    body: str
    is_public: bool
    status: str
    author_name: str | None
    assignee_id: UUID | None
    assignee_name: str | None
    created_at: datetime
    responses: list[QueryResponseOut]


class MyQueryOut(BaseModel):
    id: UUID
    hackathon_name: str
    hackathon_slug: str
    body: str
    is_public: bool
    status: str
    created_at: datetime
    responses: list[QueryResponseOut]


class AdminAnnouncementOut(BaseModel):
    id: UUID
    hackathon_id: UUID
    hackathon_name: str
    title: str
    published_at: datetime | None


class HackathonCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    organiser: str = Field(min_length=2, max_length=200)
    short_description: str | None = Field(default=None, max_length=400)
    timezone: str | None = None

    @field_validator("name", "organiser")
    @classmethod
    def strip_required(cls, value: str) -> str:
        return value.strip()

    @field_validator("short_description")
    @classmethod
    def strip_short(cls, value: str | None) -> str | None:
        return _blank(value)

    @field_validator("timezone")
    @classmethod
    def tz_ok(cls, value: str | None) -> str | None:
        return _timezone(value) if value else value


class HackathonUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    organiser: str | None = Field(default=None, min_length=2, max_length=200)
    organiser_logo_url: str | None = None
    short_description: str | None = Field(default=None, max_length=400)
    description: str | None = None
    problem_statements: str | None = None
    official_website: str | None = None
    banner_url: str | None = None
    difficulty: str | None = None
    participation_type: str | None = None
    min_team_size: int | None = Field(default=None, ge=1, le=100)
    max_team_size: int | None = Field(default=None, ge=1, le=100)
    eligibility: str | None = None
    academic_year: str | None = Field(default=None, max_length=120)
    degree_requirements: str | None = None
    geographic_restrictions: str | None = None
    other_eligibility: str | None = None
    mode: str | None = None
    venue: str | None = Field(default=None, max_length=300)
    location: str | None = Field(default=None, max_length=300)
    event_duration: str | None = Field(default=None, max_length=120)
    registration_url: str | None = None
    registration_opens_at: datetime | None = None
    registration_closes_at: datetime | None = None
    registration_instructions: str | None = None
    submission_url: str | None = None
    submission_deadline: datetime | None = None
    required_deliverables: str | None = None
    submission_instructions: str | None = None
    prize_pool: str | None = Field(default=None, max_length=200)
    first_prize: str | None = Field(default=None, max_length=200)
    second_prize: str | None = Field(default=None, max_length=200)
    third_prize: str | None = Field(default=None, max_length=200)
    special_awards: str | None = None
    certificates: str | None = None
    internships: str | None = None
    other_rewards: str | None = None
    preparation_guidelines: str | None = None
    timezone: str | None = None
    featured: bool | None = None
    category_ids: list[UUID] | None = None
    labels: list[LabelIn] | None = None

    @field_validator(
        "name",
        "organiser",
        "short_description",
        "description",
        "problem_statements",
        "eligibility",
        "academic_year",
        "degree_requirements",
        "geographic_restrictions",
        "other_eligibility",
        "venue",
        "location",
        "event_duration",
        "registration_instructions",
        "required_deliverables",
        "submission_instructions",
        "prize_pool",
        "first_prize",
        "second_prize",
        "third_prize",
        "special_awards",
        "certificates",
        "internships",
        "other_rewards",
        "preparation_guidelines",
    )
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return _blank(value)

    @field_validator("organiser_logo_url", "official_website", "banner_url", "registration_url", "submission_url")
    @classmethod
    def urls(cls, value: str | None) -> str | None:
        return _http_url(value)

    @field_validator("difficulty")
    @classmethod
    def difficulty_ok(cls, value: str | None) -> str | None:
        if value is not None and value not in DIFFICULTIES:
            raise ValueError("Unknown difficulty")
        return value

    @field_validator("participation_type")
    @classmethod
    def participation_ok(cls, value: str | None) -> str | None:
        if value is not None and value not in PARTICIPATION:
            raise ValueError("Unknown participation type")
        return value

    @field_validator("mode")
    @classmethod
    def mode_ok(cls, value: str | None) -> str | None:
        if value is not None and value not in MODES:
            raise ValueError("Unknown mode")
        return value

    @field_validator("timezone")
    @classmethod
    def tz_ok(cls, value: str | None) -> str | None:
        return _timezone(value) if value else value

    @field_validator("registration_opens_at", "registration_closes_at", "submission_deadline")
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        return _aware(value)


class InternalUpdate(BaseModel):
    internal_notes: str | None = None
    tracking_status: str | None = Field(default=None, max_length=80)
    administrative_comments: str | None = None
    verification_status: str | None = None
    last_verified_at: datetime | None = None
    source_urls: str | None = None

    @field_validator("internal_notes", "tracking_status", "administrative_comments", "source_urls")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return _blank(value)

    @field_validator("verification_status")
    @classmethod
    def verification_ok(cls, value: str | None) -> str | None:
        if value is not None and value not in VERIFICATION_STATES:
            raise ValueError("Unknown verification status")
        return value

    @field_validator("last_verified_at")
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        return _aware(value)


class InternalOut(BaseModel):
    internal_notes: str | None
    tracking_status: str | None
    administrative_comments: str | None
    verification_status: str
    last_verified_at: datetime | None
    source_urls: str | None


class CoordinatorIn(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def email_ok(cls, value: str) -> str:
        return _email(value)


class CoordinatorOut(BaseModel):
    id: UUID
    email: str
    name: str
    role: str


class HackathonCard(BaseModel):
    id: UUID
    slug: str
    name: str
    organiser: str
    organiser_logo_url: str | None
    short_description: str | None
    categories: list[CategoryOut]
    mode: str | None
    participation_type: str | None
    difficulty: str | None
    registration_state: str
    registration_closes_at: datetime | None
    submission_deadline: datetime | None
    min_team_size: int | None
    max_team_size: int | None
    prize_pool: str | None
    next_deadline_at: datetime | None
    next_deadline_title: str | None
    featured: bool
    lifecycle: str
    timezone: str
    published_at: datetime | None
    updated_at: datetime
    labels: list[LabelOut] = []


class HackathonPublic(HackathonCard):
    description: str | None
    problem_statements: str | None
    official_website: str | None
    banner_url: str | None
    eligibility: str | None
    academic_year: str | None
    degree_requirements: str | None
    geographic_restrictions: str | None
    other_eligibility: str | None
    venue: str | None
    location: str | None
    event_duration: str | None
    registration_url: str | None
    registration_opens_at: datetime | None
    registration_instructions: str | None
    submission_url: str | None
    required_deliverables: str | None
    submission_instructions: str | None
    first_prize: str | None
    second_prize: str | None
    third_prize: str | None
    special_awards: str | None
    certificates: str | None
    internships: str | None
    other_rewards: str | None
    preparation_guidelines: str | None
    labels: list[LabelOut]
    milestones: list[MilestoneOut]
    resources: list[ResourceOut]
    tracks: list[TrackOut]
    deliverables: list[DeliverableOut]
    prizes: list[PrizeOut]
    judging_criteria: list[JudgingOut]
    faqs: list[FaqOut]
    announcements: list[AnnouncementOut]
    section_states: list[SectionStateOut]
    queries: list[QueryOut]
    following: bool = False
    bookmarked: bool = False
    stance: str | None = None


class HackathonAdmin(HackathonPublic):
    created_by: UUID | None
    internal: InternalOut
    coordinators: list[CoordinatorOut]


class Page(BaseModel):
    items: list[HackathonCard]
    page: int
    page_size: int
    total: int


class AdminPage(BaseModel):
    items: list[HackathonCard]
    page: int
    page_size: int
    total: int


class LifecycleIn(BaseModel):
    lifecycle: str

    @field_validator("lifecycle")
    @classmethod
    def lifecycle_ok(cls, value: str) -> str:
        if value not in LIFECYCLES - {"draft"} and value != "draft":
            raise ValueError("Unknown lifecycle")
        if value not in LIFECYCLES:
            raise ValueError("Unknown lifecycle")
        return value


class HistoryOut(BaseModel):
    id: UUID
    actor_id: UUID | None
    entity_type: str
    entity_id: UUID | None
    action: str
    previous: dict | None
    new: dict | None
    created_at: datetime


class ActivityOut(BaseModel):
    id: UUID
    action: str
    entity_type: str
    summary: str
    created_at: datetime


class StatsOut(BaseModel):
    total: int
    published: int
    draft: int
    registration_open: int
    upcoming_deadlines: int
    completed: int
    recent_activity: list[ActivityOut]


class CalendarEvent(BaseModel):
    id: UUID
    title: str
    hackathon_name: str
    hackathon_slug: str
    type: str
    starts_at: datetime | None
    ends_at: datetime | None
    timezone: str


class CalendarResponse(BaseModel):
    items: list[CalendarEvent]
    time_label: str
