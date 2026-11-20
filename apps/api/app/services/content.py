from datetime import UTC, datetime

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.documents import append_item, drop_item, items, touch
from app.errors import AppError
from app.members import ensure_member, get_member, prune_member
from app.models import (
    PUBLIC_LIFECYCLES,
    SECTION_KEYS,
    Hackathon,
    HackathonMember,
    StudentQuery,
    User,
)
from app.schemas import (
    AnnouncementIn,
    AnnouncementOut,
    DeliverableIn,
    DeliverableOut,
    FaqIn,
    FaqOut,
    JudgingIn,
    JudgingOut,
    PrizeIn,
    PrizeOut,
    QueryOut,
    QueryResponseOut,
    SectionStateIn,
    TrackIn,
    TrackOut,
)
from app.services import notifications
from app.services.hackathons import get_hackathon, record_history, scoped_ids, to_card


def _position(rows, requested: int | None) -> int:
    if requested is not None:
        return requested
    return (max((item.position for item in rows), default=-1)) + 1


def _history(db: Session, actor: User, hackathon: Hackathon, kind: str, row, action: str, previous, new) -> None:
    record_history(
        db,
        hackathon_id=hackathon.id,
        actor=actor,
        entity_type=kind,
        entity_id=row.id,
        action=action,
        previous=previous,
        new=new,
    )
    hackathon.updated_at = datetime.now(UTC)


def track_out(row) -> TrackOut:
    return TrackOut(id=row.id, name=row.name, requirements=row.requirements, position=row.position)


def deliverable_out(row) -> DeliverableOut:
    return DeliverableOut(id=row.id, title=row.title, detail=row.detail, required=row.required, position=row.position)


def prize_out(row) -> PrizeOut:
    return PrizeOut(id=row.id, label=row.label, detail=row.detail, position=row.position)


def judging_out(row) -> JudgingOut:
    return JudgingOut(id=row.id, title=row.title, detail=row.detail, weight=row.weight, position=row.position)


def faq_out(row) -> FaqOut:
    return FaqOut(id=row.id, question=row.question, answer=row.answer, position=row.position)


def announcement_out(row) -> AnnouncementOut:
    return AnnouncementOut(
        id=row.id, title=row.title, body=row.body, published_at=row.published_at, position=row.position
    )


def query_out(row: StudentQuery) -> QueryOut:
    return QueryOut(
        id=row.id,
        body=row.body,
        is_public=row.is_public,
        status=row.status,
        created_at=row.created_at,
        responses=[
            QueryResponseOut(id=item.id, body=item.body, official=item.official, created_at=item.created_at)
            for item in items(row, "responses")
        ],
    )


def section_has_content(hackathon: Hackathon, section: str) -> bool:
    if section == "eligibility":
        return any(
            (
                hackathon.eligibility,
                hackathon.academic_year,
                hackathon.degree_requirements,
                hackathon.geographic_restrictions,
                hackathon.other_eligibility,
                hackathon.min_team_size,
                hackathon.max_team_size,
            )
        )
    if section == "participation":
        return any(
            (hackathon.participation_type, hackathon.mode, hackathon.venue, hackathon.location, hackathon.event_duration)
        )
    if section == "themes":
        return bool(hackathon.labels or hackathon.problem_statements)
    if section == "submission":
        return any(
            (
                hackathon.required_deliverables,
                hackathon.submission_instructions,
                hackathon.submission_url,
                hackathon.submission_deadline,
                hackathon.deliverables,
            )
        )
    if section == "prizes":
        return any(
            (
                hackathon.prize_pool,
                hackathon.first_prize,
                hackathon.second_prize,
                hackathon.third_prize,
                hackathon.special_awards,
                hackathon.certificates,
                hackathon.internships,
                hackathon.other_rewards,
                hackathon.prizes,
            )
        )
    if section == "judging":
        return bool(hackathon.judging_criteria)
    if section == "preparation":
        return bool(hackathon.preparation_guidelines)
    if section == "dates":
        dated = any(item.starts_at or item.ends_at for item in hackathon.milestones)
        return dated or any(
            (hackathon.registration_opens_at, hackathon.registration_closes_at, hackathon.submission_deadline)
        )
    return False


def _add(hackathon: Hackathon, field: str, data: dict):
    data["position"] = _position(items(hackathon, field), data.get("position"))
    data["hackathon_id"] = hackathon.id
    return append_item(hackathon, field, data)


def _change(hackathon: Hackathon, field: str, row_id, label: str):
    return _find(items(hackathon, field), row_id, label)


def add_track(db: Session, actor: User, hackathon: Hackathon, payload: TrackIn):
    row = _add(hackathon, "tracks", {"name": payload.name, "requirements": payload.requirements, "position": payload.position})
    _history(db, actor, hackathon, "track", row, "created", None, {"name": row.name})
    return row


def update_track(db: Session, actor: User, hackathon: Hackathon, row_id, payload: TrackIn):
    row = _change(hackathon, "tracks", row_id, "Track")
    row.name = payload.name
    row.requirements = payload.requirements
    if payload.position is not None:
        row.position = payload.position
    touch(hackathon, "tracks")
    _history(db, actor, hackathon, "track", row, "updated", None, {"name": row.name, "position": row.position})
    return row


def delete_track(db: Session, actor: User, hackathon: Hackathon, row_id) -> None:
    row = _change(hackathon, "tracks", row_id, "Track")
    _history(db, actor, hackathon, "track", row, "deleted", {"name": row.name}, None)
    drop_item(hackathon, "tracks", row_id)


def add_deliverable(db: Session, actor: User, hackathon: Hackathon, payload: DeliverableIn):
    row = _add(
        hackathon,
        "deliverables",
        {"title": payload.title, "detail": payload.detail, "required": payload.required, "position": payload.position},
    )
    _history(db, actor, hackathon, "deliverable", row, "created", None, {"title": row.title})
    return row


def update_deliverable(db: Session, actor: User, hackathon: Hackathon, row_id, payload: DeliverableIn):
    row = _change(hackathon, "deliverables", row_id, "Deliverable")
    row.title = payload.title
    row.detail = payload.detail
    row.required = payload.required
    if payload.position is not None:
        row.position = payload.position
    touch(hackathon, "deliverables")
    _history(db, actor, hackathon, "deliverable", row, "updated", None, {"title": row.title})
    return row


def delete_deliverable(db: Session, actor: User, hackathon: Hackathon, row_id) -> None:
    row = _change(hackathon, "deliverables", row_id, "Deliverable")
    _history(db, actor, hackathon, "deliverable", row, "deleted", {"title": row.title}, None)
    drop_item(hackathon, "deliverables", row_id)


def add_prize(db: Session, actor: User, hackathon: Hackathon, payload: PrizeIn):
    row = _add(hackathon, "prizes", {"label": payload.label, "detail": payload.detail, "position": payload.position})
    _history(db, actor, hackathon, "prize", row, "created", None, {"label": row.label})
    return row


def update_prize(db: Session, actor: User, hackathon: Hackathon, row_id, payload: PrizeIn):
    row = _change(hackathon, "prizes", row_id, "Prize")
    row.label = payload.label
    row.detail = payload.detail
    if payload.position is not None:
        row.position = payload.position
    touch(hackathon, "prizes")
    _history(db, actor, hackathon, "prize", row, "updated", None, {"label": row.label})
    return row


def delete_prize(db: Session, actor: User, hackathon: Hackathon, row_id) -> None:
    row = _change(hackathon, "prizes", row_id, "Prize")
    _history(db, actor, hackathon, "prize", row, "deleted", {"label": row.label}, None)
    drop_item(hackathon, "prizes", row_id)


def add_judging(db: Session, actor: User, hackathon: Hackathon, payload: JudgingIn):
    row = _add(
        hackathon,
        "judging_criteria",
        {"title": payload.title, "detail": payload.detail, "weight": payload.weight, "position": payload.position},
    )
    _history(db, actor, hackathon, "judging", row, "created", None, {"title": row.title, "weight": row.weight})
    return row


def update_judging(db: Session, actor: User, hackathon: Hackathon, row_id, payload: JudgingIn):
    row = _change(hackathon, "judging_criteria", row_id, "Judging criterion")
    row.title = payload.title
    row.detail = payload.detail
    row.weight = payload.weight
    if payload.position is not None:
        row.position = payload.position
    touch(hackathon, "judging_criteria")
    _history(db, actor, hackathon, "judging", row, "updated", None, {"title": row.title})
    return row


def delete_judging(db: Session, actor: User, hackathon: Hackathon, row_id) -> None:
    row = _change(hackathon, "judging_criteria", row_id, "Judging criterion")
    _history(db, actor, hackathon, "judging", row, "deleted", {"title": row.title}, None)
    drop_item(hackathon, "judging_criteria", row_id)


def add_faq(db: Session, actor: User, hackathon: Hackathon, payload: FaqIn):
    row = _add(
        hackathon,
        "faqs",
        {"question": payload.question, "answer": payload.answer, "position": payload.position},
    )
    _history(db, actor, hackathon, "faq", row, "created", None, {"question": row.question})
    return row


def update_faq(db: Session, actor: User, hackathon: Hackathon, row_id, payload: FaqIn):
    row = _change(hackathon, "faqs", row_id, "FAQ")
    row.question = payload.question
    row.answer = payload.answer
    if payload.position is not None:
        row.position = payload.position
    touch(hackathon, "faqs")
    _history(db, actor, hackathon, "faq", row, "updated", None, {"question": row.question})
    return row


def delete_faq(db: Session, actor: User, hackathon: Hackathon, row_id) -> None:
    row = _change(hackathon, "faqs", row_id, "FAQ")
    _history(db, actor, hackathon, "faq", row, "deleted", {"question": row.question}, None)
    drop_item(hackathon, "faqs", row_id)


def add_announcement(db: Session, actor: User, hackathon: Hackathon, payload: AnnouncementIn):
    row = _add(
        hackathon,
        "announcements",
        {"title": payload.title, "body": payload.body, "published_at": payload.published_at, "position": payload.position},
    )
    _history(db, actor, hackathon, "announcement", row, "created", None, {"title": row.title})
    if row.published_at is not None:
        notifications.schedule_announcement(db, hackathon, row)
    return row


def update_announcement(db: Session, actor: User, hackathon: Hackathon, row_id, payload: AnnouncementIn):
    row = _change(hackathon, "announcements", row_id, "Announcement")
    was_draft = row.published_at is None
    row.title = payload.title
    row.body = payload.body
    row.published_at = payload.published_at
    if payload.position is not None:
        row.position = payload.position
    touch(hackathon, "announcements")
    _history(db, actor, hackathon, "announcement", row, "updated", None, {"title": row.title})
    if was_draft and row.published_at is not None:
        notifications.schedule_announcement(db, hackathon, row)
    return row


def delete_announcement(db: Session, actor: User, hackathon: Hackathon, row_id) -> None:
    row = _change(hackathon, "announcements", row_id, "Announcement")
    _history(db, actor, hackathon, "announcement", row, "deleted", {"title": row.title}, None)
    drop_item(hackathon, "announcements", row_id)


def set_section_states(db: Session, actor: User, hackathon: Hackathon, states: list[SectionStateIn]) -> Hackathon:
    current = dict(hackathon.section_states or {})
    for incoming in states:
        if incoming.state == "confirmed" and not section_has_content(hackathon, incoming.section):
            raise AppError(422, "empty_section", f"{incoming.section} is marked confirmed but has no information")
        current[incoming.section] = incoming.state
    hackathon.section_states = current
    touch(hackathon, "section_states")
    record_history(
        db,
        hackathon_id=hackathon.id,
        actor=actor,
        entity_type="section_state",
        entity_id=hackathon.id,
        action="updated",
        previous=None,
        new={item.section: item.state for item in states},
    )
    db.flush()
    return get_hackathon(db, hackathon.id)


def ask_query(db: Session, user: User, hackathon: Hackathon, body: str, is_public: bool) -> StudentQuery:
    if hackathon.lifecycle not in PUBLIC_LIFECYCLES:
        raise AppError(404, "not_found", "Hackathon not found")
    row = StudentQuery(
        hackathon_id=hackathon.id,
        author_id=user.id,
        body=body,
        is_public=is_public,
        responses=[],
        created_at=datetime.now(UTC),
    )
    db.add(row)
    db.flush()
    return row


def answer_query(db: Session, actor: User, hackathon: Hackathon, query_id, body: str) -> StudentQuery:
    row = _find(hackathon.queries, query_id, "Question")
    append_item(
        row,
        "responses",
        {"author_id": actor.id, "body": body, "official": True, "created_at": datetime.now(UTC)},
    )
    if row.status != "closed":
        row.status = "answered"
    db.flush()
    record_history(
        db,
        hackathon_id=hackathon.id,
        actor=actor,
        entity_type="query",
        entity_id=row.id,
        action="answered",
        previous=None,
        new={"body": body},
    )
    return row


def follow(db: Session, user: User, hackathon: Hackathon) -> None:
    if hackathon.lifecycle not in PUBLIC_LIFECYCLES:
        raise AppError(404, "not_found", "Hackathon not found")
    row = ensure_member(db, hackathon.id, user.id)
    if row.followed_at is None:
        row.followed_at = datetime.now(UTC)
    db.flush()
    notifications.schedule_for_user(db, hackathon, user.id)


def unfollow(db: Session, user: User, hackathon: Hackathon) -> None:
    row = get_member(db, hackathon.id, user.id)
    if row is not None:
        row.followed_at = None
        prune_member(db, row)
    notifications.cancel_user_jobs(db, hackathon.id, user.id)


def is_following(db: Session, hackathon_id, user_id) -> bool:
    row = get_member(db, hackathon_id, user_id)
    return row is not None and row.followed_at is not None


def ensure_section_states(db: Session, hackathon_id) -> None:
    hackathon = db.get(Hackathon, hackathon_id)
    if hackathon is None:
        return
    current = dict(hackathon.section_states or {})
    for section in SECTION_KEYS:
        current.setdefault(section, "not_specified")
    hackathon.section_states = current
    touch(hackathon, "section_states")


def _find(rows, row_id, label: str):
    for row in rows:
        if row.id == row_id:
            return row
    raise AppError(404, "not_found", f"{label} not found")


def is_bookmarked(db: Session, hackathon_id, user_id) -> bool:
    row = get_member(db, hackathon_id, user_id)
    return row is not None and row.bookmarked_at is not None


def bookmark(db: Session, user: User, hackathon: Hackathon) -> None:
    if hackathon.lifecycle not in PUBLIC_LIFECYCLES:
        raise AppError(404, "not_found", "Hackathon not found")
    if not is_bookmarked(db, hackathon.id, user.id):
        ensure_member(db, hackathon.id, user.id).bookmarked_at = datetime.now(UTC)


def unbookmark(db: Session, user: User, hackathon: Hackathon) -> None:
    row = get_member(db, hackathon.id, user.id)
    if row is not None:
        row.bookmarked_at = None
        prune_member(db, row)


def _saved(db: Session, user_id, column):
    rows = db.scalars(
        select(Hackathon)
        .join(HackathonMember, HackathonMember.hackathon_id == Hackathon.id)
        .where(HackathonMember.user_id == user_id, column.is_not(None), Hackathon.lifecycle.in_(PUBLIC_LIFECYCLES))
        .order_by(column.desc())
    ).unique().all()
    return [to_card(row) for row in rows]


def my_following(db: Session, user: User):
    return _saved(db, user.id, HackathonMember.followed_at)


def my_bookmarks(db: Session, user: User):
    return _saved(db, user.id, HackathonMember.bookmarked_at)


def stance_for(db: Session, hackathon_id, user_id) -> str | None:
    row = get_member(db, hackathon_id, user_id)
    return row.stance if row is not None else None


def set_stance(db: Session, user: User, hackathon: Hackathon, stance: str) -> None:
    if hackathon.lifecycle not in PUBLIC_LIFECYCLES:
        raise AppError(404, "not_found", "Hackathon not found")
    ensure_member(db, hackathon.id, user.id).stance = stance


def set_interest(db: Session, user: User, hackathon: Hackathon) -> None:
    if hackathon.lifecycle not in PUBLIC_LIFECYCLES:
        raise AppError(404, "not_found", "Hackathon not found")
    ensure_member(db, hackathon.id, user.id).interested_at = datetime.now(UTC)
    notifications.schedule_interest(db, hackathon, user.id)


def clear_interest(db: Session, user: User, hackathon: Hackathon) -> None:
    row = get_member(db, hackathon.id, user.id)
    if row is not None:
        row.interested_at = None
        notifications.clear_interest_job(db, hackathon.id, user.id)
        prune_member(db, row)


def is_interested(db: Session, hackathon_id, user_id) -> bool:
    row = get_member(db, hackathon_id, user_id)
    return bool(row and row.interested_at is not None)


def my_interests(db: Session, user: User) -> list[str]:
    rows = db.execute(
        select(Hackathon.slug)
        .join(HackathonMember, HackathonMember.hackathon_id == Hackathon.id)
        .where(
            HackathonMember.user_id == user.id,
            HackathonMember.interested_at.is_not(None),
            Hackathon.lifecycle.in_(PUBLIC_LIFECYCLES),
        )
        .order_by(Hackathon.updated_at.desc())
    ).all()
    return [slug for (slug,) in rows]


def clear_stance(db: Session, user: User, hackathon: Hackathon) -> None:
    row = get_member(db, hackathon.id, user.id)
    if row is not None:
        row.stance = None
        prune_member(db, row)


def my_stances(db: Session, user: User) -> list[tuple[str, str]]:
    rows = db.execute(
        select(Hackathon.slug, HackathonMember.stance)
        .join(Hackathon, Hackathon.id == HackathonMember.hackathon_id)
        .where(
            HackathonMember.user_id == user.id,
            HackathonMember.stance.is_not(None),
            Hackathon.lifecycle.in_(PUBLIC_LIFECYCLES),
        )
        .order_by(Hackathon.updated_at.desc())
    ).all()
    return [(slug, stance) for slug, stance in rows]


def my_queries(db: Session, user: User) -> list[StudentQuery]:
    return list(
        db.scalars(
            select(StudentQuery)
            .where(StudentQuery.author_id == user.id)
            .options(*selectinload_hackathon())
            .order_by(StudentQuery.created_at.desc())
        ).all()
    )


def selectinload_hackathon():
    from sqlalchemy.orm import selectinload

    return (selectinload(StudentQuery.hackathon),)


def update_query(db: Session, actor: User, query_id, status: str | None, assignee_id):
    row = db.scalar(
        select(StudentQuery).where(StudentQuery.id == query_id).options(*selectinload_hackathon(), selectinload_assignee())
    )
    if row is None:
        raise AppError(404, "not_found", "Question not found")
    hackathon = get_hackathon(db, row.hackathon_id)
    from app.deps import can_edit

    if not can_edit(db, actor, hackathon):
        raise AppError(403, "forbidden", "You are not assigned to this hackathon")
    if status is not None:
        row.status = status
    if assignee_id is not None:
        assignee = db.get(User, assignee_id)
        if assignee is None or assignee.role not in {"coordinator", "super_admin"}:
            raise AppError(422, "invalid_assignee", "Assign a coordinator or administrator")
        row.assignee_id = assignee.id
    db.flush()
    return row


def selectinload_assignee():
    from sqlalchemy.orm import selectinload

    return selectinload(StudentQuery.assignee)


def admin_queries(db: Session, actor: User) -> list[StudentQuery]:
    stmt = select(StudentQuery).options(*selectinload_hackathon(), selectinload_assignee(), selectinload_author())
    ids = scoped_ids(db, actor)
    if ids is not None:
        stmt = stmt.where(StudentQuery.hackathon_id.in_(ids or [UUID(int=0)]))
    return list(db.scalars(stmt.order_by(StudentQuery.created_at.desc()).limit(100)).all())


def selectinload_author():
    from sqlalchemy.orm import selectinload

    return selectinload(StudentQuery.author)


def admin_announcements(db: Session, actor: User):
    stmt = select(Hackathon)
    ids = scoped_ids(db, actor)
    if ids is not None:
        stmt = stmt.where(Hackathon.id.in_(ids or [UUID(int=0)]))
    found = []
    for hackathon in db.scalars(stmt):
        for item in items(hackathon, "announcements"):
            object.__setattr__(item, "hackathon", hackathon)
            object.__setattr__(item, "hackathon_id", hackathon.id)
            found.append(item)
    found.sort(
        key=lambda item: (
            item.published_at is None,
            -(item.published_at.timestamp() if item.published_at else 0),
            item.position or 0,
        )
    )
    return found[:100]
