from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.errors import AppError
from app.models import (
    PUBLIC_LIFECYCLES,
    SECTION_KEYS,
    TRANSITIONS,
    Category,
    Hackathon,
    HackathonAdmin,
    HackathonHistory,
    HackathonInternal,
    Lifecycle,
    Milestone,
    Resource,
    Role,
    SectionState,
    StudentQuery,
    Tag,
    User,
)
from app.services import notifications
from app.schemas import (
    HackathonAdmin as HackathonAdminOut,
    HackathonCard,
    HackathonCreate,
    HackathonPublic,
    HackathonUpdate,
    HistoryOut,
    InternalOut,
    InternalUpdate,
    LabelIn,
    MilestoneIn,
    ResourceIn,
    StatsOut,
    ActivityOut,
    AnnouncementOut,
    CategoryOut,
    CoordinatorOut,
    DeliverableOut,
    FaqOut,
    JudgingOut,
    LabelOut,
    MilestoneOut,
    PrizeOut,
    QueryOut,
    QueryResponseOut,
    ResourceOut,
    SectionStateOut,
    TrackOut,
)
from app.security import slugify, write_audit

SCALAR_FIELDS = (
    "name",
    "organiser",
    "organiser_logo_url",
    "short_description",
    "description",
    "problem_statements",
    "official_website",
    "banner_url",
    "difficulty",
    "participation_type",
    "min_team_size",
    "max_team_size",
    "eligibility",
    "academic_year",
    "degree_requirements",
    "geographic_restrictions",
    "other_eligibility",
    "mode",
    "venue",
    "location",
    "event_duration",
    "registration_url",
    "registration_opens_at",
    "registration_closes_at",
    "registration_instructions",
    "submission_url",
    "submission_deadline",
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
    "timezone",
    "featured",
)

LOAD = (
    selectinload(Hackathon.categories),
    selectinload(Hackathon.tags),
    selectinload(Hackathon.milestones),
    selectinload(Hackathon.resources),
    selectinload(Hackathon.internal),
    selectinload(Hackathon.admins).selectinload(HackathonAdmin.user),
    selectinload(Hackathon.tracks),
    selectinload(Hackathon.deliverables),
    selectinload(Hackathon.prizes),
    selectinload(Hackathon.judging_criteria),
    selectinload(Hackathon.faqs),
    selectinload(Hackathon.announcements),
    selectinload(Hackathon.section_states),
    selectinload(Hackathon.queries).selectinload(StudentQuery.responses),
)

STANDARD_MILESTONES = (
    ("Registration opens", "registration_opens"),
    ("Registration closes", "registration_closes"),
    ("Final submission", "final_submission"),
    ("Grand finale", "grand_finale"),
)


def jsonable(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    return value


def registration_state(hackathon: Hackathon, now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    if hackathon.lifecycle == Lifecycle.completed.value:
        return "completed"
    if hackathon.lifecycle in {Lifecycle.cancelled.value, Lifecycle.archived.value, Lifecycle.draft.value}:
        return hackathon.lifecycle
    if hackathon.registration_opens_at and now < hackathon.registration_opens_at:
        return "upcoming"
    if hackathon.registration_closes_at and now > hackathon.registration_closes_at:
        return "closed"
    if hackathon.registration_opens_at or hackathon.registration_closes_at:
        return "open"
    return "open" if hackathon.lifecycle == Lifecycle.published.value else hackathon.lifecycle


def next_deadline(hackathon: Hackathon, now: datetime | None = None) -> tuple[datetime | None, str | None]:
    now = now or datetime.now(UTC)
    candidates: list[tuple[datetime, str]] = []
    for milestone in hackathon.milestones:
        if milestone.visibility != "public":
            continue
        when = milestone.ends_at or milestone.starts_at
        if when and when >= now:
            candidates.append((when, milestone.title))
    if not candidates:
        return None, None
    when, title = min(candidates, key=lambda item: item[0])
    return when, title


def _category_out(category: Category) -> CategoryOut:
    return CategoryOut(id=category.id, name=category.name, slug=category.slug)


def _label_out(tag: Tag) -> LabelOut:
    return LabelOut(id=tag.id, name=tag.name, slug=tag.slug, kind=tag.kind)


def _milestone_out(milestone: Milestone) -> MilestoneOut:
    return MilestoneOut(
        id=milestone.id,
        title=milestone.title,
        description=milestone.description,
        type=milestone.type,
        starts_at=milestone.starts_at,
        ends_at=milestone.ends_at,
        visibility=milestone.visibility,
        reminder_enabled=milestone.reminder_enabled,
        version=milestone.version,
        position=milestone.position,
    )


def _resource_out(resource: Resource) -> ResourceOut:
    return ResourceOut(
        id=resource.id, title=resource.title, url=resource.url, kind=resource.kind, position=resource.position
    )


def to_card(hackathon: Hackathon) -> HackathonCard:
    when, title = next_deadline(hackathon)
    return HackathonCard(
        id=hackathon.id,
        slug=hackathon.slug,
        name=hackathon.name,
        organiser=hackathon.organiser,
        organiser_logo_url=hackathon.organiser_logo_url,
        short_description=hackathon.short_description,
        categories=[_category_out(item) for item in hackathon.categories],
        mode=hackathon.mode,
        participation_type=hackathon.participation_type,
        difficulty=hackathon.difficulty,
        registration_state=registration_state(hackathon),
        registration_closes_at=hackathon.registration_closes_at,
        submission_deadline=hackathon.submission_deadline,
        min_team_size=hackathon.min_team_size,
        max_team_size=hackathon.max_team_size,
        prize_pool=hackathon.prize_pool,
        next_deadline_at=when,
        next_deadline_title=title,
        featured=hackathon.featured,
        lifecycle=hackathon.lifecycle,
        timezone=hackathon.timezone,
        published_at=hackathon.published_at,
        updated_at=hackathon.updated_at,
        labels=[_label_out(item) for item in hackathon.tags],
    )


def _public_query(row: StudentQuery) -> QueryOut | None:
    if not row.is_public or not any(item.official for item in row.responses):
        return None
    return QueryOut(
        id=row.id,
        body=row.body,
        is_public=True,
        status=row.status,
        created_at=row.created_at,
        responses=[
            QueryResponseOut(id=item.id, body=item.body, official=item.official, created_at=item.created_at)
            for item in row.responses
            if item.official
        ],
    )


def _states(hackathon: Hackathon) -> list[SectionStateOut]:
    found = {item.section: item.state for item in hackathon.section_states}
    return [SectionStateOut(section=section, state=found.get(section, "not_specified")) for section in SECTION_KEYS]


def to_public(
    hackathon: Hackathon, following: bool = False, bookmarked: bool = False, stance: str | None = None
) -> HackathonPublic:
    card = to_card(hackathon)
    now = datetime.now(UTC)
    queries = [item for item in (_public_query(row) for row in hackathon.queries) if item is not None]
    return HackathonPublic(
        **card.model_dump(),
        description=hackathon.description,
        problem_statements=hackathon.problem_statements,
        official_website=hackathon.official_website,
        banner_url=hackathon.banner_url,
        eligibility=hackathon.eligibility,
        academic_year=hackathon.academic_year,
        degree_requirements=hackathon.degree_requirements,
        geographic_restrictions=hackathon.geographic_restrictions,
        other_eligibility=hackathon.other_eligibility,
        venue=hackathon.venue,
        location=hackathon.location,
        event_duration=hackathon.event_duration,
        registration_url=hackathon.registration_url,
        registration_opens_at=hackathon.registration_opens_at,
        registration_instructions=hackathon.registration_instructions,
        submission_url=hackathon.submission_url,
        required_deliverables=hackathon.required_deliverables,
        submission_instructions=hackathon.submission_instructions,
        first_prize=hackathon.first_prize,
        second_prize=hackathon.second_prize,
        third_prize=hackathon.third_prize,
        special_awards=hackathon.special_awards,
        certificates=hackathon.certificates,
        internships=hackathon.internships,
        other_rewards=hackathon.other_rewards,
        preparation_guidelines=hackathon.preparation_guidelines,
        milestones=[_milestone_out(item) for item in hackathon.milestones if item.visibility == "public"],
        resources=[_resource_out(item) for item in hackathon.resources],
        tracks=[TrackOut(id=item.id, name=item.name, requirements=item.requirements, position=item.position) for item in hackathon.tracks],
        deliverables=[
            DeliverableOut(id=item.id, title=item.title, detail=item.detail, required=item.required, position=item.position)
            for item in hackathon.deliverables
        ],
        prizes=[PrizeOut(id=item.id, label=item.label, detail=item.detail, position=item.position) for item in hackathon.prizes],
        judging_criteria=[
            JudgingOut(id=item.id, title=item.title, detail=item.detail, weight=item.weight, position=item.position)
            for item in hackathon.judging_criteria
        ],
        faqs=[FaqOut(id=item.id, question=item.question, answer=item.answer, position=item.position) for item in hackathon.faqs],
        announcements=[
            AnnouncementOut(id=item.id, title=item.title, body=item.body, published_at=item.published_at, position=item.position)
            for item in hackathon.announcements
            if item.published_at is not None and item.published_at <= now
        ],
        section_states=_states(hackathon),
        queries=queries,
        following=following,
        bookmarked=bookmarked,
        stance=stance,
    )


def to_admin(hackathon: Hackathon) -> HackathonAdminOut:
    data = to_public(hackathon).model_dump()
    data["milestones"] = [_milestone_out(item).model_dump() for item in hackathon.milestones]
    data["announcements"] = [
        AnnouncementOut(
            id=item.id, title=item.title, body=item.body, published_at=item.published_at, position=item.position
        ).model_dump()
        for item in hackathon.announcements
    ]
    data["queries"] = [
        QueryOut(
            id=item.id,
            body=item.body,
            is_public=item.is_public,
            status=item.status,
            created_at=item.created_at,
            responses=[
                QueryResponseOut(id=answer.id, body=answer.body, official=answer.official, created_at=answer.created_at)
                for answer in item.responses
            ],
        ).model_dump()
        for item in hackathon.queries
    ]
    internal = hackathon.internal or HackathonInternal(hackathon_id=hackathon.id)
    return HackathonAdminOut(
        **data,
        created_by=hackathon.created_by,
        internal=InternalOut(
            internal_notes=internal.internal_notes,
            tracking_status=internal.tracking_status,
            administrative_comments=internal.administrative_comments,
            verification_status=internal.verification_status or "unverified",
            last_verified_at=internal.last_verified_at,
            source_urls=internal.source_urls,
        ),
        coordinators=[
            CoordinatorOut(id=link.user.id, email=link.user.email, name=link.user.name, role=link.user.role)
            for link in hackathon.admins
            if link.user is not None
        ],
    )


def _unique_slug(db: Session, name: str) -> str:
    base = slugify(name)
    slug = base
    number = 2
    while db.scalar(select(Hackathon.id).where(Hackathon.slug == slug)):
        slug = f"{base[:70]}-{number}"
        number += 1
    return slug


def _snapshot(hackathon: Hackathon) -> dict:
    data = {field: jsonable(getattr(hackathon, field)) for field in SCALAR_FIELDS}
    data["lifecycle"] = hackathon.lifecycle
    data["category_ids"] = sorted(str(item.id) for item in hackathon.categories)
    data["labels"] = sorted(f"{item.kind}:{item.name}" for item in hackathon.tags)
    return data


def _milestone_snapshot(milestone: Milestone) -> dict:
    return jsonable(
        {
            "title": milestone.title,
            "description": milestone.description,
            "type": milestone.type,
            "starts_at": milestone.starts_at,
            "ends_at": milestone.ends_at,
            "visibility": milestone.visibility,
            "reminder_enabled": milestone.reminder_enabled,
            "version": milestone.version,
            "position": milestone.position,
        }
    )


def _diff(before: dict, after: dict) -> tuple[dict, dict]:
    previous: dict = {}
    current: dict = {}
    for key, value in after.items():
        if before.get(key) != value:
            previous[key] = before.get(key)
            current[key] = value
    return previous, current


def record_history(
    db: Session,
    *,
    hackathon_id: UUID,
    actor: User,
    entity_type: str,
    entity_id: UUID | None,
    action: str,
    previous: dict | None,
    new: dict | None,
) -> None:
    if previous == new:
        return
    db.add(
        HackathonHistory(
            hackathon_id=hackathon_id,
            actor_id=actor.id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            previous=previous,
            new=new,
        )
    )


def get_hackathon(db: Session, hackathon_id: UUID) -> Hackathon:
    hackathon = db.scalar(select(Hackathon).where(Hackathon.id == hackathon_id).options(*LOAD))
    if hackathon is None:
        raise AppError(404, "not_found", "Hackathon not found")
    return hackathon


def get_public_by_slug(db: Session, slug: str) -> Hackathon:
    hackathon = db.scalar(
        select(Hackathon)
        .where(Hackathon.slug == slug, Hackathon.lifecycle.in_(PUBLIC_LIFECYCLES))
        .options(*LOAD)
    )
    if hackathon is None:
        raise AppError(404, "not_found", "Hackathon not found")
    return hackathon


def create_hackathon(db: Session, settings: Settings, actor: User, payload: HackathonCreate) -> Hackathon:
    hackathon = Hackathon(
        name=payload.name,
        organiser=payload.organiser,
        short_description=payload.short_description,
        slug=_unique_slug(db, payload.name),
        timezone=payload.timezone or settings.default_timezone,
        created_by=actor.id,
        lifecycle=Lifecycle.draft.value,
    )
    db.add(hackathon)
    db.flush()
    db.add(HackathonInternal(hackathon_id=hackathon.id))
    for section in SECTION_KEYS:
        db.add(SectionState(hackathon_id=hackathon.id, section=section, state="not_specified"))
    if actor.role == Role.coordinator.value:
        db.add(HackathonAdmin(hackathon_id=hackathon.id, user_id=actor.id))
    record_history(
        db,
        hackathon_id=hackathon.id,
        actor=actor,
        entity_type="hackathon",
        entity_id=hackathon.id,
        action="created",
        previous=None,
        new={"name": hackathon.name, "lifecycle": hackathon.lifecycle},
    )
    db.flush()
    return get_hackathon(db, hackathon.id)


def _apply_categories(db: Session, hackathon: Hackathon, category_ids: list[UUID]) -> None:
    categories = list(db.scalars(select(Category).where(Category.id.in_(category_ids)))) if category_ids else []
    if len(categories) != len(set(category_ids)):
        raise AppError(422, "invalid_category", "One or more categories do not exist")
    hackathon.categories = categories


def _apply_labels(db: Session, hackathon: Hackathon, labels: list[LabelIn]) -> None:
    chosen: list[Tag] = []
    seen: set[tuple[str, str]] = set()
    for label in labels:
        name = label.name.strip()
        key = (label.kind, name.lower())
        if key in seen:
            continue
        seen.add(key)
        slug = slugify(name)
        tag = db.scalar(select(Tag).where(Tag.slug == slug, Tag.kind == label.kind))
        if tag is None:
            tag = Tag(name=name, slug=slug, kind=label.kind)
            db.add(tag)
            db.flush()
        chosen.append(tag)
    hackathon.tags = chosen


def update_hackathon(db: Session, actor: User, hackathon: Hackathon, payload: HackathonUpdate) -> Hackathon:
    before = _snapshot(hackathon)
    data = payload.model_dump(exclude_unset=True)
    category_ids = data.pop("category_ids", None)
    labels = data.pop("labels", None)
    for field, value in data.items():
        setattr(hackathon, field, value)
    if hackathon.min_team_size and hackathon.max_team_size and hackathon.min_team_size > hackathon.max_team_size:
        raise AppError(422, "invalid_team_size", "Minimum team size cannot exceed the maximum")
    if (
        hackathon.registration_opens_at
        and hackathon.registration_closes_at
        and hackathon.registration_closes_at < hackathon.registration_opens_at
    ):
        raise AppError(422, "invalid_registration_window", "Registration cannot close before it opens")
    if category_ids is not None:
        _apply_categories(db, hackathon, category_ids)
    if labels is not None:
        _apply_labels(db, hackathon, [LabelIn.model_validate(item) for item in labels])
    hackathon.updated_at = datetime.now(UTC)
    after = _snapshot(hackathon)
    previous, current = _diff(before, after)
    record_history(
        db,
        hackathon_id=hackathon.id,
        actor=actor,
        entity_type="hackathon",
        entity_id=hackathon.id,
        action="updated",
        previous=previous or None,
        new=current or None,
    )
    db.flush()
    return get_hackathon(db, hackathon.id)


def update_internal(db: Session, actor: User, hackathon: Hackathon, payload: InternalUpdate) -> Hackathon:
    internal = hackathon.internal or HackathonInternal(hackathon_id=hackathon.id)
    if hackathon.internal is None:
        db.add(internal)
        hackathon.internal = internal
    before = {
        "internal_notes": internal.internal_notes,
        "tracking_status": internal.tracking_status,
        "administrative_comments": internal.administrative_comments,
        "verification_status": internal.verification_status,
        "last_verified_at": jsonable(internal.last_verified_at),
        "source_urls": internal.source_urls,
    }
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(internal, field, value)
    after = {
        "internal_notes": internal.internal_notes,
        "tracking_status": internal.tracking_status,
        "administrative_comments": internal.administrative_comments,
        "verification_status": internal.verification_status,
        "last_verified_at": jsonable(internal.last_verified_at),
        "source_urls": internal.source_urls,
    }
    previous, current = _diff(before, after)
    record_history(
        db,
        hackathon_id=hackathon.id,
        actor=actor,
        entity_type="internal",
        entity_id=hackathon.id,
        action="updated",
        previous=previous or None,
        new=current or None,
    )
    db.flush()
    return get_hackathon(db, hackathon.id)


def change_lifecycle(db: Session, actor: User, hackathon: Hackathon, target: str, ip: str | None) -> Hackathon:
    allowed = TRANSITIONS.get(hackathon.lifecycle, set())
    if target not in allowed:
        raise AppError(409, "invalid_transition", f"Cannot move a {hackathon.lifecycle} hackathon to {target}")
    previous = hackathon.lifecycle
    hackathon.lifecycle = target
    if target == Lifecycle.published.value and hackathon.published_at is None:
        hackathon.published_at = datetime.now(UTC)
    hackathon.updated_at = datetime.now(UTC)
    record_history(
        db,
        hackathon_id=hackathon.id,
        actor=actor,
        entity_type="hackathon",
        entity_id=hackathon.id,
        action="lifecycle",
        previous={"lifecycle": previous},
        new={"lifecycle": target},
    )
    write_audit(
        db,
        action=f"hackathon.{target}",
        actor_id=actor.id,
        entity_type="hackathon",
        entity_id=str(hackathon.id),
        metadata={"from": previous, "to": target, "slug": hackathon.slug},
        ip=ip,
    )
    db.flush()
    refreshed = get_hackathon(db, hackathon.id)
    notifications.on_lifecycle(db, refreshed, previous=previous)
    return refreshed


def delete_draft(db: Session, actor: User, hackathon: Hackathon) -> None:
    if hackathon.lifecycle != Lifecycle.draft.value:
        raise AppError(409, "not_draft", "Only drafts can be deleted")
    write_audit(
        db,
        action="hackathon.deleted",
        actor_id=actor.id,
        entity_type="hackathon",
        entity_id=str(hackathon.id),
        metadata={"name": hackathon.name},
    )
    db.delete(hackathon)


def add_milestone(db: Session, actor: User, hackathon: Hackathon, payload: MilestoneIn) -> Milestone:
    try:
        payload.check_range()
    except ValueError as exc:
        raise AppError(422, "invalid_milestone", str(exc)) from exc
    position = payload.position
    if position is None:
        position = (max((item.position for item in hackathon.milestones), default=-1)) + 1
    milestone = Milestone(
        hackathon_id=hackathon.id,
        title=payload.title.strip(),
        description=payload.description,
        type=payload.type,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        visibility=payload.visibility,
        reminder_enabled=payload.reminder_enabled,
        position=position,
    )
    db.add(milestone)
    hackathon.updated_at = datetime.now(UTC)
    db.flush()
    record_history(
        db,
        hackathon_id=hackathon.id,
        actor=actor,
        entity_type="milestone",
        entity_id=milestone.id,
        action="created",
        previous=None,
        new=_milestone_snapshot(milestone),
    )
    notifications.schedule_milestone(db, hackathon, milestone)
    notifications.announce_meeting(db, hackathon, milestone)
    return milestone


def add_standard_milestones(db: Session, actor: User, hackathon: Hackathon) -> Hackathon:
    start = max((item.position for item in hackathon.milestones), default=-1) + 1
    for offset, (title, kind) in enumerate(STANDARD_MILESTONES):
        add_milestone(
            db,
            actor,
            hackathon,
            MilestoneIn(title=title, type=kind, visibility="public", position=start + offset),
        )
    return get_hackathon(db, hackathon.id)


def _get_milestone(hackathon: Hackathon, milestone_id: UUID) -> Milestone:
    for milestone in hackathon.milestones:
        if milestone.id == milestone_id:
            return milestone
    raise AppError(404, "not_found", "Milestone not found")


def update_milestone(db: Session, actor: User, hackathon: Hackathon, milestone_id: UUID, payload: MilestoneIn) -> Milestone:
    try:
        payload.check_range()
    except ValueError as exc:
        raise AppError(422, "invalid_milestone", str(exc)) from exc
    milestone = _get_milestone(hackathon, milestone_id)
    before = _milestone_snapshot(milestone)
    milestone.title = payload.title.strip()
    milestone.description = payload.description
    milestone.type = payload.type
    milestone.starts_at = payload.starts_at
    milestone.ends_at = payload.ends_at
    milestone.visibility = payload.visibility
    milestone.reminder_enabled = payload.reminder_enabled
    if payload.position is not None:
        milestone.position = payload.position
    dates_changed = before.get("starts_at") != jsonable(milestone.starts_at) or before.get("ends_at") != jsonable(
        milestone.ends_at
    )
    if dates_changed or before.get("title") != milestone.title or before.get("visibility") != milestone.visibility:
        milestone.version += 1
    milestone.updated_at = datetime.now(UTC)
    hackathon.updated_at = datetime.now(UTC)
    record_history(
        db,
        hackathon_id=hackathon.id,
        actor=actor,
        entity_type="milestone",
        entity_id=milestone.id,
        action="updated",
        previous=before,
        new=_milestone_snapshot(milestone),
    )
    db.flush()
    notifications.schedule_milestone(db, hackathon, milestone)
    notifications.announce_meeting(db, hackathon, milestone)
    return milestone


def delete_milestone(db: Session, actor: User, hackathon: Hackathon, milestone_id: UUID) -> None:
    milestone = _get_milestone(hackathon, milestone_id)
    record_history(
        db,
        hackathon_id=hackathon.id,
        actor=actor,
        entity_type="milestone",
        entity_id=milestone.id,
        action="deleted",
        previous=_milestone_snapshot(milestone),
        new=None,
    )
    notifications.cancel_milestone_jobs(db, milestone.id)
    db.delete(milestone)
    hackathon.updated_at = datetime.now(UTC)


def add_resource(db: Session, actor: User, hackathon: Hackathon, payload: ResourceIn) -> Resource:
    position = payload.position
    if position is None:
        position = (max((item.position for item in hackathon.resources), default=-1)) + 1
    resource = Resource(
        hackathon_id=hackathon.id,
        title=payload.title.strip(),
        url=payload.url,
        kind=payload.kind,
        position=position,
    )
    db.add(resource)
    hackathon.updated_at = datetime.now(UTC)
    db.flush()
    record_history(
        db,
        hackathon_id=hackathon.id,
        actor=actor,
        entity_type="resource",
        entity_id=resource.id,
        action="created",
        previous=None,
        new={"title": resource.title, "url": resource.url, "kind": resource.kind},
    )
    return resource


def delete_resource(db: Session, actor: User, hackathon: Hackathon, resource_id: UUID) -> None:
    resource = next((item for item in hackathon.resources if item.id == resource_id), None)
    if resource is None:
        raise AppError(404, "not_found", "Resource not found")
    record_history(
        db,
        hackathon_id=hackathon.id,
        actor=actor,
        entity_type="resource",
        entity_id=resource.id,
        action="deleted",
        previous={"title": resource.title, "url": resource.url},
        new=None,
    )
    db.delete(resource)


def assign_coordinator(db: Session, actor: User, hackathon: Hackathon, email: str) -> Hackathon:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        raise AppError(404, "user_not_found", "No user with that email has signed in yet")
    if user.role == Role.student.value:
        user.role = Role.coordinator.value
    exists = any(link.user_id == user.id for link in hackathon.admins)
    if not exists:
        db.add(HackathonAdmin(hackathon_id=hackathon.id, user_id=user.id))
        record_history(
            db,
            hackathon_id=hackathon.id,
            actor=actor,
            entity_type="coordinator",
            entity_id=user.id,
            action="assigned",
            previous=None,
            new={"email": user.email},
        )
    db.flush()
    return get_hackathon(db, hackathon.id)


def remove_coordinator(db: Session, actor: User, hackathon: Hackathon, user_id: UUID) -> Hackathon:
    link = next((item for item in hackathon.admins if item.user_id == user_id), None)
    if link is None:
        raise AppError(404, "not_found", "Coordinator is not assigned")
    record_history(
        db,
        hackathon_id=hackathon.id,
        actor=actor,
        entity_type="coordinator",
        entity_id=user_id,
        action="unassigned",
        previous={"email": link.user.email if link.user else None},
        new=None,
    )
    db.delete(link)
    db.flush()
    return get_hackathon(db, hackathon.id)


def history(db: Session, hackathon_id: UUID) -> list[HistoryOut]:
    rows = db.scalars(
        select(HackathonHistory)
        .where(HackathonHistory.hackathon_id == hackathon_id)
        .order_by(HackathonHistory.created_at.desc())
    ).all()
    return [
        HistoryOut(
            id=row.id,
            actor_id=row.actor_id,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            action=row.action,
            previous=row.previous,
            new=row.new,
            created_at=row.created_at,
        )
        for row in rows
    ]


def _filters(q: str | None, category: str | None, mode: str | None, participation: str | None, difficulty: str | None, registration: str | None, lifecycle: str | None, featured: bool | None):
    clauses = []
    now = datetime.now(UTC)
    if q:
        like = f"%{q.strip()}%"
        clauses.append(
            or_(
                Hackathon.name.ilike(like),
                Hackathon.organiser.ilike(like),
                Hackathon.short_description.ilike(like),
                Hackathon.description.ilike(like),
                Hackathon.tags.any(Tag.name.ilike(like)),
                Hackathon.categories.any(Category.name.ilike(like)),
            )
        )
    if category:
        clauses.append(Hackathon.categories.any(Category.slug == category))
    if mode:
        clauses.append(Hackathon.mode == mode)
    if participation:
        clauses.append(Hackathon.participation_type == participation)
    if difficulty:
        clauses.append(Hackathon.difficulty == difficulty)
    if featured is not None:
        clauses.append(Hackathon.featured == featured)
    if lifecycle:
        clauses.append(Hackathon.lifecycle == lifecycle)
    if registration == "open":
        clauses.append(Hackathon.lifecycle.in_((Lifecycle.published.value, Lifecycle.postponed.value)))
        clauses.append(or_(Hackathon.registration_opens_at.is_(None), Hackathon.registration_opens_at <= now))
        clauses.append(or_(Hackathon.registration_closes_at.is_(None), Hackathon.registration_closes_at > now))
    elif registration == "upcoming":
        clauses.append(Hackathon.registration_opens_at > now)
        clauses.append(Hackathon.lifecycle.in_((Lifecycle.published.value, Lifecycle.postponed.value)))
    elif registration == "closed":
        clauses.append(Hackathon.registration_closes_at < now)
        clauses.append(Hackathon.lifecycle.in_((Lifecycle.published.value, Lifecycle.postponed.value)))
    elif registration == "completed":
        clauses.append(Hackathon.lifecycle == Lifecycle.completed.value)
    return clauses


def _order(stmt: Select, sort: str) -> Select:
    event_date = (
        select(func.min(Milestone.starts_at))
        .where(Milestone.hackathon_id == Hackathon.id, Milestone.visibility == "public")
        .scalar_subquery()
    )
    if sort == "registration_deadline":
        return stmt.order_by(Hackathon.registration_closes_at.asc().nulls_last(), Hackathon.name.asc())
    if sort == "submission_deadline":
        return stmt.order_by(Hackathon.submission_deadline.asc().nulls_last(), Hackathon.name.asc())
    if sort == "event_date":
        return stmt.order_by(event_date.asc().nulls_last(), Hackathon.name.asc())
    return stmt.order_by(Hackathon.published_at.desc().nulls_last(), Hackathon.created_at.desc())


def list_public(
    db: Session,
    *,
    q: str | None,
    category: str | None,
    mode: str | None,
    participation: str | None,
    difficulty: str | None,
    registration: str | None,
    sort: str,
    featured: bool | None,
    page: int,
    page_size: int,
) -> tuple[list[Hackathon], int]:
    clauses = [Hackathon.lifecycle.in_(PUBLIC_LIFECYCLES), *_filters(q, category, mode, participation, difficulty, registration, None, featured)]
    total = db.scalar(select(func.count(func.distinct(Hackathon.id))).where(*clauses)) or 0
    stmt = _order(select(Hackathon).where(*clauses).options(*LOAD), sort)
    rows = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).unique().all()
    return list(rows), total


def list_admin(
    db: Session, actor: User, *, q: str | None, lifecycle: str | None, sort: str, page: int, page_size: int
) -> tuple[list[Hackathon], int]:
    clauses = _filters(q, None, None, None, None, None, lifecycle, None)
    stmt = select(Hackathon)
    if actor.role != Role.super_admin.value:
        stmt = stmt.join(HackathonAdmin, HackathonAdmin.hackathon_id == Hackathon.id).where(HackathonAdmin.user_id == actor.id)
    if clauses:
        stmt = stmt.where(*clauses)
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = db.scalar(count_stmt) or 0
    if sort == "name":
        ordering = Hackathon.name.asc()
    elif sort == "deadline":
        ordering = Hackathon.submission_deadline.asc().nulls_last()
    else:
        ordering = Hackathon.updated_at.desc()
    rows = db.scalars(stmt.options(*LOAD).order_by(ordering).offset((page - 1) * page_size).limit(page_size)).unique().all()
    return list(rows), total


def scoped_ids(db: Session, actor: User) -> list[UUID] | None:
    if actor.role == Role.super_admin.value:
        return None
    return list(db.scalars(select(HackathonAdmin.hackathon_id).where(HackathonAdmin.user_id == actor.id)).all())


def stats(db: Session, actor: User) -> StatsOut:
    ids = scoped_ids(db, actor)
    base = select(Hackathon)
    if ids is not None:
        base = base.where(Hackathon.id.in_(ids or [UUID(int=0)]))
    rows = db.scalars(base.options(selectinload(Hackathon.milestones))).unique().all()
    now = datetime.now(UTC)
    upcoming = 0
    open_count = 0
    for hackathon in rows:
        if registration_state(hackathon, now) == "open":
            open_count += 1
        if hackathon.lifecycle not in {Lifecycle.published.value, Lifecycle.postponed.value}:
            continue
        for milestone in hackathon.milestones:
            if milestone.visibility != "public":
                continue
            when = milestone.ends_at or milestone.starts_at
            if when and when >= now:
                upcoming += 1
    history_stmt = select(HackathonHistory).order_by(HackathonHistory.created_at.desc()).limit(12)
    if ids is not None:
        history_stmt = history_stmt.where(HackathonHistory.hackathon_id.in_(ids or [UUID(int=0)]))
    activity = []
    for row in db.scalars(history_stmt).all():
        summary = row.action.replace("_", " ")
        if row.new and row.new.get("name"):
            summary = f"{row.action}: {row.new['name']}"
        elif row.new and row.new.get("title"):
            summary = f"{row.action}: {row.new['title']}"
        elif row.new and row.new.get("lifecycle"):
            summary = f"lifecycle {row.previous.get('lifecycle') if row.previous else '?'} → {row.new['lifecycle']}"
        activity.append(
            ActivityOut(
                id=row.id,
                action=row.action,
                entity_type=row.entity_type,
                summary=summary,
                created_at=row.created_at,
            )
        )
    return StatsOut(
        total=len(rows),
        published=sum(1 for item in rows if item.lifecycle == Lifecycle.published.value),
        draft=sum(1 for item in rows if item.lifecycle == Lifecycle.draft.value),
        registration_open=open_count,
        upcoming_deadlines=upcoming,
        completed=sum(1 for item in rows if item.lifecycle == Lifecycle.completed.value),
        recent_activity=activity,
    )


def calendar_events(
    db: Session,
    *,
    start: datetime,
    end: datetime,
    category: str | None,
    event_type: str | None,
    hackathon: str | None,
) -> list[Milestone]:
    stmt = (
        select(Milestone)
        .join(Hackathon, Hackathon.id == Milestone.hackathon_id)
        .where(
            Hackathon.lifecycle.in_(PUBLIC_LIFECYCLES),
            Milestone.visibility == "public",
            or_(
                Milestone.starts_at.between(start, end),
                Milestone.ends_at.between(start, end),
                (Milestone.starts_at <= start) & (Milestone.ends_at >= end),
            ),
        )
        .options(selectinload(Milestone.hackathon).selectinload(Hackathon.categories))
        .order_by(func.coalesce(Milestone.starts_at, Milestone.ends_at).asc())
    )
    if category:
        stmt = stmt.where(Hackathon.categories.any(Category.slug == category))
    if event_type:
        stmt = stmt.where(Milestone.type == event_type)
    if hackathon:
        stmt = stmt.where(Hackathon.slug == hackathon)
    return list(db.scalars(stmt).unique().all())
