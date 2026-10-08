"""core identity and catalogs

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("google_sub", sa.Text(), nullable=True),
        sa.Column("timezone", sa.Text(), server_default=sa.text("'America/Lima'"), nullable=False),
        sa.Column(
            "base_currency", sa.CHAR(length=3), server_default=sa.text("'PEN'"), nullable=False
        ),
        sa.Column("locale", sa.Text(), server_default=sa.text("'es'"), nullable=False),
        sa.Column("pin_hash", sa.Text(), nullable=True),
        sa.Column("pin_failed_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("lock_after_minutes", sa.Integer(), nullable=True),
        sa.Column("report_currency", sa.CHAR(length=3), nullable=False),
        sa.Column(
            "preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
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
        sa.CheckConstraint("locale IN ('es', 'en')", name=op.f("ck_users_locale")),
        sa.CheckConstraint(
            "base_currency = upper(base_currency)", name=op.f("ck_users_base_currency_upper")
        ),
        sa.CheckConstraint("length(base_currency) = 3", name=op.f("ck_users_base_currency_length")),
        sa.CheckConstraint(
            "length(report_currency) = 3", name=op.f("ck_users_report_currency_length")
        ),
        sa.CheckConstraint(
            "report_currency = upper(report_currency)", name=op.f("ck_users_report_currency_upper")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(
        "uq_users_email",
        "users",
        [sa.literal_column("lower(email)")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_users_google_sub",
        "users",
        ["google_sub"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND google_sub IS NOT NULL"),
    )
    op.create_table(
        "accounts",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), nullable=False),
        sa.Column(
            "initial_balance",
            sa.Numeric(precision=18, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("color", sa.Text(), nullable=True),
        sa.Column("icon", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
            "type IN ('cash', 'bank', 'wallet', 'card', 'other')", name=op.f("ck_accounts_type")
        ),
        sa.CheckConstraint("currency = upper(currency)", name=op.f("ck_accounts_currency_upper")),
        sa.CheckConstraint("length(currency) = 3", name=op.f("ck_accounts_currency_length")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_accounts_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_accounts")),
        sa.UniqueConstraint("id", "currency", name="uq_accounts_id_currency"),
    )
    op.create_index(
        "uq_accounts_user_id_name",
        "accounts",
        ["user_id", sa.literal_column("lower(name)")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "categories",
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("icon", sa.Text(), nullable=True),
        sa.Column("color", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("system_key", sa.Text(), nullable=True),
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
        sa.CheckConstraint("kind IN ('income', 'expense')", name=op.f("ck_categories_kind")),
        sa.CheckConstraint(
            "system_key IN ('interest_income', 'interest_expense')",
            name=op.f("ck_categories_system_key"),
        ),
        sa.CheckConstraint(
            "is_system = (system_key IS NOT NULL)", name=op.f("ck_categories_is_system")
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["categories.id"], name=op.f("fk_categories_parent_id_categories")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_categories_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
    )
    op.create_index(
        "uq_categories_user_id_system_key",
        "categories",
        ["user_id", "system_key"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND system_key IS NOT NULL"),
    )
    op.create_table(
        "people",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "aliases", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False
        ),
        sa.Column("note", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_people_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_people")),
    )
    op.create_index(
        "ix_people_aliases", "people", ["aliases"], unique=False, postgresql_using="gin"
    )
    op.create_index("ix_people_name", "people", [sa.literal_column("lower(name)")], unique=False)
    op.create_table(
        "sessions",
        sa.Column("token_hash", sa.LargeBinary(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip", sa.Text(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_sessions_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
    )
    op.create_index(
        "ix_sessions_user_id_revoked_at", "sessions", ["user_id", "revoked_at"], unique=False
    )
    op.create_index(
        "uq_sessions_token_hash",
        "sessions",
        ["token_hash"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "tags",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("color", sa.Text(), nullable=True),
        sa.Column("icon", sa.Text(), nullable=True),
        sa.Column("emoji", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_tags_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tags")),
    )
    op.create_index(
        "uq_tags_user_id_name",
        "tags",
        ["user_id", sa.literal_column("lower(name)")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND archived_at IS NULL"),
    )

    op.execute("""
        CREATE FUNCTION validate_category_hierarchy() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE parent categories%ROWTYPE;
        BEGIN
            IF NEW.parent_id IS NOT NULL THEN
                IF NEW.parent_id = NEW.id THEN
                    RAISE EXCEPTION 'A category cannot be its own parent' USING ERRCODE = '23514';
                END IF;
                SELECT * INTO parent FROM categories WHERE id = NEW.parent_id FOR UPDATE;
                IF NOT FOUND OR parent.parent_id IS NOT NULL
                   OR parent.kind <> NEW.kind OR parent.user_id <> NEW.user_id THEN
                    RAISE EXCEPTION 'Category parent must be a root of the same kind and user'
                        USING ERRCODE = '23514';
                END IF;
            END IF;
            IF EXISTS (
                SELECT 1 FROM categories WHERE parent_id = NEW.id
                AND (NEW.parent_id IS NOT NULL OR kind <> NEW.kind OR user_id <> NEW.user_id)
            ) THEN
                RAISE EXCEPTION 'Category update would invalidate existing children'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER category_hierarchy
        BEFORE INSERT OR UPDATE OF parent_id, kind, user_id ON categories
        FOR EACH ROW EXECUTE FUNCTION validate_category_hierarchy()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER category_hierarchy ON categories")
    op.execute("DROP FUNCTION validate_category_hierarchy()")
    op.drop_index(
        "uq_tags_user_id_name",
        table_name="tags",
        postgresql_where=sa.text("deleted_at IS NULL AND archived_at IS NULL"),
    )
    op.drop_table("tags")
    op.drop_index(
        "uq_sessions_token_hash",
        table_name="sessions",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index("ix_sessions_user_id_revoked_at", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("ix_people_name", table_name="people")
    op.drop_index("ix_people_aliases", table_name="people", postgresql_using="gin")
    op.drop_table("people")
    op.drop_index(
        "uq_categories_user_id_system_key",
        table_name="categories",
        postgresql_where=sa.text("deleted_at IS NULL AND system_key IS NOT NULL"),
    )
    op.drop_table("categories")
    op.drop_index(
        "uq_accounts_user_id_name",
        table_name="accounts",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_table("accounts")
    op.drop_index(
        "uq_users_google_sub",
        table_name="users",
        postgresql_where=sa.text("deleted_at IS NULL AND google_sub IS NOT NULL"),
    )
    op.drop_index(
        "uq_users_email", table_name="users", postgresql_where=sa.text("deleted_at IS NULL")
    )
    op.drop_table("users")
