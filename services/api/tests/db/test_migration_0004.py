from uuid import uuid4

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from monetae.db.models import Account, User

from .conftest import migration_config


def test_migration_0004_roundtrip(database_url: str, db_engine: Engine) -> None:
    config = migration_config(database_url)
    command.downgrade(config, "0003")
    assert "ck_transactions_transfer_group" not in {
        c["name"] for c in inspect(db_engine).get_check_constraints("transactions")
    }
    command.upgrade(config, "0004")
    command.check(config)
    command.downgrade(config, "0003")
    command.upgrade(config, "0004")
    command.check(config)
    indexes = {i["name"]: i for i in inspect(db_engine).get_indexes("transactions")}
    for direction in ("incoming", "outgoing"):
        assert indexes[f"uq_transactions_transfer_{direction}"]["unique"]


def test_direct_sql_transfer_integrity(db_session: Session, users: tuple[User, User]) -> None:
    account = Account(user_id=users[0].id, name="Wallet", type="cash", currency="PEN")
    db_session.add(account)
    db_session.flush()
    group = uuid4()
    insert = text(
        "INSERT INTO transactions (user_id, account_id, currency, kind, amount, "
        "transfer_group_id, occurred_at, status, title, fx_rate_to_base, fx_rate_source, source) "
        "VALUES (:user, :account, 'PEN', :kind, :amount, :group, now(), 'posted', "
        "'Synthetic transfer', 1, 'manual', 'web')"
    )
    params = {"user": users[0].id, "account": account.id, "group": group, "kind": "transfer"}
    for amount in (-10, 10):
        db_session.execute(insert, {**params, "amount": amount})
    for changes in (
        {"amount": -5},
        {"amount": 5},
        {"amount": 5, "group": None},
        {"amount": 5, "kind": "income"},
    ):
        with pytest.raises(IntegrityError), db_session.begin_nested():
            db_session.execute(insert, {**params, **changes})
    db_session.execute(
        text("UPDATE transactions SET deleted_at=now() WHERE transfer_group_id=:group"),
        {"group": group},
    )
    db_session.execute(insert, {**params, "amount": -5})
    db_session.execute(insert, {**params, "amount": 5})
