"""User-owned goals and reversible transaction selections."""

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


class Goal(UserScopedModel):
    __tablename__ = "goals"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_goals_id_user_id"),
        CheckConstraint("kind IN ('spend', 'save')", name="kind"),
        CheckConstraint("target_amount > 0", name="target_amount_positive"),
        CheckConstraint("color IS NULL OR color ~ '^#[0-9A-Fa-f]{6}$'", name="color"),
        CheckConstraint("icon IS NULL OR length(icon) BETWEEN 1 AND 64", name="icon"),
        CheckConstraint("currency = upper(currency) AND length(currency) = 3", name="currency"),
        Index(
            "ix_goals_user_created",
            "user_id",
            "created_at",
            "id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
    name: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(CHAR(3))
    due_on: Mapped[date | None]
    color: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(Text)


class GoalTransaction(UserScopedModel):
    __tablename__ = "goal_transactions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["goal_id", "user_id"],
            ["goals.id", "goals.user_id"],
            name="fk_goal_transactions_goal_owner",
        ),
        ForeignKeyConstraint(
            ["transaction_id", "user_id"],
            ["transactions.id", "transactions.user_id"],
            name="fk_goal_transactions_transaction_owner",
        ),
        UniqueConstraint("goal_id", "transaction_id", name="uq_goal_transactions_pair"),
        Index("ix_goal_transactions_user_goal", "user_id", "goal_id"),
    )
    goal_id: Mapped[UUID]
    transaction_id: Mapped[UUID]
