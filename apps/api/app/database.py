import ssl
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings

settings = get_settings()
connect_args = {}
pool: dict = {"pool_pre_ping": True}
if settings.is_production:
    connect_args["ssl_context"] = ssl.create_default_context()
    pool = {"poolclass": NullPool}
engine = create_engine(settings.database_url, connect_args=connect_args, **pool)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
