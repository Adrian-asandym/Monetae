from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import Engine, delete, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from monetae.db.models import Account, ImportReviewItem, ImportRun, User

from .conftest import migration_config


def test_migration_0007_roundtrip_with_data(database_url: str, db_engine: Engine) -> None:
    config = migration_config(database_url)
    command.downgrade(config, "0006")
    # Escribir por SQL en 0006: los modelos actuales incluyen la columna de 0007.
    from sqlalchemy import text

    user_id, account_id = uuid4(), uuid4()
    with db_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO users (id, email, report_currency) VALUES (:id, :email, 'PEN')"),
            {"id": user_id, "email": f"migration-{user_id}@example.test"},
        )
        connection.execute(
            text(
                "INSERT INTO accounts (id, user_id, name, type, currency, initial_balance) "
                "VALUES (:id, :user_id, 'Synthetic', 'cash', 'PEN', 123.45)"
            ),
            {"id": account_id, "user_id": user_id},
        )
    try:
        for _ in range(2):
            command.upgrade(config, "0007")
            command.check(config)
            with Session(db_engine) as session:
                account = session.get(Account, account_id)
                assert account is not None and account.initial_balance == Decimal("123.45")
                account.import_external_id = "cashew:sqlite:synthetic"
                audit = ImportRun(
                    user_id=user_id,
                    source_kind="sqlite",
                    source_schema_version=48,
                    file_sha256="a" * 64,
                    mode="dry_run",
                    started_at=datetime.now(UTC),
                    report={"synthetic": True},
                )
                session.add(audit)
                session.flush()
                session.add(
                    ImportReviewItem(
                        user_id=user_id, import_run_id=audit.id, kind="synthetic", payload={}
                    )
                )
                session.commit()
            command.downgrade(config, "0006")
            inspector = inspect(db_engine)
            assert not {"import_runs", "import_review_items"} & set(inspector.get_table_names())
            assert "import_external_id" not in {
                c["name"] for c in inspector.get_columns("accounts")
            }
        command.upgrade(config, "0007")
        command.check(config)
        with Session(db_engine) as session:
            account = session.get(Account, account_id)
            assert account is not None and account.initial_balance == Decimal("123.45")
            assert account.import_external_id is None
        inspector = inspect(db_engine)
        for table in (
            "accounts",
            "categories",
            "people",
            "tags",
            "recurring_rules",
            "subscriptions",
        ):
            assert any(
                index["name"] == f"uq_{table}_user_import_external" and index["unique"]
                for index in inspector.get_indexes(table)
            )
        assert ("import_run_id", "user_id") in {
            tuple(fk["constrained_columns"])
            for fk in inspector.get_foreign_keys("import_review_items")
        }
    finally:
        command.upgrade(config, "head")
        with Session(db_engine) as session:
            for model in (ImportReviewItem, ImportRun, Account):
                session.execute(delete(model).where(model.user_id == user_id))
            session.execute(delete(User).where(User.id == user_id))
            session.commit()


def test_import_review_items_reject_cross_user(
    db_session: Session, users: tuple[User, User]
) -> None:
    first, second = users
    audit = ImportRun(
        user_id=first.id,
        source_kind="sqlite",
        source_schema_version=None,
        file_sha256="b" * 64,
        mode="apply",
        started_at=datetime.now(UTC),
        report={},
    )
    db_session.add(audit)
    db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            ImportReviewItem(
                user_id=second.id, import_run_id=audit.id, kind="synthetic", payload={}
            )
        )
        db_session.flush()
    assert not list(
        db_session.scalars(select(ImportReviewItem).where(ImportReviewItem.user_id == second.id))
    )
