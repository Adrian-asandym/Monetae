"""Persistencia del libro de préstamos; saldo y estado se calculan por SQL."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from monetae.db.base import UserScopedModel


class Loan(UserScopedModel):
    __tablename__ = "loans"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_loans_id_user_id"),
        ForeignKeyConstraint(
            ["person_id", "user_id"], ["people.id", "people.user_id"], name="fk_loans_person_owner"
        ),
        CheckConstraint("direction IN ('lent', 'borrowed')", name="direction"),
        CheckConstraint("principal > 0", name="principal_positive"),
        CheckConstraint("currency = upper(currency) AND length(currency) = 3", name="currency"),
        Index(
            "uq_loans_user_import_external",
            "user_id",
            "import_external_id",
            unique=True,
            postgresql_where=text("import_external_id IS NOT NULL AND deleted_at IS NULL"),
        ),
    )
    person_id: Mapped[UUID]
    direction: Mapped[str] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(CHAR(3))
    principal: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    opened_on: Mapped[date]
    due_on: Mapped[date | None]
    note: Mapped[str | None] = mapped_column(Text)
    import_external_id: Mapped[str | None] = mapped_column(Text)


class LoanMovement(UserScopedModel):
    __tablename__ = "loan_movements"
    __table_args__ = (
        ForeignKeyConstraint(
            ["loan_id", "user_id"],
            ["loans.id", "loans.user_id"],
            name="fk_loan_movements_loan_owner",
        ),
        ForeignKeyConstraint(
            ["transaction_id", "user_id"],
            ["transactions.id", "transactions.user_id"],
            name="fk_loan_movements_transaction_owner",
        ),
        UniqueConstraint("transaction_id", name="uq_loan_movements_transaction"),
        UniqueConstraint("loan_id", "sequence", name="uq_loan_movements_sequence"),
        CheckConstraint("sequence >= 0", name="sequence"),
        CheckConstraint(
            "kind IN ('disbursement', 'interest', 'payment', 'adjustment', 'write_off')",
            name="kind",
        ),
        CheckConstraint(
            (
                "(kind = 'adjustment' AND amount_in_loan_currency <> 0) OR (kind <> "
                "'adjustment' AND amount_in_loan_currency > 0)"
            ),
            name="amount",
        ),
        CheckConstraint(
            (
                "(kind IN ('payment', 'write_off') AND interest_part IS NOT NULL AND "
                "principal_part IS NOT NULL AND interest_part >= 0 AND principal_part >= "
                "0 AND interest_part + principal_part = amount_in_loan_currency) OR (kind"
                " NOT IN ('payment', 'write_off') AND interest_part IS NULL AND "
                "principal_part IS NULL)"
            ),
            name="split",
        ),
        CheckConstraint(
            "kind IN ('disbursement', 'payment') OR "
            "(transaction_id IS NULL AND fx_rate_applied IS NULL)",
            name="cash",
        ),
        CheckConstraint(
            "fx_rate_applied IS NULL OR (transaction_id IS NOT NULL AND fx_rate_applied > 0)",
            name="fx_rate",
        ),
        Index(
            "ix_loan_movements_user_loan_occurred", "user_id", "loan_id", "occurred_at", "sequence"
        ),
        Index(
            "uq_loan_movements_disbursement",
            "loan_id",
            unique=True,
            postgresql_where=text("kind = 'disbursement' AND deleted_at IS NULL"),
        ),
    )
    loan_id: Mapped[UUID]
    kind: Mapped[str] = mapped_column(Text)
    amount_in_loan_currency: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    transaction_id: Mapped[UUID | None]
    interest_part: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    principal_part: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    fx_rate_applied: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)
    sequence: Mapped[int] = mapped_column(BigInteger)
