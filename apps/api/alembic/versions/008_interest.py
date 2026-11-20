"""remember who is interested in a hackathon

Revision ID: 008_interest
Revises: 007_accounts
Create Date: 2026-11-20
"""

import sqlalchemy as sa
from alembic import op

revision = "008_interest"
down_revision = "007_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("hackathon_members", sa.Column("interested_at", sa.DateTime(timezone=True)))
    op.drop_constraint("ck_hackathon_members_active", "hackathon_members", type_="check")
    op.create_check_constraint(
        "ck_hackathon_members_active",
        "hackathon_members",
        "is_admin OR followed_at IS NOT NULL OR bookmarked_at IS NOT NULL OR stance IS NOT NULL OR interested_at IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_hackathon_members_active", "hackathon_members", type_="check")
    op.create_check_constraint(
        "ck_hackathon_members_active",
        "hackathon_members",
        "is_admin OR followed_at IS NOT NULL OR bookmarked_at IS NOT NULL OR stance IS NOT NULL",
    )
    op.drop_column("hackathon_members", "interested_at")
