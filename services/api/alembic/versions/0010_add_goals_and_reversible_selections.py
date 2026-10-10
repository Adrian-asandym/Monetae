"""add goals and reversible selections

Revision ID: 0010
Revises: 0009
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("target_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("color", sa.Text(), nullable=True),
        sa.Column("icon", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "color IS NULL OR color ~ '^#[0-9A-Fa-f]{6}$'", name=op.f("ck_goals_color")
        ),
        sa.CheckConstraint("kind IN ('spend', 'save')", name=op.f("ck_goals_kind")),
        sa.CheckConstraint(
            "currency = upper(currency) AND length(currency) = 3", name=op.f("ck_goals_currency")
        ),
        sa.CheckConstraint(
            "icon IS NULL OR length(icon) BETWEEN 1 AND 64", name=op.f("ck_goals_icon")
        ),
        sa.CheckConstraint("target_amount > 0", name=op.f("ck_goals_target_amount_positive")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_goals_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_goals")),
        sa.UniqueConstraint("id", "user_id", name="uq_goals_id_user_id"),
    )
    op.create_index(
        "ix_goals_user_created",
        "goals",
        ["user_id", "created_at", "id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "goal_transactions",
        sa.Column("goal_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["goal_id", "user_id"],
            ["goals.id", "goals.user_id"],
            name="fk_goal_transactions_goal_owner",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id", "user_id"],
            ["transactions.id", "transactions.user_id"],
            name="fk_goal_transactions_transaction_owner",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_goal_transactions_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_goal_transactions")),
        sa.UniqueConstraint("goal_id", "transaction_id", name="uq_goal_transactions_pair"),
    )
    op.create_index(
        "ix_goal_transactions_user_goal", "goal_transactions", ["user_id", "goal_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_goal_transactions_user_goal", table_name="goal_transactions")
    op.drop_table("goal_transactions")
    op.drop_index(
        "ix_goals_user_created", table_name="goals", postgresql_where=sa.text("deleted_at IS NULL")
    )
    op.drop_table("goals")
