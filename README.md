# HackHub

HackHub is a database-backed platform for publishing external hackathons once and showing them on the public site and calendar.

This repository currently implements the core loop:

1. An administrator signs in.
2. They create a draft, add milestones, and publish.
3. Visitors open the public page without an account.
4. Public milestones appear on the calendar.
5. Editing a milestone updates the calendar and records the previous value.

Drafts, internal notes, and internal milestones stay off the public API.

## Local setup

Postgres runs in Docker. The API and website run on your machine.

```powershell
docker compose up -d postgres
cd apps/api
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
copy ..\..\.env.example .env
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m scripts.seed
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

In another terminal:

```powershell
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000. In development, sign in at `/login` with `admin@hackhub.local`. Sample titles start with `[Sample]` and can be deleted from the admin list while they are drafts, or archived after publish.

`scripts/seed.py` refuses to run unless `APP_ENV=development`.

## Tests

```powershell
cd apps/api
.\.venv\Scripts\python -m pytest
```

The suite uses the `hackhub_test` database and checks draft privacy, coordinator scope, and milestone history.

## Documentation

- [docs/SETUP.md](docs/SETUP.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)

Interactive API docs: http://localhost:8000/docs
# external-hackathon-web
