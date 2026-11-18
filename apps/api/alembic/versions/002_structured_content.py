"""structured sections, queries, and notification jobs

Revision ID: 002_structured_content
Revises: 001_slice_a
Create Date: 2026-11-18
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "002_structured_content"
down_revision = "001_slice_a"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)

SECTION_SQL = {
    "eligibility": (
        "eligibility IS NOT NULL OR academic_year IS NOT NULL OR degree_requirements IS NOT NULL "
        "OR geographic_restrictions IS NOT NULL OR other_eligibility IS NOT NULL "
        "OR min_team_size IS NOT NULL OR max_team_size IS NOT NULL"
    ),
    "participation": (
        "participation_type IS NOT NULL OR mode IS NOT NULL OR venue IS NOT NULL "
        "OR location IS NOT NULL OR event_duration IS NOT NULL"
    ),
    "themes": (
        "problem_statements IS NOT NULL OR EXISTS "
        "(SELECT 1 FROM hackathon_tags ht WHERE ht.hackathon_id = hackathons.id)"
    ),
    "submission": (
        "required_deliverables IS NOT NULL OR submission_instructions IS NOT NULL "
        "OR submission_url IS NOT NULL OR submission_deadline IS NOT NULL"
    ),
    "prizes": (
        "prize_pool IS NOT NULL OR first_prize IS NOT NULL OR second_prize IS NOT NULL "
        "OR third_prize IS NOT NULL OR special_awards IS NOT NULL OR certificates IS NOT NULL "
        "OR internships IS NOT NULL OR other_rewards IS NOT NULL"
    ),
    "judging": "FALSE",
    "preparation": "preparation_guidelines IS NOT NULL",
    "dates": (
        "registration_opens_at IS NOT NULL OR registration_closes_at IS NOT NULL "
        "OR submission_deadline IS NOT NULL OR EXISTS "
        "(SELECT 1 FROM milestones m WHERE m.hackathon_id = hackathons.id "
        "AND (m.starts_at IS NOT NULL OR m.ends_at IS NOT NULL))"
    ),
}


def _child(name: str, *columns: sa.Column) -> None:
    op.create_table(
        name,
        sa.Column("id", UUID, primary_key=True),
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        *columns,
    )
    op.create_index(f"ix_{name}_hackathon_id", name, ["hackathon_id"])


def upgrade() -> None:
    op.add_column("hackathons", sa.Column("preparation_guidelines", sa.Text()))
    op.add_column(
        "hackathon_internal",
        sa.Column("verification_status", sa.String(32), nullable=False, server_default="unverified"),
    )
    op.add_column("hackathon_internal", sa.Column("last_verified_at", sa.DateTime(timezone=True)))
    op.add_column("hackathon_internal", sa.Column("source_urls", sa.Text()))

    _child("tracks", sa.Column("name", sa.String(200), nullable=False), sa.Column("requirements", sa.Text()))
    _child(
        "deliverables",
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("detail", sa.Text()),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    _child("prizes", sa.Column("label", sa.String(200), nullable=False), sa.Column("detail", sa.Text()))
    _child(
        "judging_criteria",
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("detail", sa.Text()),
        sa.Column("weight", sa.Integer()),
        sa.CheckConstraint("weight IS NULL OR (weight >= 0 AND weight <= 100)", name="ck_judging_weight"),
    )
    _child(
        "faqs",
        sa.Column("question", sa.String(300), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
    )
    _child(
        "announcements",
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "section_states",
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("section", sa.String(32), primary_key=True),
        sa.Column("state", sa.String(32), nullable=False),
        sa.CheckConstraint(
            "section in ('eligibility','participation','themes','submission','prizes','judging','preparation','dates')",
            name="ck_section_states_section",
        ),
        sa.CheckConstraint(
            "state in ('confirmed','not_announced','not_specified','awaiting_confirmation','not_applicable')",
            name="ck_section_states_state",
        ),
    )
    for section, predicate in SECTION_SQL.items():
        op.execute(
            sa.text(
                "INSERT INTO section_states (hackathon_id, section, state) "
                f"SELECT id, :section, CASE WHEN {predicate} THEN 'confirmed' ELSE 'not_specified' END FROM hackathons"
            ).bindparams(section=section)
        )
    op.create_table(
        "queries",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_queries_hackathon_id", "queries", ["hackathon_id"])
    op.create_table(
        "query_responses",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("query_id", UUID, sa.ForeignKey("queries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("official", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_query_responses_query_id", "query_responses", ["query_id"])
    op.create_table(
        "hackathon_followers",
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("hackathon_id", "user_id", name="uq_hackathon_followers_pair"),
    )
    op.create_table(
        "notification_preferences",
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("in_app", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("email", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "notification_jobs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("milestone_id", UUID),
        sa.Column("announcement_id", UUID),
        sa.Column("offset_days", sa.Integer()),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_notification_jobs_key"),
        sa.CheckConstraint("status in ('pending','cancelled','done')", name="ck_notification_jobs_status"),
    )
    op.create_index("ix_notification_jobs_user_id", "notification_jobs", ["user_id"])
    op.create_index("ix_notification_jobs_hackathon_id", "notification_jobs", ["hackathon_id"])
    op.create_index("ix_notification_jobs_run_at", "notification_jobs", ["run_at"])
    op.create_table(
        "notifications",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE")),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_table(
        "notification_deliveries",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("job_id", UUID, sa.ForeignKey("notification_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("detail", sa.String(300)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_notification_deliveries_job_id", "notification_deliveries", ["job_id"])


def downgrade() -> None:
    for name in (
        "notification_deliveries",
        "notifications",
        "notification_jobs",
        "notification_preferences",
        "hackathon_followers",
        "query_responses",
        "queries",
        "section_states",
        "announcements",
        "faqs",
        "judging_criteria",
        "prizes",
        "deliverables",
        "tracks",
    ):
        op.drop_table(name)
    op.drop_column("hackathon_internal", "source_urls")
    op.drop_column("hackathon_internal", "last_verified_at")
    op.drop_column("hackathon_internal", "verification_status")
    op.drop_column("hackathons", "preparation_guidelines")
