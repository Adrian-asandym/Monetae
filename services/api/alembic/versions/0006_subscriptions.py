"""subscriptions

Revision ID: 0006
Revises: 0005

El downgrade pierde suscripciones y reglas por diseño. Desvincula todas las
transacciones sin borrarlas ni cambiar sus importes; las scheduled sobreviven
como programadas normales y el siguiente upgrade no deja referencias huérfanas.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recurring_rules",
        sa.Column("fx_rate_to_base", sa.Numeric(18, 6), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("period", sa.Text(), nullable=False),
        sa.Column("interval_count", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("anchor_on", sa.Date(), nullable=False),
        sa.Column("next_run_on", sa.Date(), nullable=False),
        sa.Column("end_on", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("subscription_id", sa.Uuid(), nullable=True),
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
        sa.CheckConstraint("fx_rate_to_base > 0", name=op.f("ck_recurring_rules_fx_rate")),
        sa.CheckConstraint(
            "amount <> 0 AND (kind = 'income') = (amount > 0)",
            name=op.f("ck_recurring_rules_amount"),
        ),
        sa.CheckConstraint("kind IN ('income', 'expense')", name=op.f("ck_recurring_rules_kind")),
        sa.CheckConstraint(
            "period IN ('daily', 'weekly', 'monthly', 'yearly')",
            name=op.f("ck_recurring_rules_period"),
        ),
        sa.CheckConstraint(
            "currency = upper(currency) AND length(currency) = 3",
            name=op.f("ck_recurring_rules_currency"),
        ),
        sa.CheckConstraint(
            "interval_count BETWEEN 1 AND 366", name=op.f("ck_recurring_rules_interval_count")
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "currency"],
            ["accounts.id", "accounts.currency"],
            name="fk_recurring_rules_account_currency",
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["accounts.id", "accounts.user_id"],
            name="fk_recurring_rules_account_owner",
        ),
        sa.ForeignKeyConstraint(
            ["category_id", "user_id"],
            ["categories.id", "categories.user_id"],
            name="fk_recurring_rules_category_owner",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_recurring_rules_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recurring_rules")),
        sa.UniqueConstraint("id", "user_id", name="uq_recurring_rules_id_user_id"),
    )
    op.create_index(
        "ix_recurring_rules_user_subscription",
        "recurring_rules",
        ["user_id", "subscription_id"],
        unique=False,
    )
    op.create_table(
        "subscriptions",
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("period", sa.Text(), nullable=False),
        sa.Column("interval_count", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("anchor_on", sa.Date(), nullable=False),
        sa.Column("next_due_on", sa.Date(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archive_reason", sa.Text(), nullable=True),
        sa.Column("reminder_days_before", sa.Integer(), nullable=True),
        sa.Column("recurring_rule_id", sa.Uuid(), nullable=True),
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
            "(status = 'archived') = (archived_at IS NOT NULL)",
            name=op.f("ck_subscriptions_archive_state"),
        ),
        sa.CheckConstraint(
            "period IN ('daily', 'weekly', 'monthly', 'yearly')",
            name=op.f("ck_subscriptions_period"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived')", name=op.f("ck_subscriptions_status")
        ),
        sa.CheckConstraint("amount > 0", name=op.f("ck_subscriptions_amount_positive")),
        sa.CheckConstraint(
            "archive_reason IS NULL OR length(archive_reason) <= 500",
            name=op.f("ck_subscriptions_archive_reason"),
        ),
        sa.CheckConstraint(
            "currency = upper(currency) AND length(currency) = 3",
            name=op.f("ck_subscriptions_currency"),
        ),
        sa.CheckConstraint(
            "interval_count BETWEEN 1 AND 366", name=op.f("ck_subscriptions_interval_count")
        ),
        sa.CheckConstraint(
            "reminder_days_before IS NULL OR reminder_days_before >= 0",
            name=op.f("ck_subscriptions_reminder"),
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "currency"],
            ["accounts.id", "accounts.currency"],
            name="fk_subscriptions_account_currency",
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["accounts.id", "accounts.user_id"],
            name="fk_subscriptions_account_owner",
        ),
        sa.ForeignKeyConstraint(
            ["category_id", "user_id"],
            ["categories.id", "categories.user_id"],
            name="fk_subscriptions_category_owner",
        ),
        sa.ForeignKeyConstraint(
            ["recurring_rule_id", "user_id"],
            ["recurring_rules.id", "recurring_rules.user_id"],
            name="fk_subscriptions_recurring_rule_owner",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_subscriptions_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subscriptions")),
        sa.UniqueConstraint("id", "user_id", name="uq_subscriptions_id_user_id"),
        sa.UniqueConstraint("recurring_rule_id", name="uq_subscriptions_recurring_rule"),
    )
    op.create_index(
        "ix_subscriptions_user_status_due",
        "subscriptions",
        ["user_id", "status", "next_due_on", "id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_foreign_key(
        "fk_recurring_rules_subscription_owner",
        "recurring_rules",
        "subscriptions",
        ["subscription_id", "user_id"],
        ["id", "user_id"],
    )
    op.execute(
        "ALTER TABLE transactions ADD CONSTRAINT fk_transactions_recurring_rule_owner "
        "FOREIGN KEY (recurring_rule_id, user_id) REFERENCES recurring_rules (id, user_id) "
        "NOT VALID"
    )
    op.execute("ALTER TABLE transactions VALIDATE CONSTRAINT fk_transactions_recurring_rule_owner")


def downgrade() -> None:
    op.execute(
        "UPDATE transactions SET recurring_rule_id = NULL WHERE recurring_rule_id IS NOT NULL"
    )
    op.drop_constraint("fk_transactions_recurring_rule_owner", "transactions", type_="foreignkey")
    op.drop_index(
        "ix_subscriptions_user_status_due",
        table_name="subscriptions",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_constraint(
        "fk_recurring_rules_subscription_owner", "recurring_rules", type_="foreignkey"
    )
    op.drop_table("subscriptions")
    op.drop_index("ix_recurring_rules_user_subscription", table_name="recurring_rules")
    op.drop_table("recurring_rules")
