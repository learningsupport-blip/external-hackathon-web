from datetime import UTC, datetime

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import (
    PUBLIC_LIFECYCLES,
    SECTION_KEYS,
    Announcement,
    Deliverable,
    Faq,
    Hackathon,
    HackathonBookmark,
    HackathonFollower,
    HackathonStance,
    JudgingCriterion,
    Prize,
    QueryResponse,
    SectionState,
    StudentQuery,
    Track,
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


def track_out(row: Track) -> TrackOut:
    return TrackOut(id=row.id, name=row.name, requirements=row.requirements, position=row.position)


def deliverable_out(row: Deliverable) -> DeliverableOut:
    return DeliverableOut(id=row.id, title=row.title, detail=row.detail, required=row.required, position=row.position)


def prize_out(row: Prize) -> PrizeOut:
    return PrizeOut(id=row.id, label=row.label, detail=row.detail, position=row.position)


def judging_out(row: JudgingCriterion) -> JudgingOut:
    return JudgingOut(id=row.id, title=row.title, detail=row.detail, weight=row.weight, position=row.position)


def faq_out(row: Faq) -> FaqOut:
    return FaqOut(id=row.id, question=row.question, answer=row.answer, position=row.position)


def announcement_out(row: Announcement) -> AnnouncementOut:
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
            for item in row.responses
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
        return bool(hackathon.tags or hackathon.problem_statements)
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


def add_track(db: Session, actor: User, hackathon: Hackathon, payload: TrackIn) -> Track:
    row = Track(
        hackathon_id=hackathon.id,
        name=payload.name,
        requirements=payload.requirements,
        position=_position(hackathon.tracks, payload.position),
    )
    db.add(row)
    db.flush()
    _history(db, actor, hackathon, "track", row, "created", None, {"name": row.name})
    return row


def update_track(db: Session, actor: User, hackathon: Hackathon, row_id, payload: TrackIn) -> Track:
    row = _find(hackathon.tracks, row_id, "Track")
    row.name = payload.name
    row.requirements = payload.requirements
    if payload.position is not None:
        row.position = payload.position
    _history(db, actor, hackathon, "track", row, "updated", None, {"name": row.name, "position": row.position})
    return row


def delete_track(db: Session, actor: User, hackathon: Hackathon, row_id) -> None:
    row = _find(hackathon.tracks, row_id, "Track")
    _history(db, actor, hackathon, "track", row, "deleted", {"name": row.name}, None)
    db.delete(row)


def add_deliverable(db: Session, actor: User, hackathon: Hackathon, payload: DeliverableIn) -> Deliverable:
    row = Deliverable(
        hackathon_id=hackathon.id,
        title=payload.title,
        detail=payload.detail,
        required=payload.required,
        position=_position(hackathon.deliverables, payload.position),
    )
    db.add(row)
    db.flush()
    _history(db, actor, hackathon, "deliverable", row, "created", None, {"title": row.title})
    return row


def update_deliverable(db: Session, actor: User, hackathon: Hackathon, row_id, payload: DeliverableIn) -> Deliverable:
    row = _find(hackathon.deliverables, row_id, "Deliverable")
    row.title = payload.title
    row.detail = payload.detail
    row.required = payload.required
    if payload.position is not None:
        row.position = payload.position
    _history(db, actor, hackathon, "deliverable", row, "updated", None, {"title": row.title})
    return row


def delete_deliverable(db: Session, actor: User, hackathon: Hackathon, row_id) -> None:
    row = _find(hackathon.deliverables, row_id, "Deliverable")
    _history(db, actor, hackathon, "deliverable", row, "deleted", {"title": row.title}, None)
    db.delete(row)


def add_prize(db: Session, actor: User, hackathon: Hackathon, payload: PrizeIn) -> Prize:
    row = Prize(
        hackathon_id=hackathon.id,
        label=payload.label,
        detail=payload.detail,
        position=_position(hackathon.prizes, payload.position),
    )
    db.add(row)
    db.flush()
    _history(db, actor, hackathon, "prize", row, "created", None, {"label": row.label})
    return row


def update_prize(db: Session, actor: User, hackathon: Hackathon, row_id, payload: PrizeIn) -> Prize:
    row = _find(hackathon.prizes, row_id, "Prize")
    row.label = payload.label
    row.detail = payload.detail
    if payload.position is not None:
        row.position = payload.position
    _history(db, actor, hackathon, "prize", row, "updated", None, {"label": row.label})
    return row


def delete_prize(db: Session, actor: User, hackathon: Hackathon, row_id) -> None:
    row = _find(hackathon.prizes, row_id, "Prize")
    _history(db, actor, hackathon, "prize", row, "deleted", {"label": row.label}, None)
    db.delete(row)


def add_judging(db: Session, actor: User, hackathon: Hackathon, payload: JudgingIn) -> JudgingCriterion:
    row = JudgingCriterion(
        hackathon_id=hackathon.id,
        title=payload.title,
        detail=payload.detail,
        weight=payload.weight,
        position=_position(hackathon.judging_criteria, payload.position),
    )
    db.add(row)
    db.flush()
    _history(db, actor, hackathon, "judging", row, "created", None, {"title": row.title, "weight": row.weight})
    return row


def update_judging(db: Session, actor: User, hackathon: Hackathon, row_id, payload: JudgingIn) -> JudgingCriterion:
    row = _find(hackathon.judging_criteria, row_id, "Judging criterion")
    row.title = payload.title
    row.detail = payload.detail
    row.weight = payload.weight
    if payload.position is not None:
        row.position = payload.position
    _history(db, actor, hackathon, "judging", row, "updated", None, {"title": row.title})
    return row


def delete_judging(db: Session, actor: User, hackathon: Hackathon, row_id) -> None:
    row = _find(hackathon.judging_criteria, row_id, "Judging criterion")
    _history(db, actor, hackathon, "judging", row, "deleted", {"title": row.title}, None)
    db.delete(row)


def add_faq(db: Session, actor: User, hackathon: Hackathon, payload: FaqIn) -> Faq:
    row = Faq(
        hackathon_id=hackathon.id,
        question=payload.question,
        answer=payload.answer,
        position=_position(hackathon.faqs, payload.position),
    )
    db.add(row)
    db.flush()
    _history(db, actor, hackathon, "faq", row, "created", None, {"question": row.question})
    return row


def update_faq(db: Session, actor: User, hackathon: Hackathon, row_id, payload: FaqIn) -> Faq:
    row = _find(hackathon.faqs, row_id, "FAQ")
    row.question = payload.question
    row.answer = payload.answer
    if payload.position is not None:
        row.position = payload.position
    _history(db, actor, hackathon, "faq", row, "updated", None, {"question": row.question})
    return row


def delete_faq(db: Session, actor: User, hackathon: Hackathon, row_id) -> None:
    row = _find(hackathon.faqs, row_id, "FAQ")
    _history(db, actor, hackathon, "faq", row, "deleted", {"question": row.question}, None)
    db.delete(row)


def add_announcement(db: Session, actor: User, hackathon: Hackathon, payload: AnnouncementIn) -> Announcement:
    row = Announcement(
        hackathon_id=hackathon.id,
        title=payload.title,
        body=payload.body,
        published_at=payload.published_at,
        position=_position(hackathon.announcements, payload.position),
    )
    db.add(row)
    db.flush()
    _history(db, actor, hackathon, "announcement", row, "created", None, {"title": row.title})
    if row.published_at is not None:
        notifications.schedule_announcement(db, hackathon, row)
    return row


def update_announcement(db: Session, actor: User, hackathon: Hackathon, row_id, payload: AnnouncementIn) -> Announcement:
    row = _find(hackathon.announcements, row_id, "Announcement")
    was_draft = row.published_at is None
    row.title = payload.title
    row.body = payload.body
    row.published_at = payload.published_at
    if payload.position is not None:
        row.position = payload.position
    _history(db, actor, hackathon, "announcement", row, "updated", None, {"title": row.title})
    if was_draft and row.published_at is not None:
        notifications.schedule_announcement(db, hackathon, row)
    return row


def delete_announcement(db: Session, actor: User, hackathon: Hackathon, row_id) -> None:
    row = _find(hackathon.announcements, row_id, "Announcement")
    _history(db, actor, hackathon, "announcement", row, "deleted", {"title": row.title}, None)
    db.delete(row)


def set_section_states(db: Session, actor: User, hackathon: Hackathon, states: list[SectionStateIn]) -> Hackathon:
    by_section = {item.section: item for item in hackathon.section_states}
    for incoming in states:
        if incoming.state == "confirmed" and not section_has_content(hackathon, incoming.section):
            raise AppError(422, "empty_section", f"{incoming.section} is marked confirmed but has no information")
        row = by_section.get(incoming.section)
        if row is None:
            row = SectionState(hackathon_id=hackathon.id, section=incoming.section, state=incoming.state)
            db.add(row)
        else:
            row.state = incoming.state
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
        hackathon_id=hackathon.id, author_id=user.id, body=body, is_public=is_public, created_at=datetime.now(UTC)
    )
    db.add(row)
    db.flush()
    return row


def answer_query(db: Session, actor: User, hackathon: Hackathon, query_id, body: str) -> StudentQuery:
    row = _find(hackathon.queries, query_id, "Question")
    answer = QueryResponse(query_id=row.id, author_id=actor.id, body=body, official=True, created_at=datetime.now(UTC))
    row.responses.append(answer)
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
    exists = db.scalar(
        select(HackathonFollower.user_id).where(
            HackathonFollower.hackathon_id == hackathon.id, HackathonFollower.user_id == user.id
        )
    )
    if exists is None:
        db.add(HackathonFollower(hackathon_id=hackathon.id, user_id=user.id))
        db.flush()
    notifications.schedule_for_user(db, hackathon, user.id)


def unfollow(db: Session, user: User, hackathon: Hackathon) -> None:
    db.query(HackathonFollower).filter(
        HackathonFollower.hackathon_id == hackathon.id, HackathonFollower.user_id == user.id
    ).delete()
    notifications.cancel_user_jobs(db, hackathon.id, user.id)


def is_following(db: Session, hackathon_id, user_id) -> bool:
    return (
        db.scalar(
            select(HackathonFollower.user_id).where(
                HackathonFollower.hackathon_id == hackathon_id, HackathonFollower.user_id == user_id
            )
        )
        is not None
    )


def ensure_section_states(db: Session, hackathon_id) -> None:
    for section in SECTION_KEYS:
        db.add(SectionState(hackathon_id=hackathon_id, section=section, state="not_specified"))


def _find(rows, row_id, label: str):
    for row in rows:
        if row.id == row_id:
            return row
    raise AppError(404, "not_found", f"{label} not found")


def is_bookmarked(db: Session, hackathon_id, user_id) -> bool:
    return (
        db.scalar(
            select(HackathonBookmark.user_id).where(
                HackathonBookmark.hackathon_id == hackathon_id, HackathonBookmark.user_id == user_id
            )
        )
        is not None
    )


def bookmark(db: Session, user: User, hackathon: Hackathon) -> None:
    if hackathon.lifecycle not in PUBLIC_LIFECYCLES:
        raise AppError(404, "not_found", "Hackathon not found")
    if not is_bookmarked(db, hackathon.id, user.id):
        db.add(HackathonBookmark(hackathon_id=hackathon.id, user_id=user.id))


def unbookmark(db: Session, user: User, hackathon: Hackathon) -> None:
    db.query(HackathonBookmark).filter(
        HackathonBookmark.hackathon_id == hackathon.id, HackathonBookmark.user_id == user.id
    ).delete()


def _saved(db: Session, model, user_id):
    rows = db.scalars(
        select(Hackathon)
        .join(model, model.hackathon_id == Hackathon.id)
        .where(model.user_id == user_id, Hackathon.lifecycle.in_(PUBLIC_LIFECYCLES))
        .order_by(model.created_at.desc())
    ).unique().all()
    return [to_card(row) for row in rows]


def my_following(db: Session, user: User):
    return _saved(db, HackathonFollower, user.id)


def my_bookmarks(db: Session, user: User):
    return _saved(db, HackathonBookmark, user.id)


def stance_for(db: Session, hackathon_id, user_id) -> str | None:
    return db.scalar(
        select(HackathonStance.stance).where(
            HackathonStance.hackathon_id == hackathon_id, HackathonStance.user_id == user_id
        )
    )


def set_stance(db: Session, user: User, hackathon: Hackathon, stance: str) -> None:
    if hackathon.lifecycle not in PUBLIC_LIFECYCLES:
        raise AppError(404, "not_found", "Hackathon not found")
    row = db.scalar(
        select(HackathonStance).where(
            HackathonStance.hackathon_id == hackathon.id, HackathonStance.user_id == user.id
        )
    )
    if row:
        row.stance = stance
        return
    db.add(HackathonStance(hackathon_id=hackathon.id, user_id=user.id, stance=stance))


def clear_stance(db: Session, user: User, hackathon: Hackathon) -> None:
    db.query(HackathonStance).filter(
        HackathonStance.hackathon_id == hackathon.id, HackathonStance.user_id == user.id
    ).delete()


def my_stances(db: Session, user: User) -> list[tuple[str, str]]:
    rows = db.execute(
        select(Hackathon.slug, HackathonStance.stance)
        .join(Hackathon, Hackathon.id == HackathonStance.hackathon_id)
        .where(HackathonStance.user_id == user.id, Hackathon.lifecycle.in_(PUBLIC_LIFECYCLES))
        .order_by(HackathonStance.created_at.desc())
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

    return selectinload(StudentQuery.hackathon), selectinload(StudentQuery.responses)


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


def admin_announcements(db: Session, actor: User) -> list[Announcement]:
    stmt = select(Announcement).join(Hackathon).order_by(Announcement.published_at.desc().nulls_last(), Announcement.position)
    ids = scoped_ids(db, actor)
    if ids is not None:
        stmt = stmt.where(Announcement.hackathon_id.in_(ids or [UUID(int=0)]))
    return list(db.scalars(stmt.limit(100)).all())
