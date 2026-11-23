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
    if not settings.is_production and os.environ.get("HACKHUB_JOBS", "1") == "1":
        _run_jobs()
        thread = threading.Thread(target=_job_loop, args=(stop,), name="hackhub-jobs", daemon=True)
        thread.start()
    yield
    stop.set()
    if thread is not None:
        thread.join(timeout=1)


app = FastAPI(
    title="HackHub API",
    version="1.0.0",
    docs_url=None if settings.is_production else "/docs",
    openapi_url=None if settings.is_production else "/openapi.json",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)
app.include_router(router)


@app.get("/")
def root() -> dict:
    return {"status": "ok"}

_PUBLIC_CATALOG = {"/api/v1/home", "/api/v1/categories", "/api/v1/calendar", "/api/v1/hackathons", "/api/v1/hackathons/due"}


@app.middleware("http")
async def cache_policy(request, call_next):
    response = await call_next(request)
    if request.method == "GET" and request.url.path in _PUBLIC_CATALOG:
        response.headers["Cache-Control"] = "public, s-maxage=60, stale-while-revalidate=120"
        response.headers["CDN-Cache-Control"] = "public, s-maxage=60"
        response.headers["Vercel-CDN-Cache-Control"] = "public, s-maxage=60"
        return response
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["CDN-Cache-Control"] = "no-store"
    response.headers["Vercel-CDN-Cache-Control"] = "no-store"
    return response
