# Architecture

HackHub is a modular monolith. The browser talks only to the Next.js app. Next.js rewrites `/api/v1/*` to FastAPI. FastAPI owns the database, permissions, and session cookie.

```text
Browser -> Next.js (apps/web) -> FastAPI (apps/api) -> PostgreSQL
```

Business rules live in `apps/api/app/services`. Routers validate input and call services. The public and admin responses are separate models. Internal notes live in `hackathon_internal`, and the public repository never joins that table into a public response.

Registration status is calculated from the lifecycle and the registration timestamps. It is not stored, so the badge cannot drift away from the dates.

The calendar is a query over `milestones`. A row appears when the hackathon is published, postponed, or completed, the milestone is public, and its time overlaps the requested range. Drafts, archived hackathons, cancelled hackathons, and internal milestones are excluded.

Changing a milestone writes the previous and new values to `hackathon_history` and increments `milestones.version`. That version is the hook for later reminder jobs. Reminder delivery is not part of this slice. When it is added, jobs will be rows in Postgres, drained by a scheduled call, rather than an always-on worker.

Sessions are rows in `sessions`. The cookie stores a random token. The database stores only its SHA-256 hash.

Coordinators can edit a hackathon only when `hackathon_admins` links them to it. Super admins can edit every hackathon. Those checks run in the API.

Hosting for a first deploy is Cloud Run at scale-to-zero plus Neon Postgres. Supabase Pro is a later option if Auth and file storage should share one invoice. Cloud SQL and Memorystore are not required for this version.
