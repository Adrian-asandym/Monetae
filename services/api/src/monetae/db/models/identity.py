"""Identidad y sesiones opacas; el token en claro nunca se persiste."""

from datetime import datetime

from sqlalchemy import CHAR, CheckConstraint, DateTime, Index, LargeBinary, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from monetae.db.base import Base, SoftDeleteMixin, TimestampMixin, UserScopedModel


class User(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("base_currency = upper(base_currency)", name="base_currency_upper"),
        CheckConstraint("length(base_currency) = 3", name="base_currency_length"),
        CheckConstraint("report_currency = upper(report_currency)", name="report_currency_upper"),
        CheckConstraint("length(report_currency) = 3", name="report_currency_length"),
        CheckConstraint("locale IN ('es', 'en')", name="locale"),
        Index(
            "uq_users_email",
            func.lower(text("email")),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_users_google_sub",
            "google_sub",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND google_sub IS NOT NULL"),
        ),
    )

    email: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str | None] = mapped_column(Text)
    google_sub: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(Text, server_default=text("'America/Lima'"))
    base_currency: Mapped[str] = mapped_column(CHAR(3), server_default=text("'PEN'"))
    locale: Mapped[str] = mapped_column(Text, server_default=text("'es'"))
    pin_hash: Mapped[str | None] = mapped_column(Text)
    pin_failed_attempts: Mapped[int] = mapped_column(server_default=text("0"))
    lock_after_minutes: Mapped[int | None]
    # El servicio de registro copia base_currency; no hay default fijo en la BD.
    report_currency: Mapped[str] = mapped_column(CHAR(3))
    preferences: Mapped[dict[str, object]] = mapped_column(JSONB, server_default=text("'{}'"))


class Session(UserScopedModel):
    __tablename__ = "sessions"
    __table_args__ = (
        Index(
            "uq_sessions_token_hash",
            "token_hash",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_sessions_user_id_revoked_at", "user_id", "revoked_at"),
    )

    token_hash: Mapped[bytes] = mapped_column(LargeBinary)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(Text)
    ip: Mapped[str | None] = mapped_column(Text)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
