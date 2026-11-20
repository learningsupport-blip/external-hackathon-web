"""Align the published ODSC hackathon with the official page. Run once inside the API."""

from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.catalog import category_id
from app.database import SessionLocal
from app.models import User
from app.schemas import (
    DeliverableIn,
    FaqIn,
    HackathonUpdate,
    JudgingIn,
    LabelIn,
    MilestoneIn,
    PrizeIn,
    ResourceIn,
    SectionStateIn,
    TrackIn,
)
from app.services import content
from app.services.hackathons import add_milestone, add_resource, delete_milestone, get_hackathon, update_hackathon

HACKATHON_ID = UUID("67508eac-4ceb-4e22-a0ce-339014c014e7")
ZONE = ZoneInfo("America/New_York")


def at(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=ZONE)


def main() -> None:
    db = SessionLocal()
    try:
        actor = db.scalar(select(User).where(User.email == "admin@hackhub.local"))
        if actor is None:
            raise SystemExit("Admin user admin@hackhub.local was not found")
        hackathon = get_hackathon(db, HACKATHON_ID)
        update_hackathon(
            db,
            actor,
            hackathon,
            HackathonUpdate(
                timezone="America/New_York",
                mode="hybrid",
                participation_type="both",
                difficulty=None,
                min_team_size=1,
                category_ids=[category_id("ai-ml")],
                registration_instructions=(
                    "Register free through the official hackathon website. "
                    "Registration takes about two minutes and there is no acceptance review. Solo or teams may participate."
                ),
                labels=[
                    LabelIn(name="Research agents", kind="theme"),
                    LabelIn(name="Sourced answers", kind="theme"),
                    LabelIn(name="Open models", kind="theme"),
                    LabelIn(name="Nebius Token Factory", kind="technology"),
                    LabelIn(name="Tavily", kind="technology"),
                    LabelIn(name="AI", kind="tag"),
                    LabelIn(name="Agents", kind="tag"),
                    LabelIn(name="Research", kind="tag"),
                ],
            ),
        )
        hackathon = get_hackathon(db, HACKATHON_ID)
        for milestone in list(hackathon.milestones):
            delete_milestone(db, actor, hackathon, milestone.id)
        hackathon = get_hackathon(db, HACKATHON_ID)
        add_milestone(
            db,
            actor,
            hackathon,
            MilestoneIn(
                title="Kickoff at ODSC AI West, San Francisco",
                description="Meet the Nebius team, get set up, and form a team in person. Streamed online. Exact kickoff times are shared with registered participants.",
                type="workshop",
                starts_at=at(2026, 10, 28, 0, 0),
                visibility="public",
                position=0,
            ),
        )
        add_milestone(
            db,
            actor,
            hackathon,
            MilestoneIn(
                title="Build with live support",
                description="Hack on your research agent at your own pace, with Nebius engineers available online.",
                type="other",
                starts_at=at(2026, 10, 28, 0, 0),
                ends_at=at(2026, 11, 20, 23, 59),
                visibility="public",
                position=1,
            ),
        )
        add_milestone(
            db,
            actor,
            hackathon,
            MilestoneIn(
                title="Submissions close",
                description="Submissions close Friday, November 20, 2026 at 11:59 PM EST. There is no live demo day. Judging follows the deadline.",
                type="final_submission",
                ends_at=at(2026, 11, 20, 23, 59),
                visibility="public",
                position=2,
            ),
        )
        hackathon = get_hackathon(db, HACKATHON_ID)
        track = hackathon.tracks[0]
        content.update_track(
            db,
            actor,
            hackathon,
            UUID(str(track["id"])),
            TrackIn(
                name="Single Nebius challenge: build a research agent that brings its sources",
                requirements=(
                    "Inference on Nebius Token Factory. Real-time web search with Tavily. "
                    "A public repo with a README. A demo video (2–3 minutes suggested)."
                ),
            ),
        )
        for row in list(hackathon.deliverables):
            content.delete_deliverable(db, actor, hackathon, UUID(str(row["id"])))
        for row in list(hackathon.prizes):
            content.delete_prize(db, actor, hackathon, UUID(str(row["id"])))
        for row in list(hackathon.judging_criteria):
            content.delete_judging(db, actor, hackathon, UUID(str(row["id"])))
        content.add_deliverable(
            db,
            actor,
            hackathon,
            DeliverableIn(title="Public GitHub repository with README and setup instructions", detail="Judges need to reproduce the core experience.", required=True, position=0),
        )
        content.add_deliverable(
            db,
            actor,
            hackathon,
            DeliverableIn(title="Demo video, 2–3 minutes suggested", detail="Show a question, the sourced answer, and a failure or insufficient-evidence case.", required=True, position=1),
        )
        content.add_deliverable(
            db,
            actor,
            hackathon,
            DeliverableIn(title="Live app or write-up", detail="Optional.", required=False, position=2),
        )
        content.add_prize(db, actor, hackathon, PrizeIn(label="Nebius challenge winner", detail="$2,000 Token Factory credits", position=0))
        content.add_prize(db, actor, hackathon, PrizeIn(label="Runner-up", detail="$1,000 Token Factory credits", position=1))
        content.add_prize(db, actor, hackathon, PrizeIn(label="Third place", detail="$500 Token Factory credits", position=2))
        criteria = (
            (30, "Sourced and verifiable answers", "Answers are grounded in credible evidence, with citations a reader can check."),
            (25, "Works end to end", "A working path from a question through search and inference to a sourced answer."),
            (20, "Usefulness", "The agent solves a clear research need and makes the result easier to verify."),
            (15, "Agent design", "Thoughtful research orchestration, not complexity for its own sake."),
            (10, "Use of Token Factory and Tavily", "Token Factory drives inference and Tavily retrieves live web evidence."),
        )
        for position, (weight, title, detail) in enumerate(criteria):
            content.add_judging(db, actor, hackathon, JudgingIn(title=title, detail=detail, weight=weight, position=position))
        content.add_faq(
            db,
            actor,
            hackathon,
            FaqIn(question="Is there a demo day?", answer="No. There is no live demo day. Judging follows the deadline, and winners are announced soon after. A short live Q&A for finalists may be arranged if the judging process allows it, and that Q&A is optional.", position=0),
        )
        content.add_faq(
            db,
            actor,
            hackathon,
            FaqIn(question="Who can take part?", answer="The hackathon is open to everyone. Come solo and find teammates, or bring your own team.", position=1),
        )
        content.add_faq(
            db,
            actor,
            hackathon,
            FaqIn(question="Is registration free?", answer="Registration is free, takes about two minutes, and there is no acceptance review.", position=2),
        )
        content.add_faq(
            db,
            actor,
            hackathon,
            FaqIn(question="When do submissions close?", answer="Submissions close on Friday, November 20, 2026 at 11:59 PM EST.", position=3),
        )
        add_resource(db, actor, hackathon, ResourceIn(title="Official website", url="https://hackathon.odsc.ai/", kind="guidelines", position=0))
        add_resource(db, actor, hackathon, ResourceIn(title="Submission page", url="https://hackathon.odsc.ai/submit", kind="other", position=1))
        content.set_section_states(
            db,
            actor,
            hackathon,
            [
                SectionStateIn(section=section, state="confirmed")
                for section in ("eligibility", "participation", "themes", "submission", "prizes", "judging", "preparation", "dates")
            ],
        )
        db.commit()
        print("corrected", HACKATHON_ID)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
