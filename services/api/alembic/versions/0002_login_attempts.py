"""Registro persistente de intentos de login (seguridad, sin user_id)."""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email_lower", sa.Text(), nullable=False),
        sa.Column("ip", sa.Text(), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login_attempts")),
    )
    for columns in [("email_lower", "attempted_at"), ("ip", "attempted_at"), ("attempted_at",)]:
        op.create_index("ix_login_attempts_" + "_".join(columns), "login_attempts", list(columns))


def downgrade() -> None:
    op.drop_table("login_attempts")
