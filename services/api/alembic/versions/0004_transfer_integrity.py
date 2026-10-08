"""Enforce group membership and one live leg per transfer direction.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        op.f("ck_transactions_transfer_group"),
        "transactions",
        "(kind = 'transfer') = (transfer_group_id IS NOT NULL)",
    )
    for direction, comparison in (("outgoing", "<"), ("incoming", ">")):
        op.create_index(
            f"uq_transactions_transfer_{direction}",
            "transactions",
            ["transfer_group_id"],
            unique=True,
            postgresql_where=sa.text(
                f"kind = 'transfer' AND amount {comparison} 0 AND deleted_at IS NULL"
            ),
        )


def downgrade() -> None:
    for direction in ("incoming", "outgoing"):
        op.drop_index(f"uq_transactions_transfer_{direction}", table_name="transactions")
    op.drop_constraint(op.f("ck_transactions_transfer_group"), "transactions", type_="check")
