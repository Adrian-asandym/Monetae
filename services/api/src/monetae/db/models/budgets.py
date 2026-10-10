"""User-owned budgets and reversible category/transaction selections."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from monetae.db.base import UserScopedModel


class Budget(UserScopedModel):
    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_budgets_id_user_id"),
        CheckConstraint("period IN ('daily', 'weekly', 'monthly', 'custom')", name="period"),
        CheckConstraint("scope IN ('all', 'selected')", name="scope"),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("period <> 'custom' OR end_on IS NOT NULL", name="custom_end"),
        CheckConstraint("end_on IS NULL OR end_on >= start_on", name="dates"),
        CheckConstraint("currency = upper(currency) AND length(currency) = 3", name="currency"),
        Index(
            "ix_budgets_user_created",
            "user_id",
            "created_at",
            "id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
    name: Mapped[str] = mapped_column(Text)
    period: Mapped[str] = mapped_column(Text)
    start_on: Mapped[date]
    end_on: Mapped[date | None]
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(CHAR(3))
    scope: Mapped[str] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(Text)


class BudgetCategory(UserScopedModel):
    __tablename__ = "budget_categories"
    __table_args__ = (
        ForeignKeyConstraint(
            ["budget_id", "user_id"],
            ["budgets.id", "budgets.user_id"],
            name="fk_budget_categories_budget_owner",
        ),
        ForeignKeyConstraint(
            ["category_id", "user_id"],
            ["categories.id", "categories.user_id"],
            name="fk_budget_categories_category_owner",
        ),
        UniqueConstraint("budget_id", "category_id", name="uq_budget_categories_pair"),
        CheckConstraint("limit_amount >= 0", name="limit_nonnegative"),
        Index("ix_budget_categories_user_budget", "user_id", "budget_id"),
    )
    budget_id: Mapped[UUID]
    category_id: Mapped[UUID]
    limit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))


class BudgetTransaction(UserScopedModel):
    __tablename__ = "budget_transactions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["budget_id", "user_id"],
            ["budgets.id", "budgets.user_id"],
            name="fk_budget_transactions_budget_owner",
        ),
        ForeignKeyConstraint(
            ["transaction_id", "user_id"],
            ["transactions.id", "transactions.user_id"],
            name="fk_budget_transactions_transaction_owner",
        ),
        UniqueConstraint("budget_id", "transaction_id", name="uq_budget_transactions_pair"),
        Index("ix_budget_transactions_user_budget", "user_id", "budget_id"),
    )
    budget_id: Mapped[UUID]
    transaction_id: Mapped[UUID]
