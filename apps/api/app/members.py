"""One membership row per person per hackathon."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models import HackathonMember


def get_member(db: Session, hackathon_id: UUID, user_id: UUID) -> HackathonMember | None:
    return db.get(HackathonMember, (hackathon_id, user_id))


def ensure_member(db: Session, hackathon_id: UUID, user_id: UUID) -> HackathonMember:
    row = get_member(db, hackathon_id, user_id)
    if row is None:
        row = HackathonMember(hackathon_id=hackathon_id, user_id=user_id, is_admin=False)
        db.add(row)
    return row


def prune_member(db: Session, row: HackathonMember | None) -> None:
    if row is None:
        return
    if row.is_admin or row.followed_at is not None or row.bookmarked_at is not None or row.stance or row.interested_at is not None:
        return
    db.delete(row)
