"""slice A: users, hackathons, milestones, history

Revision ID: 001_slice_a
Revises:
Create Date: 2026-11-18
"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "001_slice_a"
down_revision = None
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
CATEGORIES = (
    ("AI/ML", "ai-ml"),
    ("Web Development", "web-development"),
    ("Open Source", "open-source"),
    ("Cloud Computing", "cloud-computing"),
    ("Cybersecurity", "cybersecurity"),
    ("Sustainability", "sustainability"),
    ("Social Impact", "social-impact"),
    ("Robotics", "robotics"),
    ("Product Development", "product-development"),
    ("Other", "other"),
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("avatar_url", sa.String(1000)),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("google_sub", sa.String(255), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "sessions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])
    op.create_table(
        "categories",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
    )
    op.create_table(
        "tags",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.UniqueConstraint("slug", "kind", name="uq_tags_slug_kind"),
    )
    op.create_table(
        "hackathons",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("slug", sa.String(140), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("organiser", sa.String(200), nullable=False),
        sa.Column("organiser_logo_url", sa.String(1000)),
        sa.Column("short_description", sa.String(400)),
        sa.Column("description", sa.Text()),
        sa.Column("problem_statements", sa.Text()),
        sa.Column("official_website", sa.String(1000)),
        sa.Column("banner_url", sa.String(1000)),
        sa.Column("difficulty", sa.String(32)),
        sa.Column("participation_type", sa.String(32)),
        sa.Column("min_team_size", sa.Integer()),
        sa.Column("max_team_size", sa.Integer()),
        sa.Column("eligibility", sa.Text()),
        sa.Column("academic_year", sa.String(120)),
        sa.Column("degree_requirements", sa.Text()),
        sa.Column("geographic_restrictions", sa.Text()),
        sa.Column("other_eligibility", sa.Text()),
        sa.Column("mode", sa.String(32)),
        sa.Column("venue", sa.String(300)),
        sa.Column("location", sa.String(300)),
        sa.Column("event_duration", sa.String(120)),
        sa.Column("registration_url", sa.String(1000)),
        sa.Column("registration_opens_at", sa.DateTime(timezone=True)),
        sa.Column("registration_closes_at", sa.DateTime(timezone=True)),
        sa.Column("registration_instructions", sa.Text()),
        sa.Column("submission_url", sa.String(1000)),
        sa.Column("submission_deadline", sa.DateTime(timezone=True)),
        sa.Column("required_deliverables", sa.Text()),
        sa.Column("submission_instructions", sa.Text()),
        sa.Column("prize_pool", sa.String(200)),
        sa.Column("first_prize", sa.String(200)),
        sa.Column("second_prize", sa.String(200)),
        sa.Column("third_prize", sa.String(200)),
        sa.Column("special_awards", sa.Text()),
        sa.Column("certificates", sa.Text()),
        sa.Column("internships", sa.Text()),
        sa.Column("other_rewards", sa.Text()),
        sa.Column("lifecycle", sa.String(32), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "lifecycle in ('draft','published','postponed','cancelled','archived','completed')",
            name="ck_hackathons_lifecycle",
        ),
    )
    op.create_index("ix_hackathons_lifecycle", "hackathons", ["lifecycle"])
    op.create_index("ix_hackathons_registration_closes_at", "hackathons", ["registration_closes_at"])
    op.create_index("ix_hackathons_submission_deadline", "hackathons", ["submission_deadline"])
    op.create_index("ix_hackathons_published_at", "hackathons", ["published_at"])
    op.execute(
        """
        ALTER TABLE hackathons ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(organiser, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(short_description, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(description, '')), 'C')
        ) STORED
        """
    )
    op.execute("CREATE INDEX ix_hackathons_search ON hackathons USING GIN (search_vector)")
    op.execute("CREATE INDEX ix_hackathons_name_trgm ON hackathons USING GIN (name gin_trgm_ops)")
    op.execute("CREATE INDEX ix_hackathons_organiser_trgm ON hackathons USING GIN (organiser gin_trgm_ops)")
    op.create_table(
        "hackathon_internal",
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("internal_notes", sa.Text()),
        sa.Column("tracking_status", sa.String(80)),
        sa.Column("administrative_comments", sa.Text()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "hackathon_categories",
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("category_id", UUID, sa.ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "hackathon_tags",
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", UUID, sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "hackathon_admins",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("hackathon_id", "user_id", name="uq_hackathon_admins_pair"),
    )
    op.create_index("ix_hackathon_admins_hackathon_id", "hackathon_admins", ["hackathon_id"])
    op.create_index("ix_hackathon_admins_user_id", "hackathon_admins", ["user_id"])
    op.create_table(
        "milestones",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True)),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.Column("visibility", sa.String(16), nullable=False),
        sa.Column("reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_milestones_hackathon_id", "milestones", ["hackathon_id"])
    op.create_index("ix_milestones_starts_at", "milestones", ["starts_at"])
    op.create_table(
        "resources",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resources_hackathon_id", "resources", ["hackathon_id"])
    op.create_table(
        "hackathon_history",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", UUID),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("previous", postgresql.JSONB),
        sa.Column("new", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_hackathon_history_hackathon_id", "hackathon_history", ["hackathon_id"])
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("actor_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(40)),
        sa.Column("entity_id", sa.String(80)),
        sa.Column("metadata", postgresql.JSONB),
        sa.Column("ip", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    categories = sa.table("categories", sa.column("id", UUID), sa.column("name", sa.String), sa.column("slug", sa.String))
    op.bulk_insert(
        categories,
        [{"id": uuid.uuid4(), "name": name, "slug": slug} for name, slug in CATEGORIES],
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("hackathon_history")
    op.drop_table("resources")
    op.drop_table("milestones")
    op.drop_table("hackathon_admins")
    op.drop_table("hackathon_tags")
    op.drop_table("hackathon_categories")
    op.drop_table("hackathon_internal")
    op.drop_table("hackathons")
    op.drop_table("tags")
    op.drop_table("categories")
    op.drop_table("sessions")
    op.drop_table("users")
