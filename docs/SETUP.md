# Setup

## Requirements

- Docker, for Postgres
- Python 3.12
- Node.js 22 or newer

Windows may block the native PostgreSQL driver. The API uses `pg8000`, a pure-Python driver, so local development does not need that binary.

## Database

From the repository root:

```powershell
docker compose up -d postgres
```

Postgres listens on `localhost:5432` with user `hackhub`, password `hackhub`, and database `hackhub`. The first start also creates `hackhub_test` for pytest.

## API

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
copy ..\..\.env.example .env
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m scripts.seed
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The seed script creates four hackathons whose titles start with `[Sample]`. It exits immediately when `APP_ENV` is not `development`.

## Website

```powershell
cd apps/web
npm install
npm run dev
```

`apps/web/.env.local` should contain `API_URL=http://localhost:8000`. The browser calls `/api/v1` on the website origin, and Next.js forwards those requests to the API so the session cookie stays on one host.

## Sign in

Development sign-in is on `/login`. The seeded administrator is `admin@hackhub.local`.

Google sign-in needs `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI=http://localhost:3000/api/v1/auth/google/callback`.

`ADMIN_EMAILS` promotes those addresses to super admin on first sign-in. `ALLOWED_EMAIL_DOMAINS` limits new student accounts. Leave it empty to allow any Google account.

## Tests

```powershell
cd apps/api
.\.venv\Scripts\python -m pytest
```
