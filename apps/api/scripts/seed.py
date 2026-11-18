"""Development-only sample hackathons. Refuses to run outside APP_ENV=development."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.errors import AppError
from app.models import Category, User
from app.schemas import HackathonCreate, HackathonUpdate, LabelIn, MilestoneIn
from app.services import hackathons as service


def _at(days: int, hour: int = 18) -> datetime:
    moment = datetime.now(UTC) + timedelta(days=days)
    return moment.replace(hour=hour, minute=0, second=0, microsecond=0)


def main() -> None:
    settings = get_settings()
    if settings.app_env != "development":
        raise SystemExit("Seed refused: APP_ENV must be development")
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.email == "admin@hackhub.local"))
        if admin is None:
            admin = User(email="admin@hackhub.local", name="HackHub Admin", role="super_admin")
            db.add(admin)
            db.flush()
        categories = {row.slug: row.id for row in db.scalars(select(Category)).all()}
        samples = [
            {
                "create": HackathonCreate(name="[Sample] Northwind AI Challenge", organiser="Sample AI Guild", short_description="Online sample for machine-learning teams. Not a real event."),
                "update": HackathonUpdate(
                    description="Sample online hackathon used to demonstrate HackHub. Do not treat this as a verified external opportunity.",
                    mode="online",
                    difficulty="intermediate",
                    participation_type="team",
                    min_team_size=2,
                    max_team_size=4,
                    eligibility="Sample rule: open to enrolled students.",
                    academic_year="Any",
                    registration_url="https://example.com/sample-ai",
                    official_website="https://example.com/sample-ai",
                    registration_opens_at=_at(-2),
                    registration_closes_at=_at(12),
                    submission_deadline=_at(20),
                    prize_pool="Sample credits",
                    category_ids=[categories["ai-ml"]],
                    labels=[LabelIn(name="Python", kind="technology"), LabelIn(name="Health", kind="theme")],
                    featured=True,
                    timezone="Asia/Kolkata",
                ),
                "milestones": [
                    ("Registration closes", "registration_closes", 12),
                    ("Final submission", "final_submission", 20),
                ],
            },
            {
                "create": HackathonCreate(name="[Sample] River City Sustainability Jam", organiser="Sample Civic Lab", short_description="Hybrid sample with an on-site finale."),
                "update": HackathonUpdate(
                    description="Sample hybrid sustainability event. Dates and prizes are fictional.",
                    mode="hybrid",
                    difficulty="beginner",
                    participation_type="both",
                    location="Sample campus hall",
                    venue="Block C atrium",
                    registration_url="https://example.com/sample-sustainability",
                    registration_opens_at=_at(5),
                    registration_closes_at=_at(18),
                    category_ids=[categories["sustainability"]],
                    labels=[LabelIn(name="Climate", kind="theme")],
                    timezone="Asia/Kolkata",
                ),
                "milestones": [
                    ("Registration opens", "registration_opens", 5),
                    ("Grand finale", "grand_finale", 25),
                ],
            },
            {
                "create": HackathonCreate(name="[Sample] Offline Open Source Weekend", organiser="Sample Maintainers", short_description="In-person sample for contributors."),
                "update": HackathonUpdate(
                    description="Sample offline open-source weekend. Not an official programme.",
                    mode="offline",
                    difficulty="advanced",
                    participation_type="individual",
                    location="Sample city library",
                    registration_url="https://example.com/sample-oss",
                    registration_opens_at=_at(-10),
                    registration_closes_at=_at(-1),
                    category_ids=[categories["open-source"]],
                    labels=[LabelIn(name="Git", kind="technology")],
                    timezone="Asia/Kolkata",
                ),
                "milestones": [("Results", "results", 2)],
            },
            {
                "create": HackathonCreate(name="[Sample] Product Studio Build", organiser="Sample Product Club", short_description="Team sample focused on shipping a product demo."),
                "update": HackathonUpdate(
                    description="Sample team product hackathon with a prototype checkpoint.",
                    mode="online",
                    difficulty="beginner",
                    participation_type="team",
                    min_team_size=3,
                    max_team_size=5,
                    eligibility="Sample: first and second year students.",
                    academic_year="1st and 2nd year",
                    registration_url="https://example.com/sample-product",
                    registration_opens_at=_at(-1),
                    registration_closes_at=_at(8),
                    submission_deadline=_at(15),
                    category_ids=[categories["product-development"]],
                    labels=[LabelIn(name="Prototype", kind="tag")],
                    timezone="Asia/Kolkata",
                ),
                "milestones": [
                    ("Prototype submission", "prototype_submission", 11),
                    ("Final submission", "final_submission", 15),
                ],
            },
        ]
        for sample in samples:
            existing = db.scalar(select(service.Hackathon).where(service.Hackathon.name == sample["create"].name))
            if existing:
                continue
            hackathon = service.create_hackathon(db, settings, admin, sample["create"])
            service.update_hackathon(db, admin, hackathon, sample["update"])
            hackathon = service.get_hackathon(db, hackathon.id)
            for title, kind, day in sample["milestones"]:
                service.add_milestone(
                    db,
                    admin,
                    hackathon,
                    MilestoneIn(title=title, type=kind, starts_at=_at(day), visibility="public"),
                )
            hackathon = service.get_hackathon(db, hackathon.id)
            service.change_lifecycle(db, admin, hackathon, "published", None)
        db.commit()
        print("Sample hackathons are ready. Titles start with [Sample].")
    except AppError as exc:
        db.rollback()
        raise SystemExit(exc.message) from exc
    finally:
        db.close()


if __name__ == "__main__":
    main()
