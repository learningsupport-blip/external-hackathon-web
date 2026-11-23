"""Development administrator. Refuses to run outside APP_ENV=development."""

from sqlalchemy import delete, select

from app.config import get_settings
from app.database import SessionLocal
from app.models import Hackathon, User


def main() -> None:
    settings = get_settings()
    if settings.app_env != "development":
        raise SystemExit("Seed refused: APP_ENV must be development")
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.email == "admin@hackhub.local"))
        if admin is None:
            db.add(User(email="admin@hackhub.local", name="HackHub Admin", role="super_admin"))
        removed = db.execute(delete(Hackathon).where(Hackathon.name.startswith("[Sample]")))
        db.commit()
        print(f"Development admin is ready. Removed {removed.rowcount} sample hackathons.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
