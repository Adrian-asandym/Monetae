"""add budgets and reversible selections

Revision ID: 0009
Revises: 0008
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "budgets",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("period", sa.Text(), nullable=False),
        sa.Column("start_on", sa.Date(), nullable=False),
        sa.Column("end_on", sa.Date(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("color", sa.Text(), nullable=True),
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
            "period <> 'custom' OR end_on IS NOT NULL", name=op.f("ck_budgets_custom_end")
        ),
        sa.CheckConstraint(
            "period IN ('daily', 'weekly', 'monthly', 'custom')", name=op.f("ck_budgets_period")
        ),
        sa.CheckConstraint("scope IN ('all', 'selected')", name=op.f("ck_budgets_scope")),
        sa.CheckConstraint("amount > 0", name=op.f("ck_budgets_amount_positive")),
        sa.CheckConstraint(
            "currency = upper(currency) AND length(currency) = 3", name=op.f("ck_budgets_currency")
        ),
        sa.CheckConstraint("end_on IS NULL OR end_on >= start_on", name=op.f("ck_budgets_dates")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_budgets_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_budgets")),
        sa.UniqueConstraint("id", "user_id", name="uq_budgets_id_user_id"),
    )
    op.create_index(
        "ix_budgets_user_created",
        "budgets",
        ["user_id", "created_at", "id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "budget_categories",
        sa.Column("budget_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("limit_amount", sa.Numeric(precision=18, scale=2), nullable=False),
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
            "limit_amount >= 0", name=op.f("ck_budget_categories_limit_nonnegative")
        ),
        sa.ForeignKeyConstraint(
            ["budget_id", "user_id"],
            ["budgets.id", "budgets.user_id"],
            name="fk_budget_categories_budget_owner",
        ),
        sa.ForeignKeyConstraint(
            ["category_id", "user_id"],
            ["categories.id", "categories.user_id"],
            name="fk_budget_categories_category_owner",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_budget_categories_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_budget_categories")),
        sa.UniqueConstraint("budget_id", "category_id", name="uq_budget_categories_pair"),
    )
    op.create_index(
        "ix_budget_categories_user_budget",
        "budget_categories",
        ["user_id", "budget_id"],
        unique=False,
    )
    op.create_table(
        "budget_transactions",
        sa.Column("budget_id", sa.Uuid(), nullable=False),
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
            ["budget_id", "user_id"],
            ["budgets.id", "budgets.user_id"],
            name="fk_budget_transactions_budget_owner",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id", "user_id"],
            ["transactions.id", "transactions.user_id"],
            name="fk_budget_transactions_transaction_owner",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_budget_transactions_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_budget_transactions")),
        sa.UniqueConstraint("budget_id", "transaction_id", name="uq_budget_transactions_pair"),
    )
    op.create_index(
        "ix_budget_transactions_user_budget",
        "budget_transactions",
        ["user_id", "budget_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_budget_transactions_user_budget", table_name="budget_transactions")
    op.drop_table("budget_transactions")
    op.drop_index("ix_budget_categories_user_budget", table_name="budget_categories")
    op.drop_table("budget_categories")
    op.drop_index(
        "ix_budgets_user_created",
        table_name="budgets",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_table("budgets")
