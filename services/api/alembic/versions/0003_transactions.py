"""transactions

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint("uq_accounts_id_user_id", "accounts", ["id", "user_id"])
    op.create_unique_constraint("uq_categories_id_user_id", "categories", ["id", "user_id"])
    op.create_unique_constraint("uq_tags_id_user_id", "tags", ["id", "user_id"])
    op.create_table(
        "idempotency_keys",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("request_hash", sa.LargeBinary(), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_idempotency_keys_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_idempotency_keys")),
        sa.UniqueConstraint("user_id", "key", name="uq_idempotency_keys_user_key"),
    )
    op.create_table(
        "transactions",
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("fx_rate_to_base", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("fx_rate_source", sa.Text(), nullable=False),
        sa.Column("transfer_group_id", sa.Uuid(), nullable=True),
        # Sin FK hasta la creación de recurring_rules.
        sa.Column("recurring_rule_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("raw_input", sa.Text(), nullable=True),
        sa.Column("categorization_source", sa.Text(), nullable=True),
        sa.Column("is_initial_data", sa.Boolean(), server_default=sa.text("false"), nullable=False),
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
        sa.CheckConstraint(
            "categorization_source IN ('manual', 'rule', 'model', 'llm')",
            name=op.f("ck_transactions_categorization_source"),
        ),
        sa.CheckConstraint(
            "fx_rate_source IN ('manual', 'auto')", name=op.f("ck_transactions_fx_rate_source")
        ),
        sa.CheckConstraint(
            "kind IN ('income', 'expense', 'transfer', 'loan')", name=op.f("ck_transactions_kind")
        ),
        sa.CheckConstraint(
            "source IN ('web', 'import', 'telegram', 'api')", name=op.f("ck_transactions_source")
        ),
        sa.CheckConstraint(
            "status IN ('posted', 'scheduled')", name=op.f("ck_transactions_status")
        ),
        sa.CheckConstraint("amount <> 0", name=op.f("ck_transactions_amount_nonzero")),
        sa.CheckConstraint(
            "currency = upper(currency)", name=op.f("ck_transactions_currency_upper")
        ),
        sa.CheckConstraint("fx_rate_to_base > 0", name=op.f("ck_transactions_fx_rate_positive")),
        sa.CheckConstraint("length(currency) = 3", name=op.f("ck_transactions_currency_length")),
        sa.ForeignKeyConstraint(
            ["account_id", "currency"],
            ["accounts.id", "accounts.currency"],
            name="fk_transactions_account_currency",
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["accounts.id", "accounts.user_id"],
            name="fk_transactions_account_owner",
        ),
        sa.ForeignKeyConstraint(
            ["category_id", "user_id"],
            ["categories.id", "categories.user_id"],
            name="fk_transactions_category_owner",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_transactions_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transactions")),
        sa.UniqueConstraint("id", "user_id", name="uq_transactions_id_user_id"),
    )
    op.create_index(
        "ix_transactions_search",
        "transactions",
        [sa.literal_column("to_tsvector('spanish', title || ' ' || coalesce(note, ''))")],
        unique=False,
        postgresql_using="gin",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_transactions_user_account_occurred",
        "transactions",
        ["user_id", "account_id", sa.literal_column("occurred_at DESC")],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_transactions_user_category_occurred",
        "transactions",
        ["user_id", "category_id", "occurred_at"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_transactions_user_occurred",
        "transactions",
        ["user_id", sa.literal_column("occurred_at DESC")],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_transactions_user_status_occurred",
        "transactions",
        ["user_id", "status", "occurred_at"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_transactions_user_import_external",
        "transactions",
        ["user_id", "import_external_id"],
        unique=True,
        postgresql_where=sa.text("import_external_id IS NOT NULL AND deleted_at IS NULL"),
    )
    op.create_table(
        "transaction_tags",
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["tag_id", "user_id"], ["tags.id", "tags.user_id"], name="fk_transaction_tags_tag_owner"
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id", "user_id"],
            ["transactions.id", "transactions.user_id"],
            name="fk_transaction_tags_transaction_owner",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_transaction_tags_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transaction_tags")),
    )
    op.create_index(
        "ix_transaction_tags_user_tag", "transaction_tags", ["user_id", "tag_id"], unique=False
    )
    op.create_index(
        "uq_transaction_tags_active",
        "transaction_tags",
        ["transaction_id", "tag_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_transaction_tags_active",
        table_name="transaction_tags",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index("ix_transaction_tags_user_tag", table_name="transaction_tags")
    op.drop_table("transaction_tags")
    op.drop_index(
        "uq_transactions_user_import_external",
        table_name="transactions",
        postgresql_where=sa.text("import_external_id IS NOT NULL AND deleted_at IS NULL"),
    )
    op.drop_index(
        "ix_transactions_user_status_occurred",
        table_name="transactions",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(
        "ix_transactions_user_occurred",
        table_name="transactions",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(
        "ix_transactions_user_category_occurred",
        table_name="transactions",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(
        "ix_transactions_user_account_occurred",
        table_name="transactions",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(
        "ix_transactions_search",
        table_name="transactions",
        postgresql_using="gin",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_table("transactions")
    op.drop_table("idempotency_keys")
    op.drop_constraint("uq_tags_id_user_id", "tags", type_="unique")
    op.drop_constraint("uq_categories_id_user_id", "categories", type_="unique")
    op.drop_constraint("uq_accounts_id_user_id", "accounts", type_="unique")
