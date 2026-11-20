"""store extra notifications sent from the admin menu

Revision ID: 009_extra_notifications
Revises: 008_interest
Create Date: 2026-11-20
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "009_extra_notifications"
down_revision = "008_interest"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "extra_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("hackathon_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_extra_notifications_hackathon_id", "extra_notifications", ["hackathon_id"])
    op.add_column(
        "notification_jobs",
        sa.Column("notice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("extra_notifications.id", ondelete="SET NULL")),
    )


def downgrade() -> None:
    op.drop_column("notification_jobs", "notice_id")
    op.drop_index("ix_extra_notifications_hackathon_id", table_name="extra_notifications")
    op.drop_table("extra_notifications")
