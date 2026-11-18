"""bookmarks and query inbox fields

Revision ID: 003_portal
Revises: 002_structured_content
Create Date: 2026-11-18
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "003_portal"
down_revision = "002_structured_content"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column("queries", sa.Column("assignee_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")))
    op.add_column("queries", sa.Column("status", sa.String(16), nullable=False, server_default="open"))
    op.create_check_constraint(
        "ck_queries_status",
        "queries",
        "status in ('open','answered','closed')",
    )
    op.execute(
        """
        UPDATE queries SET status = 'answered'
        WHERE EXISTS (
          SELECT 1 FROM query_responses r WHERE r.query_id = queries.id AND r.official IS TRUE
        )
        """
    )
    op.create_table(
        "hackathon_bookmarks",
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("hackathon_id", "user_id", name="uq_hackathon_bookmarks_pair"),
    )


def downgrade() -> None:
    op.drop_table("hackathon_bookmarks")
    op.drop_constraint("ck_queries_status", "queries", type_="check")
    op.drop_column("queries", "status")
    op.drop_column("queries", "assignee_id")
