"""Libro mayor con referencias compuestas que preservan dueño y moneda."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    LargeBinary,
    Numeric,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from monetae.db.base import Base, UserScopedModel

# La expresión debe coincidir literalmente con el índice de PostgreSQL.
SEARCH_VECTOR = (
    "to_tsvector('spanish'::regconfig, (title || ' '::text) || COALESCE(note, ''::text))"
)


class Transaction(UserScopedModel):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_transactions_id_user_id"),
        ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["accounts.id", "accounts.user_id"],
            name="fk_transactions_account_owner",
        ),
        ForeignKeyConstraint(
            ["account_id", "currency"],
            ["accounts.id", "accounts.currency"],
            name="fk_transactions_account_currency",
        ),
        ForeignKeyConstraint(
            ["category_id", "user_id"],
            ["categories.id", "categories.user_id"],
            name="fk_transactions_category_owner",
        ),
        CheckConstraint(
            "(kind = 'transfer') = (transfer_group_id IS NOT NULL)", name="transfer_group"
        ),
        Index(
            "uq_transactions_transfer_outgoing",
            "transfer_group_id",
            unique=True,
            postgresql_where=text("kind = 'transfer' AND amount < 0 AND deleted_at IS NULL"),
        ),
        Index(
            "uq_transactions_transfer_incoming",
            "transfer_group_id",
            unique=True,
            postgresql_where=text("kind = 'transfer' AND amount > 0 AND deleted_at IS NULL"),
        ),
        CheckConstraint("amount <> 0", name="amount_nonzero"),
        CheckConstraint("fx_rate_to_base > 0", name="fx_rate_positive"),
        CheckConstraint("currency = upper(currency)", name="currency_upper"),
        CheckConstraint("length(currency) = 3", name="currency_length"),
        CheckConstraint("kind IN ('income', 'expense', 'transfer', 'loan')", name="kind"),
        CheckConstraint("status IN ('posted', 'scheduled')", name="status"),
        CheckConstraint("fx_rate_source IN ('manual', 'auto')", name="fx_rate_source"),
        CheckConstraint("source IN ('web', 'import', 'telegram', 'api')", name="source"),
        CheckConstraint(
            "categorization_source IN ('manual', 'rule', 'model', 'llm')",
            name="categorization_source",
        ),
        Index(
            "ix_transactions_user_occurred",
            "user_id",
            text("occurred_at DESC"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_transactions_user_account_occurred",
            "user_id",
            "account_id",
            text("occurred_at DESC"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_transactions_user_category_occurred",
            "user_id",
            "category_id",
            "occurred_at",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_transactions_user_status_occurred",
            "user_id",
            "status",
            "occurred_at",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_transactions_search",
            text(SEARCH_VECTOR),
            postgresql_using="gin",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_transactions_user_import_external",
            "user_id",
            "import_external_id",
            unique=True,
            postgresql_where=text("import_external_id IS NOT NULL AND deleted_at IS NULL"),
        ),
    )

    account_id: Mapped[UUID]
    currency: Mapped[str] = mapped_column(CHAR(3))
    kind: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    category_id: Mapped[UUID | None]
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    fx_rate_to_base: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    fx_rate_source: Mapped[str] = mapped_column(Text)
    transfer_group_id: Mapped[UUID | None]
    # Sin FK: recurring_rules llega en una fase posterior.
    recurring_rule_id: Mapped[UUID | None]
    source: Mapped[str] = mapped_column(Text)
    raw_input: Mapped[str | None] = mapped_column(Text)
    categorization_source: Mapped[str | None] = mapped_column(Text)
    is_initial_data: Mapped[bool] = mapped_column(server_default=text("false"))
    import_external_id: Mapped[str | None] = mapped_column(Text)


class TransactionTag(UserScopedModel):
    __tablename__ = "transaction_tags"
    __table_args__ = (
        ForeignKeyConstraint(
            ["transaction_id", "user_id"],
            ["transactions.id", "transactions.user_id"],
            name="fk_transaction_tags_transaction_owner",
        ),
        ForeignKeyConstraint(
            ["tag_id", "user_id"],
            ["tags.id", "tags.user_id"],
            name="fk_transaction_tags_tag_owner",
        ),
        Index(
            "uq_transaction_tags_active",
            "transaction_id",
            "tag_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_transaction_tags_user_tag", "user_id", "tag_id"),
    )
    transaction_id: Mapped[UUID]
    tag_id: Mapped[UUID]


class IdempotencyKey(Base):
    """Registro técnico: no es una entidad financiera con borrado lógico."""

    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_idempotency_keys_user_key"),)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    key: Mapped[str] = mapped_column(Text)
    request_hash: Mapped[bytes] = mapped_column(LargeBinary)
    response_status: Mapped[int]
    # JSONB es un borde JSON validado por el response_model antes de persistirlo.
    response_body: Mapped[dict[str, object]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
