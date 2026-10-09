"""Importer audit and insertion-only external identities.

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CATALOGS = ("accounts", "categories", "people", "tags", "recurring_rules", "subscriptions")


def common_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    for table in CATALOGS:
        op.add_column(table, sa.Column("import_external_id", sa.Text(), nullable=True))
        op.create_index(
            f"uq_{table}_user_import_external",
            table,
            ["user_id", "import_external_id"],
            unique=True,
            postgresql_where=sa.text("import_external_id IS NOT NULL AND deleted_at IS NULL"),
        )
    op.create_table(
        "import_runs",
        *common_columns(),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("source_schema_version", sa.Integer(), nullable=True),
        sa.Column("file_sha256", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("report", JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("id", "user_id", name="uq_import_runs_id_user_id"),
        sa.CheckConstraint("source_kind IN ('sqlite', 'csv')", name="source_kind"),
        sa.CheckConstraint("mode IN ('dry_run', 'apply')", name="mode"),
    )
    op.create_table(
        "import_review_items",
        *common_columns(),
        sa.Column("import_run_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["import_run_id", "user_id"],
            ["import_runs.id", "import_runs.user_id"],
            name="fk_import_review_items_run_owner",
        ),
    )


def downgrade() -> None:
    op.drop_table("import_review_items")
    op.drop_table("import_runs")
    for table in reversed(CATALOGS):
        op.drop_index(f"uq_{table}_user_import_external", table_name=table)
        op.drop_column(table, "import_external_id")
