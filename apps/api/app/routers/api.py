import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog import all_categories
from app.config import Settings, get_settings
from app.database import get_db
from app.deps import check_origin, rate_limit, require_editor, require_staff, require_super_admin, require_user, user_from_request
from app.errors import AppError
from app.models import User
from app.schemas import (
    AdminAnnouncementOut,
    AdminPage,
    AdminQueryOut,
    AnnouncementIn,
    AnnouncementOut,
    CalendarEvent,
    CalendarResponse,
    CategoryOut,
    CoordinatorIn,
    CreateUserIn,
    DeliverableIn,
    DeliverableOut,
    DevLoginIn,
    EmailCodeIn,
    EmailCodeOut,
    EmailConfirmIn,
    EmailConfirmOut,
    ExtraNoticeIn,
    ExtraNoticeOut,
    FaqIn,
    FaqOut,
    HackathonAdmin,
    HackathonCard,
    HackathonCreate,
    HackathonPublic,
    HackathonUpdate,
    HistoryOut,
    HomeOut,
    InternalUpdate,
    JudgingIn,
    JudgingOut,
    LifecycleIn,
    LoginIn,
    MilestoneIn,
    MilestoneOut,
    MyQueryOut,
    ImportCommitIn,
    ImportExtractOut,
    SheetImportOut,
    SheetSkipOut,
    SheetStatusOut,
    ImportUrlIn,
    NotificationOut,
    NotificationPreferenceIn,
    NotificationPreferenceOut,
    Page,
    PrizeIn,
    PrizeOut,
    QueryIn,
    RegisterIn,
    SignupOptions,
    StanceIn,
    StanceOut,
    QueryOut,
    QueryPatch,
    QueryResponseIn,
    ResourceIn,
    ResourceOut,
    SectionStatesIn,
    StatsOut,
    TrackIn,
    TrackOut,
    UserOut,
)
from app.services import accounts, content, importing, notifications as notify, sheets
from app.security import (
    clear_session,
    google_auth_url,
    google_userinfo,
    start_session,
    upsert_user,
    write_audit,
)
from app.services import hackathons as service

router = APIRouter(prefix="/api/v1")


def _user_out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, name=user.name, avatar_url=user.avatar_url, role=user.role)


def _page_card(rows, total, page, page_size) -> Page:
    return Page(items=[service.to_card(item) for item in rows], page=page, page_size=page_size, total=total)


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/categories", response_model=list[CategoryOut])
def categories() -> list[CategoryOut]:
    return [CategoryOut(id=item["id"], name=item["name"], slug=item["slug"]) for item in all_categories()]


@router.post("/auth/dev-login", response_model=UserOut)
def dev_login(
    payload: DevLoginIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserOut:
    if settings.app_env != "development":
        raise AppError(404, "not_found", "Not found")
    check_origin(request, settings)
    rate_limit(request, "dev-login", limit=20, window=600)
    user = upsert_user(db, settings, email=payload.email, name=payload.name, avatar_url=None, google_sub=None)
    start_session(db, settings, user, response)
    write_audit(db, action="auth.dev_login", actor_id=user.id, entity_type="user", entity_id=str(user.id), ip=request.client.host if request.client else None)
    return _user_out(user)


@router.get("/auth/options", response_model=SignupOptions)
def auth_options() -> SignupOptions:
    return SignupOptions.model_validate(accounts.signup_options())


@router.post("/auth/email/code", response_model=EmailCodeOut)
def email_code(
    payload: EmailCodeIn,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EmailCodeOut:
    check_origin(request, settings)
    rate_limit(request, "email-code", limit=5, window=600)
    dev_code = accounts.request_code(db, settings, payload.email)
    message = "We sent a verification code to your email."
    if dev_code:
        message = "Email delivery is not configured, so the code is shown here."
    return EmailCodeOut(message=message, dev_code=dev_code)


@router.post("/auth/email/confirm", response_model=EmailConfirmOut)
def email_confirm(
    payload: EmailConfirmIn,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EmailConfirmOut:
    check_origin(request, settings)
    rate_limit(request, "email-confirm", limit=10, window=600)
    token = accounts.confirm_code(db, payload.email, payload.code)
    return EmailConfirmOut(verification_token=token)


@router.post("/auth/register", response_model=UserOut, status_code=201)
def register(
    payload: RegisterIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserOut:
    check_origin(request, settings)
    rate_limit(request, "register", limit=10, window=600)
    user = accounts.register_user(db, payload)
    if payload.email in settings.admin_email_set:
        user.role = "super_admin"
    start_session(db, settings, user, response)
    write_audit(db, action="auth.register", actor_id=user.id, entity_type="user", entity_id=str(user.id), ip=request.client.host if request.client else None)
    return _user_out(user)


@router.post("/auth/login", response_model=UserOut)
def login(
    payload: LoginIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserOut:
    check_origin(request, settings)
    rate_limit(request, "login", limit=10, window=600)
    user = accounts.login_user(db, payload.email, payload.password)
    start_session(db, settings, user, response)
    write_audit(db, action="auth.login", actor_id=user.id, entity_type="user", entity_id=str(user.id), ip=request.client.host if request.client else None)
    db.commit()
    return _user_out(user)


@router.get("/auth/google")
def google_start(request: Request, settings: Settings = Depends(get_settings)):
    rate_limit(request, "google", limit=20, window=600)
    state = secrets.token_urlsafe(24)
    redirect = RedirectResponse(google_auth_url(settings, state), status_code=302)
    redirect.set_cookie("oauth_state", state, httponly=True, max_age=600, samesite="lax", secure=settings.is_production, path="/")
    return redirect


@router.get("/auth/google/callback")
def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    saved = request.cookies.get("oauth_state")
    failure = RedirectResponse(f"{settings.web_origin}/login?error=google", status_code=302)
    failure.delete_cookie("oauth_state", path="/")
    if not code or not state or not saved or state != saved:
        return failure
    profile = google_userinfo(settings, code)
    user = upsert_user(
        db,
        settings,
        email=profile["email"],
        name=profile.get("name") or profile["email"],
        avatar_url=profile.get("picture"),
        google_sub=profile.get("sub"),
    )
    destination = "/admin" if user.role in {"coordinator", "super_admin"} else "/"
    redirect = RedirectResponse(f"{settings.web_origin}{destination}", status_code=302)
    start_session(db, settings, user, redirect)
    redirect.delete_cookie("oauth_state", path="/")
    write_audit(db, action="auth.google", actor_id=user.id, entity_type="user", entity_id=str(user.id), ip=request.client.host if request.client else None)
    return redirect


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> None:
    check_origin(request, settings)
    clear_session(db, settings, request.cookies.get(settings.session_cookie_name), response)


@router.get("/auth/me", response_model=UserOut)
def me(request: Request, db: Session = Depends(get_db)) -> UserOut:
    return _user_out(require_user(request, db))


@router.get("/hackathons", response_model=Page)
def list_hackathons(
    q: str | None = None,
    category: str | None = None,
    mode: str | None = None,
    participation: str | None = None,
    difficulty: str | None = None,
    registration: str | None = None,
    sort: str = "recent",
    featured: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
) -> Page:
    if sort not in {"recent", "registration_deadline", "submission_deadline", "event_date"}:
        raise AppError(422, "invalid_sort", "Unknown sort")
    rows, total = service.list_public(
        db,
        q=q,
        category=category,
        mode=mode,
        participation=participation,
        difficulty=difficulty,
        registration=registration,
        sort=sort,
        featured=featured,
        page=page,
        page_size=page_size,
    )
    return _page_card(rows, total, page, page_size)


@router.get("/hackathons/due", response_model=list[HackathonCard])
def hackathons_due(days: int = Query(default=3, ge=1, le=30), db: Session = Depends(get_db)) -> list[HackathonCard]:
    return [service.to_card(item) for item in service.due_soon(db, days=days)]


@router.get("/hackathons/{slug}", response_model=HackathonPublic)
def hackathon_detail(slug: str, request: Request, db: Session = Depends(get_db)) -> HackathonPublic:
    hackathon = service.get_public_by_slug(db, slug)
    user = user_from_request(request, db)
    following = bool(user and content.is_following(db, hackathon.id, user.id))
    bookmarked = bool(user and content.is_bookmarked(db, hackathon.id, user.id))
    stance = content.stance_for(db, hackathon.id, user.id) if user else None
    interested = content.is_interested(db, hackathon.id, user.id) if user else False
    return service.to_public(
        hackathon, following=following, bookmarked=bookmarked, stance=stance, interested=interested
    )


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


@router.get("/calendar", response_model=CalendarResponse)
def calendar(
    start: datetime,
    end: datetime,
    category: str | None = None,
    type: str | None = Query(default=None, alias="type"),
    hackathon: str | None = None,
    deadlines: bool = False,
    db: Session = Depends(get_db),
) -> CalendarResponse:
    start = _aware(start)
    end = _aware(end)
    if end < start:
        raise AppError(422, "invalid_range", "Calendar end must be after the start")
    if deadlines:
        marked = service.deadline_events(db, start=start, end=end, category=category, hackathon=hackathon)
        items = [
            CalendarEvent(
                id=row.id,
                title=row.name,
                hackathon_name=row.name,
                hackathon_slug=row.slug,
                type="deadline",
                starts_at=when,
                ends_at=when,
                timezone=row.timezone,
            )
            for row, when in marked
        ]
    else:
        rows = service.calendar_events(db, start=start, end=end, category=category, event_type=type, hackathon=hackathon)
        items = [
            CalendarEvent(
                id=item.id,
                title=item.title,
                hackathon_name=item.hackathon.name,
                hackathon_slug=item.hackathon.slug,
                type=item.type,
                starts_at=item.starts_at,
                ends_at=item.ends_at,
                timezone=item.hackathon.timezone,
            )
            for item in rows
        ]
    return CalendarResponse(
        items=items,
        time_label="Event times are stored in UTC and labeled with each hackathon timezone",
    )


@router.get("/home", response_model=HomeOut)
def home(db: Session = Depends(get_db)) -> HomeOut:
    now = datetime.now(UTC)
    end = now + timedelta(days=60)
    featured, _featured_total = service.list_public(
        db,
        q=None,
        category=None,
        mode=None,
        participation=None,
        difficulty=None,
        registration=None,
        sort="recent",
        featured=True,
        page=1,
        page_size=6,
    )
    recent, _recent_total = service.list_public(
        db,
        q=None,
        category=None,
        mode=None,
        participation=None,
        difficulty=None,
        registration=None,
        sort="recent",
        featured=None,
        page=1,
        page_size=6,
    )
    events = service.calendar_events(db, start=now, end=end, category=None, event_type=None, hackathon=None)
    deadlines = [
        CalendarEvent(
            id=item.id,
            title=item.title,
            hackathon_name=item.hackathon.name,
            hackathon_slug=item.hackathon.slug,
            type=item.type,
            starts_at=item.starts_at,
            ends_at=item.ends_at,
            timezone=item.hackathon.timezone,
        )
        for item in events[:6]
    ]
    return HomeOut(
        featured=[service.to_card(item) for item in featured],
        recent=[service.to_card(item) for item in recent],
        categories=[CategoryOut(id=item["id"], name=item["name"], slug=item["slug"]) for item in all_categories()],
        due=[service.to_card(item) for item in service.due_soon(db, days=3)],
        deadlines=deadlines,
    )


@router.get("/admin/stats", response_model=StatsOut)
def admin_stats(request: Request, db: Session = Depends(get_db)) -> StatsOut:
    user = require_user(request, db)
    require_staff(user)
    return service.stats(db, user)


@router.get("/admin/hackathons", response_model=AdminPage)
def admin_hackathons(
    request: Request,
    q: str | None = None,
    lifecycle: str | None = None,
    sort: str = "updated",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> AdminPage:
    user = require_user(request, db)
    require_staff(user)
    if sort not in {"updated", "name", "deadline"}:
        raise AppError(422, "invalid_sort", "Unknown sort")
    rows, total = service.list_admin(db, user, q=q, lifecycle=lifecycle, sort=sort, page=page, page_size=page_size)
    return AdminPage(items=[service.to_card(item) for item in rows], page=page, page_size=page_size, total=total)


@router.post("/admin/hackathons", response_model=HackathonAdmin, status_code=201)
def create_hackathon(
    payload: HackathonCreate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HackathonAdmin:
    check_origin(request, settings)
    user = require_user(request, db)
    require_staff(user)
    return service.to_admin(service.create_hackathon(db, settings, user, payload))


@router.post("/admin/hackathons/import/extract", response_model=ImportExtractOut)
def extract_hackathon_import(
    payload: ImportUrlIn,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ImportExtractOut:
    check_origin(request, settings)
    rate_limit(request, "import-extract", limit=8, window=600)
    user = require_user(request, db)
    require_staff(user)
    proposal, sources, missing = importing.extract_from_url(settings, payload.url)
    status = sheets.sheet_status(settings)
    sheet_row = None
    sheet_error = None
    if status["connected"]:
        try:
            sheet_row = sheets.publish_extract(settings, proposal, sources[0] if sources else payload.url)
        except AppError as exc:
            sheet_error = exc.message
    return ImportExtractOut(
        proposal=proposal,
        sources=sources,
        missing=missing,
        sheet_connected=status["connected"],
        sheet_url=status["url"],
        sheet_row=sheet_row,
        sheet_error=sheet_error,
    )


@router.get("/admin/hackathons/import/sheet", response_model=SheetStatusOut)
def hackathon_sheet_status(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SheetStatusOut:
    user = require_user(request, db)
    require_staff(user)
    return SheetStatusOut(**sheets.sheet_status(settings))


@router.post("/admin/hackathons/import/sheet", response_model=SheetImportOut)
def import_ready_sheet_rows(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SheetImportOut:
    check_origin(request, settings)
    user = require_user(request, db)
    require_staff(user)
    result = sheets.pull_ready(db, settings, user)
    return SheetImportOut(
        created_count=len(result["created_ids"]),
        created_ids=result["created_ids"],
        skipped=[SheetSkipOut(row=item.row, reason=item.reason) for item in result["skipped"]],
    )


@router.post("/admin/hackathons/import", response_model=HackathonAdmin, status_code=201)
def commit_hackathon_import(
    payload: ImportCommitIn,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HackathonAdmin:
    check_origin(request, settings)
    user = require_user(request, db)
    require_staff(user)
    return service.to_admin(importing.commit_import(db, settings, user, payload.proposal))


@router.get("/admin/hackathons/{hackathon_id}", response_model=HackathonAdmin)
def admin_hackathon(hackathon_id: UUID, request: Request, db: Session = Depends(get_db)) -> HackathonAdmin:
    user = require_user(request, db)
    hackathon = service.get_hackathon(db, hackathon_id)
    require_editor(db, user, hackathon)
    return service.to_admin(hackathon)


@router.patch("/admin/hackathons/{hackathon_id}", response_model=HackathonAdmin)
def patch_hackathon(
    hackathon_id: UUID,
    payload: HackathonUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> HackathonAdmin:
    check_origin(request)
    user = require_user(request, db)
    hackathon = service.get_hackathon(db, hackathon_id)
    require_editor(db, user, hackathon)
    return service.to_admin(service.update_hackathon(db, user, hackathon, payload))


@router.patch("/admin/hackathons/{hackathon_id}/internal", response_model=HackathonAdmin)
def patch_internal(
    hackathon_id: UUID,
    payload: InternalUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> HackathonAdmin:
    check_origin(request)
    user = require_user(request, db)
    hackathon = service.get_hackathon(db, hackathon_id)
    require_editor(db, user, hackathon)
    return service.to_admin(service.update_internal(db, user, hackathon, payload))


@router.post("/admin/hackathons/{hackathon_id}/lifecycle", response_model=HackathonAdmin)
def lifecycle(hackathon_id: UUID, payload: LifecycleIn, request: Request, db: Session = Depends(get_db)) -> HackathonAdmin:
    check_origin(request)
    user = require_user(request, db)
    hackathon = service.get_hackathon(db, hackathon_id)
    require_editor(db, user, hackathon)
    ip = request.client.host if request.client else None
    return service.to_admin(service.change_lifecycle(db, user, hackathon, payload.lifecycle, ip))


@router.delete("/admin/hackathons/{hackathon_id}", status_code=204)
def delete_hackathon(hackathon_id: UUID, request: Request, db: Session = Depends(get_db)) -> None:
    check_origin(request)
    user = require_user(request, db)
    hackathon = service.get_hackathon(db, hackathon_id)
    require_editor(db, user, hackathon)
    service.delete_draft(db, user, hackathon)


@router.post("/admin/hackathons/{hackathon_id}/milestones", response_model=MilestoneOut, status_code=201)
def create_milestone(
    hackathon_id: UUID, payload: MilestoneIn, request: Request, db: Session = Depends(get_db)
) -> MilestoneOut:
    check_origin(request)
    user = require_user(request, db)
    hackathon = service.get_hackathon(db, hackathon_id)
    require_editor(db, user, hackathon)
    return service._milestone_out(service.add_milestone(db, user, hackathon, payload))


@router.post("/admin/hackathons/{hackathon_id}/milestones/standard", response_model=HackathonAdmin)
def standard_milestones(hackathon_id: UUID, request: Request, db: Session = Depends(get_db)) -> HackathonAdmin:
    check_origin(request)
    user = require_user(request, db)
    hackathon = service.get_hackathon(db, hackathon_id)
    require_editor(db, user, hackathon)
    return service.to_admin(service.add_standard_milestones(db, user, hackathon))


@router.put("/admin/hackathons/{hackathon_id}/milestones/{milestone_id}", response_model=MilestoneOut)
def put_milestone(
    hackathon_id: UUID,
    milestone_id: UUID,
    payload: MilestoneIn,
    request: Request,
    db: Session = Depends(get_db),
) -> MilestoneOut:
    check_origin(request)
    user = require_user(request, db)
    hackathon = service.get_hackathon(db, hackathon_id)
    require_editor(db, user, hackathon)
    return service._milestone_out(service.update_milestone(db, user, hackathon, milestone_id, payload))


@router.delete("/admin/hackathons/{hackathon_id}/milestones/{milestone_id}", status_code=204)
def remove_milestone(hackathon_id: UUID, milestone_id: UUID, request: Request, db: Session = Depends(get_db)) -> None:
    check_origin(request)
    user = require_user(request, db)
    hackathon = service.get_hackathon(db, hackathon_id)
    require_editor(db, user, hackathon)
    service.delete_milestone(db, user, hackathon, milestone_id)


@router.post("/admin/hackathons/{hackathon_id}/resources", response_model=ResourceOut, status_code=201)
def create_resource(
    hackathon_id: UUID, payload: ResourceIn, request: Request, db: Session = Depends(get_db)
) -> ResourceOut:
    check_origin(request)
    user = require_user(request, db)
    hackathon = service.get_hackathon(db, hackathon_id)
    require_editor(db, user, hackathon)
    return service._resource_out(service.add_resource(db, user, hackathon, payload))


@router.delete("/admin/hackathons/{hackathon_id}/resources/{resource_id}", status_code=204)
def remove_resource(hackathon_id: UUID, resource_id: UUID, request: Request, db: Session = Depends(get_db)) -> None:
    check_origin(request)
    user = require_user(request, db)
    hackathon = service.get_hackathon(db, hackathon_id)
    require_editor(db, user, hackathon)
    service.delete_resource(db, user, hackathon, resource_id)


@router.post("/admin/hackathons/{hackathon_id}/coordinators", response_model=HackathonAdmin)
def add_coordinator(
    hackathon_id: UUID, payload: CoordinatorIn, request: Request, db: Session = Depends(get_db)
) -> HackathonAdmin:
    check_origin(request)
    user = require_user(request, db)
    require_super_admin(user)
    hackathon = service.get_hackathon(db, hackathon_id)
    return service.to_admin(service.assign_coordinator(db, user, hackathon, payload.email))


@router.delete("/admin/hackathons/{hackathon_id}/coordinators/{user_id}", response_model=HackathonAdmin)
def remove_coordinator(hackathon_id: UUID, user_id: UUID, request: Request, db: Session = Depends(get_db)) -> HackathonAdmin:
    check_origin(request)
    user = require_user(request, db)
    require_super_admin(user)
    hackathon = service.get_hackathon(db, hackathon_id)
    return service.to_admin(service.remove_coordinator(db, user, hackathon, user_id))


@router.get("/admin/hackathons/{hackathon_id}/history", response_model=list[HistoryOut])
def hackathon_history(hackathon_id: UUID, request: Request, db: Session = Depends(get_db)) -> list[HistoryOut]:
    user = require_user(request, db)
    hackathon = service.get_hackathon(db, hackathon_id)
    require_editor(db, user, hackathon)
    return service.history(db, hackathon_id)


@router.post("/admin/users", response_model=UserOut, status_code=201)
def create_user(payload: CreateUserIn, request: Request, db: Session = Depends(get_db)) -> UserOut:
    check_origin(request)
    actor = require_user(request, db)
    require_super_admin(actor)
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        existing.name = payload.name.strip()
        existing.role = payload.role
        write_audit(db, action="user.role_updated", actor_id=actor.id, entity_type="user", entity_id=str(existing.id), metadata={"role": payload.role})
        return _user_out(existing)
    created = User(email=payload.email.lower(), name=payload.name.strip(), role=payload.role)
    db.add(created)
    db.flush()
    write_audit(db, action="user.created", actor_id=actor.id, entity_type="user", entity_id=str(created.id), metadata={"role": payload.role})
    return _user_out(created)


@router.get("/admin/activity", response_model=list[HistoryOut])
def activity(request: Request, db: Session = Depends(get_db)) -> list[HistoryOut]:
    user = require_user(request, db)
    require_staff(user)
    from app.models import HackathonHistory

    stmt = select(HackathonHistory).order_by(HackathonHistory.created_at.desc()).limit(30)
    ids = service.scoped_ids(db, user)
    if ids is not None:
        stmt = stmt.where(HackathonHistory.hackathon_id.in_(ids or [UUID(int=0)]))
    rows = db.scalars(stmt).all()
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


def _editor(hackathon_id: UUID, request: Request, db: Session):
    check_origin(request)
    user = require_user(request, db)
    hackathon = service.get_hackathon(db, hackathon_id)
    require_editor(db, user, hackathon)
    return user, hackathon


@router.post("/admin/hackathons/{hackathon_id}/tracks", response_model=TrackOut, status_code=201)
def create_track(hackathon_id: UUID, payload: TrackIn, request: Request, db: Session = Depends(get_db)) -> TrackOut:
    user, hackathon = _editor(hackathon_id, request, db)
    return content.track_out(content.add_track(db, user, hackathon, payload))


@router.put("/admin/hackathons/{hackathon_id}/tracks/{row_id}", response_model=TrackOut)
def put_track(hackathon_id: UUID, row_id: UUID, payload: TrackIn, request: Request, db: Session = Depends(get_db)) -> TrackOut:
    user, hackathon = _editor(hackathon_id, request, db)
    return content.track_out(content.update_track(db, user, hackathon, row_id, payload))


@router.delete("/admin/hackathons/{hackathon_id}/tracks/{row_id}", status_code=204)
def remove_track(hackathon_id: UUID, row_id: UUID, request: Request, db: Session = Depends(get_db)) -> None:
    user, hackathon = _editor(hackathon_id, request, db)
    content.delete_track(db, user, hackathon, row_id)


@router.post("/admin/hackathons/{hackathon_id}/deliverables", response_model=DeliverableOut, status_code=201)
def create_deliverable(
    hackathon_id: UUID, payload: DeliverableIn, request: Request, db: Session = Depends(get_db)
) -> DeliverableOut:
    user, hackathon = _editor(hackathon_id, request, db)
    return content.deliverable_out(content.add_deliverable(db, user, hackathon, payload))


@router.put("/admin/hackathons/{hackathon_id}/deliverables/{row_id}", response_model=DeliverableOut)
def put_deliverable(
    hackathon_id: UUID, row_id: UUID, payload: DeliverableIn, request: Request, db: Session = Depends(get_db)
) -> DeliverableOut:
    user, hackathon = _editor(hackathon_id, request, db)
    return content.deliverable_out(content.update_deliverable(db, user, hackathon, row_id, payload))


@router.delete("/admin/hackathons/{hackathon_id}/deliverables/{row_id}", status_code=204)
def remove_deliverable(hackathon_id: UUID, row_id: UUID, request: Request, db: Session = Depends(get_db)) -> None:
    user, hackathon = _editor(hackathon_id, request, db)
    content.delete_deliverable(db, user, hackathon, row_id)


@router.post("/admin/hackathons/{hackathon_id}/prizes", response_model=PrizeOut, status_code=201)
def create_prize(hackathon_id: UUID, payload: PrizeIn, request: Request, db: Session = Depends(get_db)) -> PrizeOut:
    user, hackathon = _editor(hackathon_id, request, db)
    return content.prize_out(content.add_prize(db, user, hackathon, payload))


@router.put("/admin/hackathons/{hackathon_id}/prizes/{row_id}", response_model=PrizeOut)
def put_prize(hackathon_id: UUID, row_id: UUID, payload: PrizeIn, request: Request, db: Session = Depends(get_db)) -> PrizeOut:
    user, hackathon = _editor(hackathon_id, request, db)
    return content.prize_out(content.update_prize(db, user, hackathon, row_id, payload))


@router.delete("/admin/hackathons/{hackathon_id}/prizes/{row_id}", status_code=204)
def remove_prize(hackathon_id: UUID, row_id: UUID, request: Request, db: Session = Depends(get_db)) -> None:
    user, hackathon = _editor(hackathon_id, request, db)
    content.delete_prize(db, user, hackathon, row_id)


@router.post("/admin/hackathons/{hackathon_id}/judging-criteria", response_model=JudgingOut, status_code=201)
def create_judging(hackathon_id: UUID, payload: JudgingIn, request: Request, db: Session = Depends(get_db)) -> JudgingOut:
    user, hackathon = _editor(hackathon_id, request, db)
    return content.judging_out(content.add_judging(db, user, hackathon, payload))


@router.put("/admin/hackathons/{hackathon_id}/judging-criteria/{row_id}", response_model=JudgingOut)
def put_judging(
    hackathon_id: UUID, row_id: UUID, payload: JudgingIn, request: Request, db: Session = Depends(get_db)
) -> JudgingOut:
    user, hackathon = _editor(hackathon_id, request, db)
    return content.judging_out(content.update_judging(db, user, hackathon, row_id, payload))


@router.delete("/admin/hackathons/{hackathon_id}/judging-criteria/{row_id}", status_code=204)
def remove_judging(hackathon_id: UUID, row_id: UUID, request: Request, db: Session = Depends(get_db)) -> None:
    user, hackathon = _editor(hackathon_id, request, db)
    content.delete_judging(db, user, hackathon, row_id)


@router.post("/admin/hackathons/{hackathon_id}/faqs", response_model=FaqOut, status_code=201)
def create_faq(hackathon_id: UUID, payload: FaqIn, request: Request, db: Session = Depends(get_db)) -> FaqOut:
    user, hackathon = _editor(hackathon_id, request, db)
    return content.faq_out(content.add_faq(db, user, hackathon, payload))


@router.put("/admin/hackathons/{hackathon_id}/faqs/{row_id}", response_model=FaqOut)
def put_faq(hackathon_id: UUID, row_id: UUID, payload: FaqIn, request: Request, db: Session = Depends(get_db)) -> FaqOut:
    user, hackathon = _editor(hackathon_id, request, db)
    return content.faq_out(content.update_faq(db, user, hackathon, row_id, payload))


@router.delete("/admin/hackathons/{hackathon_id}/faqs/{row_id}", status_code=204)
def remove_faq(hackathon_id: UUID, row_id: UUID, request: Request, db: Session = Depends(get_db)) -> None:
    user, hackathon = _editor(hackathon_id, request, db)
    content.delete_faq(db, user, hackathon, row_id)


@router.post("/admin/hackathons/{hackathon_id}/announcements", response_model=AnnouncementOut, status_code=201)
def create_announcement(
    hackathon_id: UUID, payload: AnnouncementIn, request: Request, db: Session = Depends(get_db)
) -> AnnouncementOut:
    user, hackathon = _editor(hackathon_id, request, db)
    return content.announcement_out(content.add_announcement(db, user, hackathon, payload))


@router.put("/admin/hackathons/{hackathon_id}/announcements/{row_id}", response_model=AnnouncementOut)
def put_announcement(
    hackathon_id: UUID, row_id: UUID, payload: AnnouncementIn, request: Request, db: Session = Depends(get_db)
) -> AnnouncementOut:
    user, hackathon = _editor(hackathon_id, request, db)
    return content.announcement_out(content.update_announcement(db, user, hackathon, row_id, payload))


@router.delete("/admin/hackathons/{hackathon_id}/announcements/{row_id}", status_code=204)
def remove_announcement(hackathon_id: UUID, row_id: UUID, request: Request, db: Session = Depends(get_db)) -> None:
    user, hackathon = _editor(hackathon_id, request, db)
    content.delete_announcement(db, user, hackathon, row_id)


@router.patch("/admin/hackathons/{hackathon_id}/sections", response_model=HackathonAdmin)
def patch_sections(
    hackathon_id: UUID, payload: SectionStatesIn, request: Request, db: Session = Depends(get_db)
) -> HackathonAdmin:
    user, hackathon = _editor(hackathon_id, request, db)
    return service.to_admin(content.set_section_states(db, user, hackathon, payload.states))


@router.post("/admin/hackathons/{hackathon_id}/queries/{query_id}/responses", response_model=QueryOut)
def answer_query(
    hackathon_id: UUID, query_id: UUID, payload: QueryResponseIn, request: Request, db: Session = Depends(get_db)
) -> QueryOut:
    user, hackathon = _editor(hackathon_id, request, db)
    return content.query_out(content.answer_query(db, user, hackathon, query_id, payload.body))


@router.post("/hackathons/{slug}/follow", status_code=204)
def follow_hackathon(slug: str, request: Request, db: Session = Depends(get_db)) -> None:
    check_origin(request)
    user = require_user(request, db)
    content.follow(db, user, service.get_public_by_slug(db, slug))


@router.delete("/hackathons/{slug}/follow", status_code=204)
def unfollow_hackathon(slug: str, request: Request, db: Session = Depends(get_db)) -> None:
    check_origin(request)
    user = require_user(request, db)
    hackathon = service.get_public_by_slug(db, slug)
    content.unfollow(db, user, hackathon)


@router.post("/hackathons/{slug}/bookmark", status_code=204)
def bookmark_hackathon(slug: str, request: Request, db: Session = Depends(get_db)) -> None:
    check_origin(request)
    user = require_user(request, db)
    content.bookmark(db, user, service.get_public_by_slug(db, slug))


@router.delete("/hackathons/{slug}/bookmark", status_code=204)
def unbookmark_hackathon(slug: str, request: Request, db: Session = Depends(get_db)) -> None:
    check_origin(request)
    user = require_user(request, db)
    content.unbookmark(db, user, service.get_public_by_slug(db, slug))


@router.put("/hackathons/{slug}/stance", status_code=204)
def save_stance(slug: str, payload: StanceIn, request: Request, db: Session = Depends(get_db)) -> None:
    check_origin(request)
    user = require_user(request, db)
    content.set_stance(db, user, service.get_public_by_slug(db, slug), payload.stance)


@router.delete("/hackathons/{slug}/stance", status_code=204)
def remove_stance(slug: str, request: Request, db: Session = Depends(get_db)) -> None:
    check_origin(request)
    user = require_user(request, db)
    content.clear_stance(db, user, service.get_public_by_slug(db, slug))


@router.put("/hackathons/{slug}/interest", status_code=204)
def mark_interest(slug: str, request: Request, db: Session = Depends(get_db)) -> None:
    check_origin(request)
    user = require_user(request, db)
    content.set_interest(db, user, service.get_public_by_slug(db, slug))


@router.delete("/hackathons/{slug}/interest", status_code=204)
def unmark_interest(slug: str, request: Request, db: Session = Depends(get_db)) -> None:
    check_origin(request)
    user = require_user(request, db)
    content.clear_interest(db, user, service.get_public_by_slug(db, slug))


@router.post("/hackathons/{slug}/queries", response_model=QueryOut, status_code=201)
def ask_query(slug: str, payload: QueryIn, request: Request, db: Session = Depends(get_db)) -> QueryOut:
    check_origin(request)
    user = require_user(request, db)
    return content.query_out(content.ask_query(db, user, service.get_public_by_slug(db, slug), payload.body, payload.is_public))


@router.get("/me/notification-preferences", response_model=NotificationPreferenceOut)
def notification_preferences(request: Request, db: Session = Depends(get_db)) -> NotificationPreferenceOut:
    user = require_user(request, db)
    row = notify.get_preferences(db, user)
    return NotificationPreferenceOut(in_app=row.in_app, email=row.email)


@router.put("/me/notification-preferences", response_model=NotificationPreferenceOut)
def save_notification_preferences(
    payload: NotificationPreferenceIn, request: Request, db: Session = Depends(get_db)
) -> NotificationPreferenceOut:
    check_origin(request)
    user = require_user(request, db)
    row = notify.save_preferences(db, user, in_app=payload.in_app, email=payload.email)
    return NotificationPreferenceOut(in_app=row.in_app, email=row.email)


@router.get("/notifications", response_model=list[NotificationOut])
def notifications(request: Request, db: Session = Depends(get_db)) -> list[NotificationOut]:
    user = require_user(request, db)
    return [
        NotificationOut(
            id=item.id,
            hackathon_id=item.hackathon_id,
            title=item.title,
            body=item.body,
            read_at=item.read_at,
            created_at=item.created_at,
        )
        for item in notify.list_for_user(db, user.id)
    ]


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def read_notification(notification_id: UUID, request: Request, db: Session = Depends(get_db)) -> NotificationOut:
    check_origin(request)
    user = require_user(request, db)
    item = notify.mark_read(db, user.id, notification_id)
    return NotificationOut(
        id=item.id,
        hackathon_id=item.hackathon_id,
        title=item.title,
        body=item.body,
        read_at=item.read_at,
        created_at=item.created_at,
    )


def _my_query(row) -> MyQueryOut:
    return MyQueryOut(
        id=row.id,
        hackathon_name=row.hackathon.name,
        hackathon_slug=row.hackathon.slug,
        body=row.body,
        is_public=row.is_public,
        status=row.status,
        created_at=row.created_at,
        responses=content.query_out(row).responses,
    )


def _admin_query(row) -> AdminQueryOut:
    return AdminQueryOut(
        id=row.id,
        hackathon_id=row.hackathon_id,
        hackathon_name=row.hackathon.name,
        hackathon_slug=row.hackathon.slug,
        body=row.body,
        is_public=row.is_public,
        status=row.status,
        author_name=row.author.name if row.author else None,
        assignee_id=row.assignee_id,
        assignee_name=row.assignee.name if row.assignee else None,
        created_at=row.created_at,
        responses=content.query_out(row).responses,
    )


@router.get("/me/following", response_model=list[HackathonCard])
def my_following(request: Request, db: Session = Depends(get_db)) -> list[HackathonCard]:
    return content.my_following(db, require_user(request, db))


@router.get("/me/bookmarks", response_model=list[HackathonCard])
def my_bookmarks(request: Request, db: Session = Depends(get_db)) -> list[HackathonCard]:
    return content.my_bookmarks(db, require_user(request, db))


@router.get("/me/interests", response_model=list[str])
def my_interests(request: Request, db: Session = Depends(get_db)) -> list[str]:
    user = require_user(request, db)
    return content.my_interests(db, user)


@router.get("/me/stances", response_model=list[StanceOut])
def my_stances(request: Request, db: Session = Depends(get_db)) -> list[StanceOut]:
    user = require_user(request, db)
    return [StanceOut(hackathon_slug=slug, stance=stance) for slug, stance in content.my_stances(db, user)]


@router.get("/me/queries", response_model=list[MyQueryOut])
def my_queries(request: Request, db: Session = Depends(get_db)) -> list[MyQueryOut]:
    return [_my_query(row) for row in content.my_queries(db, require_user(request, db))]


@router.get("/admin/queries", response_model=list[AdminQueryOut])
def admin_queries(request: Request, db: Session = Depends(get_db)) -> list[AdminQueryOut]:
    user = require_user(request, db)
    require_staff(user)
    return [_admin_query(row) for row in content.admin_queries(db, user)]


@router.patch("/admin/queries/{query_id}", response_model=AdminQueryOut)
def patch_query(query_id: UUID, payload: QueryPatch, request: Request, db: Session = Depends(get_db)) -> AdminQueryOut:
    check_origin(request)
    user = require_user(request, db)
    require_staff(user)
    return _admin_query(content.update_query(db, user, query_id, payload.status, payload.assignee_id))


def _extra_out(row) -> ExtraNoticeOut:
    return ExtraNoticeOut(
        id=row.id,
        hackathon_id=row.hackathon_id,
        hackathon_name=row.hackathon.name,
        title=row.title,
        body=row.body,
        created_at=row.created_at,
    )


@router.get("/admin/notifications", response_model=list[ExtraNoticeOut])
def admin_notifications(request: Request, db: Session = Depends(get_db)) -> list[ExtraNoticeOut]:
    user = require_user(request, db)
    require_staff(user)
    return [_extra_out(row) for row in notify.list_extra(db, user)]


@router.post("/admin/notifications", response_model=ExtraNoticeOut, status_code=201)
def create_notification(payload: ExtraNoticeIn, request: Request, db: Session = Depends(get_db)) -> ExtraNoticeOut:
    check_origin(request)
    user = require_user(request, db)
    require_staff(user)
    hackathon = service.get_hackathon(db, payload.hackathon_id)
    require_editor(db, user, hackathon)
    if hackathon.lifecycle not in {"published", "postponed", "completed"}:
        raise AppError(422, "not_live", "Publish the hackathon before sending an extra notification")
    notice = notify.send_extra(db, user, hackathon, payload.title, payload.body)
    notice.hackathon = hackathon
    return _extra_out(notice)


@router.get("/admin/announcements", response_model=list[AdminAnnouncementOut])
def admin_announcements(request: Request, db: Session = Depends(get_db)) -> list[AdminAnnouncementOut]:
    user = require_user(request, db)
    require_staff(user)
    return [
        AdminAnnouncementOut(
            id=row.id,
            hackathon_id=row.hackathon_id,
            hackathon_name=row.hackathon.name,
            title=row.title,
            published_at=row.published_at,
        )
        for row in content.admin_announcements(db, user)
    ]


@router.get("/admin/users", response_model=list[UserOut])
def admin_users(request: Request, db: Session = Depends(get_db)) -> list[UserOut]:
    actor = require_user(request, db)
    require_super_admin(actor)
    rows = db.scalars(select(User).order_by(User.name)).all()
    return [_user_out(row) for row in rows]


@router.post("/internal/jobs/tick")
def job_tick(request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> dict:
    secret = request.headers.get("x-job-secret", "")
    if not settings.job_tick_secret or secret != settings.job_tick_secret:
        raise AppError(401, "unauthorized", "Job tick secret is missing or incorrect")
    completed = service.complete_overdue(db)
    return {"processed": notify.tick(db, settings), "completed": completed}
