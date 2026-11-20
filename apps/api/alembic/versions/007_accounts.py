"""student accounts with verified email

Revision ID: 007_accounts
Revises: 006_members
Create Date: 2026-11-19
"""

import sqlalchemy as sa
from alembic import op

revision = "007_accounts"
down_revision = "006_members"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("first_name", sa.String(80)))
    op.add_column("users", sa.Column("last_name", sa.String(80)))
    op.add_column("users", sa.Column("phone_country", sa.String(8)))
    op.add_column("users", sa.Column("phone", sa.String(20)))
    op.add_column("users", sa.Column("university", sa.String(200)))
    op.add_column("users", sa.Column("batch", sa.String(40)))
    op.add_column("users", sa.Column("niat_id", sa.String(16)))
    op.add_column("users", sa.Column("password_hash", sa.String(200)))
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True)))
    op.create_unique_constraint("uq_users_niat_id", "users", ["niat_id"])
    op.create_unique_constraint("uq_users_phone", "users", ["phone_country", "phone"])
    op.create_table(
        "email_verifications",
        sa.Column("email", sa.String(320), primary_key=True),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verified_token_hash", sa.String(64)),
        sa.Column("token_expires_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("email_verifications")
    op.drop_constraint("uq_users_phone", "users", type_="unique")
    op.drop_constraint("uq_users_niat_id", "users", type_="unique")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "niat_id")
    op.drop_column("users", "batch")
    op.drop_column("users", "university")
    op.drop_column("users", "phone")
    op.drop_column("users", "phone_country")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
