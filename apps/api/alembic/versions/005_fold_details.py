"""fold event details and query replies into JSON columns

Revision ID: 005_fold_details
Revises: 004_stances
Create Date: 2026-11-19
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "005_fold_details"
down_revision = "004_stances"
branch_labels = None
depends_on = None

UUID = sa.dialects.postgresql.UUID(as_uuid=True)

_LISTS = (
    (
        "tracks",
        """jsonb_build_object(
            'id', row.id, 'hackathon_id', row.hackathon_id, 'name', row.name,
            'requirements', row.requirements, 'position', row.position
        )""",
    ),
    (
        "deliverables",
        """jsonb_build_object(
            'id', row.id, 'hackathon_id', row.hackathon_id, 'title', row.title,
            'detail', row.detail, 'required', row.required, 'position', row.position
        )""",
    ),
    (
        "prizes",
        """jsonb_build_object(
            'id', row.id, 'hackathon_id', row.hackathon_id, 'label', row.label,
            'detail', row.detail, 'position', row.position
        )""",
    ),
    (
        "judging_criteria",
        """jsonb_build_object(
            'id', row.id, 'hackathon_id', row.hackathon_id, 'title', row.title,
            'detail', row.detail, 'weight', row.weight, 'position', row.position
        )""",
    ),
    (
        "faqs",
        """jsonb_build_object(
            'id', row.id, 'hackathon_id', row.hackathon_id, 'question', row.question,
            'answer', row.answer, 'position', row.position
        )""",
    ),
    (
        "resources",
        """jsonb_build_object(
            'id', row.id, 'hackathon_id', row.hackathon_id, 'title', row.title,
            'url', row.url, 'kind', row.kind, 'position', row.position
        )""",
    ),
    (
        "announcements",
        """jsonb_build_object(
            'id', row.id, 'hackathon_id', row.hackathon_id, 'title', row.title,
            'body', row.body, 'published_at', row.published_at, 'position', row.position
        )""",
    ),
)


def upgrade() -> None:
    op.add_column("hackathons", sa.Column("internal", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column(
        "hackathons", sa.Column("section_states", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))
    )
    for name, _expr in _LISTS:
        op.add_column("hackathons", sa.Column(name, JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("queries", sa.Column("responses", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")))

    op.execute(
        """
        UPDATE hackathons AS h
        SET internal = jsonb_build_object(
            'internal_notes', i.internal_notes,
            'tracking_status', i.tracking_status,
            'administrative_comments', i.administrative_comments,
            'verification_status', i.verification_status,
            'last_verified_at', i.last_verified_at,
            'source_urls', i.source_urls
        )
        FROM hackathon_internal AS i
        WHERE i.hackathon_id = h.id
        """
    )
    op.execute(
        """
        UPDATE hackathons AS h
        SET section_states = COALESCE(
            (SELECT jsonb_object_agg(s.section, s.state) FROM section_states AS s WHERE s.hackathon_id = h.id),
            '{}'::jsonb
        )
        """
    )
    for name, expr in _LISTS:
        op.execute(
            f"""
            UPDATE hackathons AS h
            SET {name} = COALESCE(
                (SELECT jsonb_agg({expr} ORDER BY row.position) FROM {name} AS row WHERE row.hackathon_id = h.id),
                '[]'::jsonb
            )
            """
        )
    op.execute(
        """
        UPDATE queries AS q
        SET responses = COALESCE(
            (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'id', r.id,
                        'author_id', r.author_id,
                        'body', r.body,
                        'official', r.official,
                        'created_at', r.created_at
                    )
                    ORDER BY r.created_at
                )
                FROM query_responses AS r
                WHERE r.query_id = q.id
            ),
            '[]'::jsonb
        )
        """
    )

    op.drop_table("query_responses")
    op.drop_table("section_states")
    op.drop_table("hackathon_internal")
    for name, _expr in reversed(_LISTS):
        op.drop_table(name)


def downgrade() -> None:
    _recreate_children()
    op.execute(
        """
        INSERT INTO hackathon_internal (
            hackathon_id, internal_notes, tracking_status, administrative_comments,
            verification_status, last_verified_at, source_urls, updated_at
        )
        SELECT
            id,
            internal->>'internal_notes',
            internal->>'tracking_status',
            internal->>'administrative_comments',
            COALESCE(internal->>'verification_status', 'unverified'),
            NULLIF(internal->>'last_verified_at', '')::timestamptz,
            internal->>'source_urls',
            now()
        FROM hackathons
        """
    )
    op.execute(
        """
        INSERT INTO section_states (hackathon_id, section, state)
        SELECT h.id, entry.key, entry.value
        FROM hackathons AS h
        CROSS JOIN LATERAL jsonb_each_text(h.section_states) AS entry
        """
    )
    _insert_back(
        "tracks",
        "id, hackathon_id, position, name, requirements",
        "(item->>'id')::uuid, h.id, COALESCE((item->>'position')::int, 0), item->>'name', item->>'requirements'",
    )
    _insert_back(
        "deliverables",
        "id, hackathon_id, position, title, detail, required",
        "(item->>'id')::uuid, h.id, COALESCE((item->>'position')::int, 0), item->>'title', item->>'detail', COALESCE((item->>'required')::boolean, true)",
    )
    _insert_back(
        "prizes",
        "id, hackathon_id, position, label, detail",
        "(item->>'id')::uuid, h.id, COALESCE((item->>'position')::int, 0), item->>'label', item->>'detail'",
    )
    _insert_back(
        "judging_criteria",
        "id, hackathon_id, position, title, detail, weight",
        "(item->>'id')::uuid, h.id, COALESCE((item->>'position')::int, 0), item->>'title', item->>'detail', NULLIF(item->>'weight', '')::int",
    )
    _insert_back(
        "faqs",
        "id, hackathon_id, position, question, answer",
        "(item->>'id')::uuid, h.id, COALESCE((item->>'position')::int, 0), item->>'question', item->>'answer'",
    )
    _insert_back(
        "resources",
        "id, hackathon_id, position, title, url, kind",
        "(item->>'id')::uuid, h.id, COALESCE((item->>'position')::int, 0), item->>'title', item->>'url', COALESCE(item->>'kind', 'other')",
    )
    _insert_back(
        "announcements",
        "id, hackathon_id, position, title, body, published_at",
        "(item->>'id')::uuid, h.id, COALESCE((item->>'position')::int, 0), item->>'title', item->>'body', NULLIF(item->>'published_at', '')::timestamptz",
    )
    op.execute(
        """
        INSERT INTO query_responses (id, query_id, author_id, body, official, created_at)
        SELECT
            (item->>'id')::uuid,
            q.id,
            NULLIF(item->>'author_id', '')::uuid,
            item->>'body',
            COALESCE((item->>'official')::boolean, true),
            COALESCE(NULLIF(item->>'created_at', '')::timestamptz, now())
        FROM queries AS q
        CROSS JOIN LATERAL jsonb_array_elements(q.responses) AS item
        """
    )
    op.drop_column("queries", "responses")
    for name, _expr in _LISTS:
        op.drop_column("hackathons", name)
    op.drop_column("hackathons", "section_states")
    op.drop_column("hackathons", "internal")


def _insert_back(table: str, columns: str, select: str) -> None:
    op.execute(
        f"""
        INSERT INTO {table} ({columns})
        SELECT {select}
        FROM hackathons AS h
        CROSS JOIN LATERAL jsonb_array_elements(h.{table}) AS item
        """
    )


def _recreate_children() -> None:
    op.create_table(
        "hackathon_internal",
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("internal_notes", sa.Text()),
        sa.Column("tracking_status", sa.String(80)),
        sa.Column("administrative_comments", sa.Text()),
        sa.Column("verification_status", sa.String(32), nullable=False, server_default="unverified"),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.Column("source_urls", sa.Text()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "tracks",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("requirements", sa.Text()),
    )
    op.create_table(
        "deliverables",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("detail", sa.Text()),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "prizes",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("detail", sa.Text()),
    )
    op.create_table(
        "judging_criteria",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("detail", sa.Text()),
        sa.Column("weight", sa.Integer()),
        sa.CheckConstraint("weight IS NULL OR (weight >= 0 AND weight <= 100)", name="ck_judging_weight"),
    )
    op.create_table(
        "faqs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("question", sa.String(300), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
    )
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
    op.create_table(
        "announcements",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("hackathon_id", UUID, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
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
    op.create_table(
        "query_responses",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("query_id", UUID, sa.ForeignKey("queries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("official", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
