import os
import subprocess
import sys
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from monetae.db.models import Category, User


@pytest.fixture
def cli_user(db_engine: Engine) -> Iterator[None]:
    yield
    # CLI writes outside test savepoints. Remove only these synthetic test rows.
    with Session(db_engine) as db:
        user = db.scalar(select(User).where(User.email == "cli@example.test"))
        if user:
            for category in db.scalars(select(Category).where(Category.user_id == user.id)):
                db.delete(category)
            db.delete(user)
            db.commit()


def test_cli_stdin_duplicates_and_categories(
    database_url: str, db_engine: Engine, cli_user: None
) -> None:
    env = {**os.environ, "MONETAE_DATABASE_URL": database_url}
    args = [
        sys.executable,
        "-m",
        "monetae.cli",
        "create-user",
        "--email",
        "cli@example.test",
        "--base-currency",
        "USD",
        "--locale",
        "en",
        "--password-stdin",
    ]
    result = subprocess.run(
        args, input="synthetic-password-123\n", text=True, capture_output=True, env=env
    )
    assert result.returncode == 0 and "User created" in result.stdout
    duplicate = subprocess.run(
        args, input="synthetic-password-123\n", text=True, capture_output=True, env=env
    )
    assert duplicate.returncode == 1 and "already exists" in duplicate.stderr
    assert (
        "synthetic-password" not in duplicate.stderr and "cli@example.test" not in duplicate.stderr
    )
    with Session(db_engine) as db:
        user = db.scalar(select(User).where(User.email == "cli@example.test"))
        assert user is not None and user.report_currency == user.base_currency == "USD"
        rows = db.scalars(select(Category).where(Category.user_id == user.id)).all()
        assert {row.system_key for row in rows} == {"interest_income", "interest_expense"}
        assert all(row.is_system for row in rows)


def test_cli_rejects_password_argument() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "monetae.cli",
            "create-user",
            "--email",
            "cli@example.test",
            "--password",
            "argument-forbidden",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
