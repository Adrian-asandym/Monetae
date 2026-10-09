"""Suscripciones y plantillas recurrentes con integridad de dueño y moneda."""

from datetime import date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Numeric,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from monetae.db.base import UserScopedModel
from monetae.db.models.ledger import Transaction


class RecurringRule(UserScopedModel):
    import_external_id: Mapped[str | None] = mapped_column(Text)
    __tablename__ = "recurring_rules"
    __table_args__ = (
        Index(
            "uq_recurring_rules_user_import_external",
            "user_id",
            "import_external_id",
            unique=True,
            postgresql_where=text("import_external_id IS NOT NULL AND deleted_at IS NULL"),
        ),
        UniqueConstraint("id", "user_id", name="uq_recurring_rules_id_user_id"),
        ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["accounts.id", "accounts.user_id"],
            name="fk_recurring_rules_account_owner",
        ),
        ForeignKeyConstraint(
            ["account_id", "currency"],
            ["accounts.id", "accounts.currency"],
            name="fk_recurring_rules_account_currency",
        ),
        ForeignKeyConstraint(
            ["category_id", "user_id"],
            ["categories.id", "categories.user_id"],
            name="fk_recurring_rules_category_owner",
        ),
        ForeignKeyConstraint(
            ["subscription_id", "user_id"],
            ["subscriptions.id", "subscriptions.user_id"],
            name="fk_recurring_rules_subscription_owner",
            use_alter=True,
        ),
        CheckConstraint("fx_rate_to_base > 0", name="fx_rate"),
        CheckConstraint("kind IN ('income', 'expense')", name="kind"),
        CheckConstraint("amount <> 0 AND (kind = 'income') = (amount > 0)", name="amount"),
        CheckConstraint("currency = upper(currency) AND length(currency) = 3", name="currency"),
        CheckConstraint("period IN ('daily', 'weekly', 'monthly', 'yearly')", name="period"),
        CheckConstraint("interval_count BETWEEN 1 AND 366", name="interval_count"),
        Index("ix_recurring_rules_user_subscription", "user_id", "subscription_id"),
    )
    fx_rate_to_base: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    account_id: Mapped[UUID]
    kind: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(CHAR(3))
    category_id: Mapped[UUID | None]
    title: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    period: Mapped[str] = mapped_column(Text)
    interval_count: Mapped[int] = mapped_column(server_default=text("1"))
    anchor_on: Mapped[date]
    next_run_on: Mapped[date]
    end_on: Mapped[date | None]
    active: Mapped[bool] = mapped_column(server_default=text("true"))
    subscription_id: Mapped[UUID | None]


class Subscription(UserScopedModel):
    import_external_id: Mapped[str | None] = mapped_column(Text)
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index(
            "uq_subscriptions_user_import_external",
            "user_id",
            "import_external_id",
            unique=True,
            postgresql_where=text("import_external_id IS NOT NULL AND deleted_at IS NULL"),
        ),
        UniqueConstraint("id", "user_id", name="uq_subscriptions_id_user_id"),
        UniqueConstraint("recurring_rule_id", name="uq_subscriptions_recurring_rule"),
        ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["accounts.id", "accounts.user_id"],
            name="fk_subscriptions_account_owner",
        ),
        ForeignKeyConstraint(
            ["account_id", "currency"],
            ["accounts.id", "accounts.currency"],
            name="fk_subscriptions_account_currency",
        ),
        ForeignKeyConstraint(
            ["category_id", "user_id"],
            ["categories.id", "categories.user_id"],
            name="fk_subscriptions_category_owner",
        ),
        ForeignKeyConstraint(
            ["recurring_rule_id", "user_id"],
            ["recurring_rules.id", "recurring_rules.user_id"],
            name="fk_subscriptions_recurring_rule_owner",
        ),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("currency = upper(currency) AND length(currency) = 3", name="currency"),
        CheckConstraint("period IN ('daily', 'weekly', 'monthly', 'yearly')", name="period"),
        CheckConstraint("interval_count BETWEEN 1 AND 366", name="interval_count"),
        CheckConstraint("status IN ('active', 'archived')", name="status"),
        CheckConstraint("(status = 'archived') = (archived_at IS NOT NULL)", name="archive_state"),
        CheckConstraint(
            "archive_reason IS NULL OR length(archive_reason) <= 500", name="archive_reason"
        ),
        CheckConstraint(
            "reminder_days_before IS NULL OR reminder_days_before >= 0", name="reminder"
        ),
        Index(
            "ix_subscriptions_user_status_due",
            "user_id",
            "status",
            "next_due_on",
            "id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
    title: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(CHAR(3))
    account_id: Mapped[UUID]
    category_id: Mapped[UUID | None]
    period: Mapped[str] = mapped_column(Text)
    interval_count: Mapped[int] = mapped_column(server_default=text("1"))
    anchor_on: Mapped[date]
    next_due_on: Mapped[date]
    status: Mapped[str] = mapped_column(Text)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archive_reason: Mapped[str | None] = mapped_column(Text)
    reminder_days_before: Mapped[int | None]
    recurring_rule_id: Mapped[UUID | None]


# La columna fue creada sin FK en 0003; se registra aquí junto a su tabla destino.
cast(Table, Transaction.__table__).append_constraint(
    ForeignKeyConstraint(
        ["recurring_rule_id", "user_id"],
        ["recurring_rules.id", "recurring_rules.user_id"],
        name="fk_transactions_recurring_rule_owner",
    )
)
