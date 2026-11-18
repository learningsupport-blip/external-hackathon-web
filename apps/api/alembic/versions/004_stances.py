"""student registration stance

Revision ID: 004_stances
Revises: 003_portal
Create Date: 2026-11-18
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "004_stances"
down_revision = "003_portal"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "hackathon_stances",
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("stance", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("hackathon_id", "user_id", name="uq_hackathon_stances_pair"),
        sa.CheckConstraint("stance in ('registered', 'missed')", name="ck_hackathon_stances_stance"),
    )


def downgrade() -> None:
    op.drop_table("hackathon_stances")
