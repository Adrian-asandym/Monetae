"""loans

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint("uq_people_id_user_id", "people", ["id", "user_id"])
    op.create_table(
        "loans",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), nullable=False),
        sa.Column("principal", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("opened_on", sa.Date(), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("import_external_id", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint("direction IN ('lent', 'borrowed')", name=op.f("ck_loans_direction")),
        sa.CheckConstraint(
            "currency = upper(currency) AND length(currency) = 3", name=op.f("ck_loans_currency")
        ),
        sa.CheckConstraint("principal > 0", name=op.f("ck_loans_principal_positive")),
        sa.ForeignKeyConstraint(
            ["person_id", "user_id"], ["people.id", "people.user_id"], name="fk_loans_person_owner"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_loans_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_loans")),
        sa.UniqueConstraint("id", "user_id", name="uq_loans_id_user_id"),
    )
    op.create_index(
        "uq_loans_user_import_external",
        "loans",
        ["user_id", "import_external_id"],
        unique=True,
        postgresql_where=sa.text("import_external_id IS NOT NULL AND deleted_at IS NULL"),
    )
    op.create_table(
        "loan_movements",
        sa.Column("loan_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("amount_in_loan_currency", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=True),
        sa.Column("interest_part", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("principal_part", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("fx_rate_applied", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            (
                "(kind = 'adjustment' AND amount_in_loan_currency <> 0) OR (kind <> "
                "'adjustment' AND amount_in_loan_currency > 0)"
            ),
            name=op.f("ck_loan_movements_amount"),
        ),
        sa.CheckConstraint(
            (
                "(kind IN ('payment', 'write_off') AND interest_part IS NOT NULL AND "
                "principal_part IS NOT NULL AND interest_part >= 0 AND principal_part >= "
                "0 AND interest_part + principal_part = amount_in_loan_currency) OR (kind"
                " NOT IN ('payment', 'write_off') AND interest_part IS NULL AND "
                "principal_part IS NULL)"
            ),
            name=op.f("ck_loan_movements_split"),
        ),
        sa.CheckConstraint(
            "kind IN ('disbursement', 'interest', 'payment', 'adjustment', 'write_off')",
            name=op.f("ck_loan_movements_kind"),
        ),
        sa.CheckConstraint(
            "kind IN ('disbursement', 'payment') OR "
            "(transaction_id IS NULL AND fx_rate_applied IS NULL)",
            name=op.f("ck_loan_movements_cash"),
        ),
        sa.CheckConstraint(
            "fx_rate_applied IS NULL OR (transaction_id IS NOT NULL AND fx_rate_applied > 0)",
            name=op.f("ck_loan_movements_fx_rate"),
        ),
        sa.CheckConstraint("sequence >= 0", name=op.f("ck_loan_movements_sequence")),
        sa.ForeignKeyConstraint(
            ["loan_id", "user_id"],
            ["loans.id", "loans.user_id"],
            name="fk_loan_movements_loan_owner",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id", "user_id"],
            ["transactions.id", "transactions.user_id"],
            name="fk_loan_movements_transaction_owner",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_loan_movements_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_loan_movements")),
        sa.UniqueConstraint("loan_id", "sequence", name="uq_loan_movements_sequence"),
        sa.UniqueConstraint("transaction_id", name="uq_loan_movements_transaction"),
    )
    op.create_index(
        "ix_loan_movements_user_loan_occurred",
        "loan_movements",
        ["user_id", "loan_id", "occurred_at", "sequence"],
        unique=False,
    )
    op.create_index(
        "uq_loan_movements_disbursement",
        "loan_movements",
        ["loan_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'disbursement' AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_loan_movements_disbursement",
        table_name="loan_movements",
        postgresql_where=sa.text("kind = 'disbursement' AND deleted_at IS NULL"),
    )
    op.drop_index("ix_loan_movements_user_loan_occurred", table_name="loan_movements")
    op.drop_table("loan_movements")
    op.drop_index(
        "uq_loans_user_import_external",
        table_name="loans",
        postgresql_where=sa.text("import_external_id IS NOT NULL AND deleted_at IS NULL"),
    )
    op.drop_table("loans")
    op.drop_constraint("uq_people_id_user_id", "people", type_="unique")
