"""Global historical exchange rates for report conversion.

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("from_currency", sa.CHAR(3), nullable=False),
        sa.Column("to_currency", sa.CHAR(3), nullable=False),
        sa.Column("rate", sa.Numeric(18, 6), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("rate > 0", name="rate_positive"),
        sa.CheckConstraint("from_currency <> to_currency", name="different_currencies"),
        sa.CheckConstraint("source = 'manual' OR source LIKE 'auto:%'", name="source"),
        sa.UniqueConstraint("from_currency", "to_currency", "as_of", "source"),
    )
    op.create_index(
        "ix_exchange_rates_pair_as_of", "exchange_rates", ["from_currency", "to_currency", "as_of"]
    )


def downgrade() -> None:
    op.drop_index("ix_exchange_rates_pair_as_of", table_name="exchange_rates")
    op.drop_table("exchange_rates")
