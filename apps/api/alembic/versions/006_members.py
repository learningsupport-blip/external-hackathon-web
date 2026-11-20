"""store categories, tags, and person links on fewer tables

Revision ID: 006_members
Revises: 005_fold_details
Create Date: 2026-11-19
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "006_members"
down_revision = "005_fold_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("hackathons", sa.Column("categories", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("hackathons", sa.Column("labels", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.execute(
        """
        UPDATE hackathons AS h
        SET categories = COALESCE(
            (
                SELECT jsonb_agg(
                    jsonb_build_object('id', c.id, 'name', c.name, 'slug', c.slug)
                    ORDER BY c.name
                )
                FROM hackathon_categories AS link
                JOIN categories AS c ON c.id = link.category_id
                WHERE link.hackathon_id = h.id
            ),
            '[]'::jsonb
        )
        """
    )
    op.execute(
        """
        UPDATE hackathons AS h
        SET labels = COALESCE(
            (
                SELECT jsonb_agg(
                    jsonb_build_object('id', t.id, 'name', t.name, 'slug', t.slug, 'kind', t.kind)
                    ORDER BY t.name
                )
                FROM hackathon_tags AS link
                JOIN tags AS t ON t.id = link.tag_id
                WHERE link.hackathon_id = h.id
            ),
            '[]'::jsonb
        )
        """
    )
    op.create_table(
        "hackathon_members",
        sa.Column("hackathon_id", UUID(as_uuid=True), sa.ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("followed_at", sa.DateTime(timezone=True)),
        sa.Column("bookmarked_at", sa.DateTime(timezone=True)),
        sa.Column("stance", sa.String(16)),
        sa.CheckConstraint(
            "stance IS NULL OR stance IN ('registered', 'missed')",
            name="ck_hackathon_members_stance",
        ),
        sa.CheckConstraint(
            "is_admin OR followed_at IS NOT NULL OR bookmarked_at IS NOT NULL OR stance IS NOT NULL",
            name="ck_hackathon_members_active",
        ),
    )
    op.create_index("ix_hackathon_members_user_id", "hackathon_members", ["user_id"])
    op.execute(
        """
        INSERT INTO hackathon_members (hackathon_id, user_id, is_admin, followed_at, bookmarked_at, stance)
        SELECT
            hackathon_id,
            user_id,
            bool_or(is_admin),
            max(followed_at),
            max(bookmarked_at),
            max(stance)
        FROM (
            SELECT hackathon_id, user_id, true AS is_admin,
                   NULL::timestamptz AS followed_at, NULL::timestamptz AS bookmarked_at, NULL::text AS stance
            FROM hackathon_admins
            UNION ALL
            SELECT hackathon_id, user_id, false, created_at, NULL, NULL FROM hackathon_followers
            UNION ALL
            SELECT hackathon_id, user_id, false, NULL, created_at, NULL FROM hackathon_bookmarks
            UNION ALL
            SELECT hackathon_id, user_id, false, NULL, NULL, stance FROM hackathon_stances
        ) AS links
        GROUP BY hackathon_id, user_id
        """
    )
    op.drop_table("hackathon_categories")
    op.drop_table("hackathon_tags")
    op.drop_table("categories")
    op.drop_table("tags")
    op.drop_table("hackathon_admins")
    op.drop_table("hackathon_followers")
    op.drop_table("hackathon_bookmarks")
    op.drop_table("hackathon_stances")


def downgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
    )
    op.create_table(
        "tags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.UniqueConstraint("slug", "kind", name="uq_tags_slug_kind"),
    )
    op.create_table(
        "hackathon_categories",
        sa.Column("hackathon_id", UUID(as_uuid=True), sa.ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "hackathon_tags",
        sa.Column("hackathon_id", UUID(as_uuid=True), sa.ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", UUID(as_uuid=True), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )
    op.execute(
        """
        INSERT INTO categories (id, name, slug)
        SELECT DISTINCT ON (item->>'slug')
            (item->>'id')::uuid, item->>'name', item->>'slug'
        FROM hackathons AS h
        CROSS JOIN LATERAL jsonb_array_elements(h.categories) AS item
        """
    )
    op.execute(
        """
        INSERT INTO hackathon_categories (hackathon_id, category_id)
        SELECT h.id, (item->>'id')::uuid
        FROM hackathons AS h
        CROSS JOIN LATERAL jsonb_array_elements(h.categories) AS item
        """
    )
    op.execute(
        """
        INSERT INTO tags (id, name, slug, kind)
        SELECT DISTINCT ON (item->>'slug', item->>'kind')
            (item->>'id')::uuid, item->>'name', item->>'slug', item->>'kind'
        FROM hackathons AS h
        CROSS JOIN LATERAL jsonb_array_elements(h.labels) AS item
        """
    )
    op.execute(
        """
        INSERT INTO hackathon_tags (hackathon_id, tag_id)
        SELECT h.id, (item->>'id')::uuid
        FROM hackathons AS h
        CROSS JOIN LATERAL jsonb_array_elements(h.labels) AS item
        """
    )
    op.create_table(
        "hackathon_admins",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hackathon_id", UUID(as_uuid=True), sa.ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("hackathon_id", "user_id", name="uq_hackathon_admins_pair"),
    )
    op.create_table(
        "hackathon_followers",
        sa.Column("hackathon_id", UUID(as_uuid=True), sa.ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "hackathon_bookmarks",
        sa.Column("hackathon_id", UUID(as_uuid=True), sa.ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "hackathon_stances",
        sa.Column("hackathon_id", UUID(as_uuid=True), sa.ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("stance", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("stance in ('registered', 'missed')", name="ck_hackathon_stances_stance"),
    )
    op.execute(
        """
        INSERT INTO hackathon_admins (hackathon_id, user_id)
        SELECT hackathon_id, user_id FROM hackathon_members WHERE is_admin
        """
    )
    op.execute(
        """
        INSERT INTO hackathon_followers (hackathon_id, user_id, created_at)
        SELECT hackathon_id, user_id, followed_at FROM hackathon_members WHERE followed_at IS NOT NULL
        """
    )
    op.execute(
        """
        INSERT INTO hackathon_bookmarks (hackathon_id, user_id, created_at)
        SELECT hackathon_id, user_id, bookmarked_at FROM hackathon_members WHERE bookmarked_at IS NOT NULL
        """
    )
    op.execute(
        """
        INSERT INTO hackathon_stances (hackathon_id, user_id, stance)
        SELECT hackathon_id, user_id, stance FROM hackathon_members WHERE stance IS NOT NULL
        """
    )
    op.drop_index("ix_hackathon_members_user_id", table_name="hackathon_members")
    op.drop_table("hackathon_members")
    op.drop_column("hackathons", "labels")
    op.drop_column("hackathons", "categories")
