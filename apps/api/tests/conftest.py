import os

os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+pg8000://hackhub:hackhub@localhost:5432/hackhub_test"
)
os.environ["SESSION_SECRET"] = "test-secret"
os.environ["ADMIN_EMAILS"] = "admin@hackhub.test"
os.environ["WEB_ORIGIN"] = "http://localhost:3000"
os.environ["ALLOWED_EMAIL_DOMAINS"] = ""
os.environ["JOB_TICK_SECRET"] = "test-tick"
os.environ["HACKHUB_JOBS"] = "0"
os.environ["RESEND_API_KEY"] = ""
os.environ["RESEND_FROM"] = "HackHub <onboarding@resend.dev>"

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.config import get_settings

get_settings.cache_clear()

DATABASE_URL = os.environ["DATABASE_URL"]


def _ensure_database() -> None:
    admin_url = DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    name = DATABASE_URL.rsplit("/", 1)[1]
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}).first()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    _ensure_database()
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                TRUNCATE hackathons, users, email_verifications CASCADE
                """
            )
        )
    engine.dispose()


@pytest.fixture()
def client():
    from app.deps import _hits
    from app.main import app

    _hits.clear()
    with TestClient(app) as test_client:
        yield test_client
