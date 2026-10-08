import pytest
from conftest import (
    migration_config as migration_config,  # noqa: F401 -- compatibility for T-203 tests
)
from sqlalchemy.orm import Session

from monetae.db.models import User


@pytest.fixture
def users(db_session: Session) -> tuple[User, User]:
    first = User(email="first@example.test", report_currency="PEN")
    second = User(email="second@example.test", report_currency="USD")
    db_session.add_all([first, second])
    db_session.flush()
    return first, second
