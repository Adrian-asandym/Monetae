"""Catálogos de usuario; los saldos de cuentas se calculan desde transacciones."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from monetae.db.base import UserScopedModel


class Account(UserScopedModel):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_accounts_id_user_id"),
        CheckConstraint("type IN ('cash', 'bank', 'wallet', 'card', 'other')", name="type"),
        CheckConstraint("currency = upper(currency)", name="currency_upper"),
        CheckConstraint("length(currency) = 3", name="currency_length"),
        UniqueConstraint("id", "currency", name="uq_accounts_id_currency"),
        Index(
            "uq_accounts_user_id_name",
            "user_id",
            func.lower(text("name")),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    name: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(CHAR(3))
    initial_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), server_default=text("0"))
    color: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(server_default=text("0"))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Category(UserScopedModel):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_categories_id_user_id"),
        CheckConstraint("kind IN ('income', 'expense')", name="kind"),
        CheckConstraint("system_key IN ('interest_income', 'interest_expense')", name="system_key"),
        CheckConstraint("is_system = (system_key IS NOT NULL)", name="is_system"),
        Index(
            "uq_categories_user_id_system_key",
            "user_id",
            "system_key",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND system_key IS NOT NULL"),
        ),
    )

    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("categories.id"))
    kind: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(server_default=text("false"))
    system_key: Mapped[str | None] = mapped_column(Text)


class Person(UserScopedModel):
    __tablename__ = "people"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_people_id_user_id"),
        Index("ix_people_aliases", "aliases", postgresql_using="gin"),
        Index("ix_people_name", func.lower(text("name"))),
    )

    name: Mapped[str] = mapped_column(Text)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    note: Mapped[str | None] = mapped_column(Text)


class Tag(UserScopedModel):
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_tags_id_user_id"),
        Index(
            "uq_tags_user_id_name",
            "user_id",
            func.lower(text("name")),
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND archived_at IS NULL"),
        ),
    )

    name: Mapped[str] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(Text)
    emoji: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(server_default=text("0"))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
