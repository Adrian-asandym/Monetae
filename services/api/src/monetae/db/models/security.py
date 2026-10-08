"""Registro de seguridad: excepción explícita a user_id y borrado lógico."""

from datetime import datetime

from sqlalchemy import DateTime, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from monetae.db.base import Base


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    __table_args__ = (
        Index("ix_login_attempts_email_lower_attempted_at", "email_lower", "attempted_at"),
        Index("ix_login_attempts_ip_attempted_at", "ip", "attempted_at"),
        Index("ix_login_attempts_attempted_at", "attempted_at"),
    )

    email_lower: Mapped[str] = mapped_column(Text)
    ip: Mapped[str] = mapped_column(Text)
    succeeded: Mapped[bool]
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
