"""Global historical market rates; report endpoints only read this table."""

from datetime import date
from decimal import Decimal

from sqlalchemy import CHAR, CheckConstraint, Index, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from monetae.db.base import Base, TimestampMixin


class ExchangeRate(TimestampMixin, Base):
    # Architecture §5.8: global system data, without user_id or soft deletion.
    __tablename__ = "exchange_rates"
    __table_args__ = (
        CheckConstraint("rate > 0", name="rate_positive"),
        CheckConstraint("from_currency <> to_currency", name="different_currencies"),
        CheckConstraint("source = 'manual' OR source LIKE 'auto:%'", name="source"),
        UniqueConstraint("from_currency", "to_currency", "as_of", "source"),
        Index("ix_exchange_rates_pair_as_of", "from_currency", "to_currency", "as_of"),
    )
    from_currency: Mapped[str] = mapped_column(CHAR(3))
    to_currency: Mapped[str] = mapped_column(CHAR(3))
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    as_of: Mapped[date]
    source: Mapped[str] = mapped_column(Text)
