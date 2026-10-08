from sqlalchemy import CHAR, DateTime, Engine, Numeric, inspect, text

from alembic import command

from .conftest import migration_config

TABLE_COLUMNS = {
    "users": {
        "email",
        "password_hash",
        "google_sub",
        "timezone",
        "base_currency",
        "locale",
        "pin_hash",
        "pin_failed_attempts",
        "lock_after_minutes",
        "report_currency",
        "preferences",
    },
    "sessions": {"token_hash", "last_seen_at", "expires_at", "user_agent", "ip", "revoked_at"},
    "accounts": {
        "name",
        "type",
        "currency",
        "initial_balance",
        "color",
        "icon",
        "sort_order",
        "archived_at",
    },
    "categories": {"parent_id", "kind", "name", "icon", "color", "is_system", "system_key"},
    "people": {"name", "aliases", "note"},
    "tags": {"name", "color", "icon", "emoji", "sort_order", "archived_at"},
}
CHECKS = {
    "users": {
        "ck_users_base_currency_upper",
        "ck_users_base_currency_length",
        "ck_users_report_currency_upper",
        "ck_users_report_currency_length",
        "ck_users_locale",
    },
    "accounts": {"ck_accounts_currency_upper", "ck_accounts_currency_length", "ck_accounts_type"},
    "categories": {"ck_categories_kind", "ck_categories_system_key", "ck_categories_is_system"},
}
PARTIAL_INDEXES = {
    "uq_users_email": ("lower(email)",),
    "uq_users_google_sub": ("google_sub", "google_sub IS NOT NULL"),
    "uq_accounts_user_id_name": ("user_id", "lower(name)"),
    "uq_tags_user_id_name": ("user_id", "lower(name)", "archived_at IS NULL"),
    "uq_categories_user_id_system_key": ("user_id", "system_key", "system_key IS NOT NULL"),
    "uq_sessions_token_hash": ("token_hash",),
}


def assert_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == {
        *TABLE_COLUMNS,
        "login_attempts",
        "transactions",
        "transaction_tags",
        "idempotency_keys",
        "alembic_version",
    }
    attempts = {c["name"]: c for c in inspector.get_columns("login_attempts")}
    assert set(attempts) == {"id", "email_lower", "ip", "succeeded", "attempted_at"}
    assert all(not c["nullable"] for c in attempts.values())
    assert str(attempts["id"]["type"]) == "UUID"
    assert attempts["id"]["default"] == "gen_random_uuid()"
    timestamp_type = attempts["attempted_at"]["type"]
    assert isinstance(timestamp_type, DateTime) and timestamp_type.timezone
    assert {tuple(i["column_names"]) for i in inspector.get_indexes("login_attempts")} == {
        ("email_lower", "attempted_at"),
        ("ip", "attempted_at"),
        ("attempted_at",),
    }
    for table, expected in TABLE_COLUMNS.items():
        common = {"id", "created_at", "updated_at", "deleted_at"}
        if table != "users":
            common.add("user_id")
        columns = {column["name"]: column for column in inspector.get_columns(table)}
        assert set(columns) == expected | common
        assert str(columns["id"]["type"]) == "UUID"
        id_default = columns["id"]["default"]
        assert id_default is not None and "gen_random_uuid()" in id_default
        assert not columns["id"]["nullable"]
        for name in ("created_at", "updated_at", "deleted_at"):
            column_type = columns[name]["type"]
            assert isinstance(column_type, DateTime) and column_type.timezone
            if name != "deleted_at":
                assert not columns[name]["nullable"]
                assert columns[name]["default"] == "now()"
        assert columns["deleted_at"]["nullable"]
        if table != "users":
            assert not columns["user_id"]["nullable"]
            assert any(
                fk["constrained_columns"] == ["user_id"] and fk["referred_table"] == "users"
                for fk in inspector.get_foreign_keys(table)
            )
        assert {c["name"] for c in inspector.get_check_constraints(table)} == CHECKS.get(
            table, set()
        )
    accounts = {c["name"]: c for c in inspector.get_columns("accounts")}
    money_type = accounts["initial_balance"]["type"]
    assert isinstance(money_type, Numeric) and money_type.precision == 18 and money_type.scale == 2
    currency_type = accounts["currency"]["type"]
    assert isinstance(currency_type, CHAR) and currency_type.length == 3
    assert any(
        c["column_names"] == ["id", "currency"]
        for c in inspector.get_unique_constraints("accounts")
    )
    assert any(
        fk["constrained_columns"] == ["parent_id"] and fk["referred_table"] == "categories"
        for fk in inspector.get_foreign_keys("categories")
    )
    with engine.connect() as connection:
        indexes: dict[str, str] = dict(
            connection.execute(
                text("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'public'")
            ).all()
        )
        for name, fragments in PARTIAL_INDEXES.items():
            definition = indexes[name]
            assert "CREATE UNIQUE INDEX" in definition
            assert "WHERE" in definition and "deleted_at IS NULL" in definition
            for fragment in fragments:
                assert fragment in definition
        assert "USING gin (aliases)" in indexes["ix_people_aliases"]
        assert "USING btree (lower(name))" in indexes["ix_people_name"]
        assert "(user_id, revoked_at)" in indexes["ix_sessions_user_id_revoked_at"]
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM information_schema.triggers "
                    "WHERE trigger_name = 'category_hierarchy'"
                )
            )
            == 2
        )
        assert (
            connection.scalar(
                text("SELECT count(*) FROM pg_proc WHERE proname = 'validate_category_hierarchy'")
            )
            == 1
        )


def test_upgrade_downgrade_upgrade_and_no_drift(database_url: str, db_engine: Engine) -> None:
    config = migration_config(database_url)
    assert_schema(db_engine)
    command.check(config)
    command.downgrade(config, "base")
    assert set(inspect(db_engine).get_table_names()) == {"alembic_version"}
    with db_engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM pg_proc WHERE proname = 'validate_category_hierarchy'")
            )
            == 0
        )
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM information_schema.triggers "
                    "WHERE trigger_name = 'category_hierarchy'"
                )
            )
            == 0
        )
    command.upgrade(config, "head")
    assert_schema(db_engine)
    command.check(config)


def test_migration_0002_reversible(database_url: str, db_engine: Engine) -> None:
    config = migration_config(database_url)
    command.downgrade(config, "0001")
    assert set(inspect(db_engine).get_table_names()) == {*TABLE_COLUMNS, "alembic_version"}
    command.upgrade(config, "head")
    assert_schema(db_engine)
    command.check(config)
