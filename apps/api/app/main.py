import logging
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import SessionLocal
from app.errors import register_error_handlers
from app.routers.api import router
from app.services import hackathons as hackathon_service
from app.services import notifications as notify

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
settings = get_settings()
log = logging.getLogger("hackhub.jobs")


def _run_jobs() -> None:
    db = SessionLocal()
    try:
        hackathon_service.complete_overdue(db)
        notify.tick(db, get_settings())
        db.commit()
    except Exception:
        db.rollback()
        log.exception("notification tick failed")
    finally:
        db.close()


def _job_loop(stop: threading.Event) -> None:
    while not stop.wait(60):
        _run_jobs()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    stop = threading.Event()
    thread = None
    if os.environ.get("HACKHUB_JOBS", "1") == "1":
        _run_jobs()
        thread = threading.Thread(target=_job_loop, args=(stop,), name="hackhub-jobs", daemon=True)
        thread.start()
    yield
    stop.set()
    if thread is not None:
        thread.join(timeout=1)


app = FastAPI(title="HackHub API", version="1.0.0", docs_url="/docs", openapi_url="/openapi.json", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)
app.include_router(router)
