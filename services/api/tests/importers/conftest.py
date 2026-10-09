"""Exclusivamente copias temporales de fuentes sintéticas."""

import shutil
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from monetae.db.models import User
from monetae.importers.cashew.mapping import ImportOptions
from monetae.importers.cashew.reader import Snapshot, read_snapshot

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "cashew_v48"


@pytest.fixture
def source_path(tmp_path: Path) -> Path:
    target = tmp_path / "synthetic.sqlite"
    shutil.copyfile(FIXTURES / "synthetic_v48.sqlite", target)
    return target


@pytest.fixture
def snapshot(source_path: Path) -> Snapshot:
    return read_snapshot(source_path)


@pytest.fixture
def options(source_path: Path) -> ImportOptions:
    return ImportOptions(fx_rate_overrides={"USD": Decimal("3.800000")}, source_path=source_path)


@pytest.fixture
def import_user(db_session: Session) -> User:
    user = User(email="importer@example.test", base_currency="PEN", report_currency="PEN")
    db_session.add(user)
    db_session.flush()
    return user
