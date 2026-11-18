# Database schema

Slice A is the schema in `apps/api/alembic/versions/001_slice_a.py`. Primary keys are UUIDs. Timestamps are `timestamptz`.

```text
users 1---* sessions
users 1---* hackathon_admins *---1 hackathons
users 1---* hackathons (created_by)
hackathons 1---1 hackathon_internal
hackathons *---* categories
hackathons *---* tags
hackathons 1---* milestones
hackathons 1---* resources
hackathons 1---* hackathon_history
users 1---* audit_logs
```

`hackathons.lifecycle` is one of draft, published, postponed, cancelled, archived, completed.

`hackathons.search_vector` is a generated `tsvector` over the name, organiser, and descriptions, with a trigram index on the name and organiser for short searches.

`milestones.visibility` is `public` or `internal`. `milestones.version` starts at 1 and increases when the title, dates, or visibility change.

`hackathon_internal` holds coordinator notes. It is a separate table so a public query cannot select those columns by accident.

`tags.kind` is `tag`, `theme`, or `technology`. The unique key is `(slug, kind)`.

Categories are seeded by the migration: AI/ML, Web Development, Open Source, Cloud Computing, Cybersecurity, Sustainability, Social Impact, Robotics, Product Development, and Other.

Later slices add followers, bookmarks, announcements, queries, and notification jobs. They are not tables yet.
