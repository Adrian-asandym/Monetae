"""Add the optional user display name for RF-50."""

import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(length=60), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "display_name")
