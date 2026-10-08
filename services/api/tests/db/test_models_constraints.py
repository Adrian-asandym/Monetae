from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from monetae.config import Settings
from monetae.db import session as session_module
from monetae.db.models import Account, Category, Person, Tag, User
from monetae.db.models import Session as LoginSession
from monetae.db.repository import UserScopedRepository


def test_email_partial_unique(db_session: Session, users: tuple[User, User]) -> None:
    first, _ = users
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(User(email=first.email.upper(), report_currency="PEN"))
        db_session.flush()
    first.deleted_at = datetime.now(UTC)
    db_session.flush()
    db_session.add(User(email=first.email.upper(), report_currency="PEN"))
    db_session.flush()


@pytest.mark.parametrize(
    "field,value",
    [
        ("base_currency", "pen"),
        ("base_currency", "PE"),
        ("report_currency", "usd"),
        ("report_currency", "US"),
        ("locale", "fr"),
    ],
)
def test_user_checks(db_session: Session, field: str, value: str) -> None:
    user = User(email="invalid@example.test", report_currency="PEN")
    setattr(user, field, value)
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(user)
        db_session.flush()


@pytest.mark.parametrize("currency", ["pen", "PE"])
def test_account_currency(db_session: Session, users: tuple[User, User], currency: str) -> None:
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(Account(user_id=users[0].id, name="Invalid", type="cash", currency=currency))
        db_session.flush()


def test_account_type(db_session: Session, users: tuple[User, User]) -> None:
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(Account(user_id=users[0].id, name="Invalid", type="invalid", currency="PEN"))
        db_session.flush()


@pytest.mark.parametrize("model", [Account, Tag])
def test_catalog_partial_names(
    db_session: Session, users: tuple[User, User], model: type[Account] | type[Tag]
) -> None:
    extra = {"type": "cash", "currency": "PEN"} if model is Account else {}
    first = model(user_id=users[0].id, name="Repeated", **extra)
    db_session.add(first)
    db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(model(user_id=users[0].id, name="REPEATED", **extra))
        db_session.flush()
    db_session.add(model(user_id=users[1].id, name="repeated", **extra))
    db_session.flush()
    first.deleted_at = datetime.now(UTC)
    db_session.flush()
    db_session.add(model(user_id=users[0].id, name="repeated", **extra))
    db_session.flush()


def test_archived_tag_name_reusable(db_session: Session, users: tuple[User, User]) -> None:
    db_session.add(Tag(user_id=users[0].id, name="Archived", archived_at=datetime.now(UTC)))
    db_session.flush()
    db_session.add(Tag(user_id=users[0].id, name="ARCHIVED"))
    db_session.flush()


@pytest.fixture
def hierarchy(db_session: Session, users: tuple[User, User]) -> tuple[Category, Category, Category]:
    root = Category(user_id=users[0].id, name="Root", kind="expense")
    other = Category(user_id=users[0].id, name="Other root", kind="expense")
    db_session.add_all([root, other])
    db_session.flush()
    child = Category(user_id=users[0].id, name="Child", kind="expense", parent_id=root.id)
    db_session.add(child)
    db_session.flush()
    return root, child, other


@pytest.mark.parametrize("violation", ["grandchild", "kind", "user", "self"])
def test_category_parent_rules(
    db_session: Session,
    users: tuple[User, User],
    hierarchy: tuple[Category, Category, Category],
    violation: str,
) -> None:
    root, child, _ = hierarchy
    category = Category(user_id=users[0].id, name="Invalid", kind="expense", parent_id=root.id)
    if violation == "grandchild":
        category.parent_id = child.id
    elif violation == "kind":
        category.kind = "income"
    elif violation == "user":
        category.user_id = users[1].id
    else:
        category = root
    with pytest.raises(IntegrityError), db_session.begin_nested():
        if violation == "self":
            category.parent_id = category.id
        db_session.add(category)
        db_session.flush()


@pytest.mark.parametrize("field", ["kind", "parent_id", "user_id"])
def test_category_parent_update_validates_children(
    db_session: Session,
    users: tuple[User, User],
    hierarchy: tuple[Category, Category, Category],
    field: str,
) -> None:
    root, _, other = hierarchy
    value = {"kind": "income", "parent_id": other.id, "user_id": users[1].id}[field]
    with pytest.raises(IntegrityError), db_session.begin_nested():
        setattr(root, field, value)
        db_session.flush()


@pytest.mark.parametrize(
    "key,is_system",
    [
        ("invalid", True),
        (None, True),
        ("interest_income", False),
    ],
)
def test_category_system_checks(
    db_session: Session, users: tuple[User, User], key: str | None, is_system: bool
) -> None:
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            Category(
                user_id=users[0].id,
                name="Invalid",
                kind="income",
                system_key=key,
                is_system=is_system,
            )
        )
        db_session.flush()


def test_category_kind_check(db_session: Session, users: tuple[User, User]) -> None:
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(Category(user_id=users[0].id, name="Invalid", kind="unknown"))
        db_session.flush()


def test_system_category_unique_per_user(db_session: Session, users: tuple[User, User]) -> None:
    for user in users:
        db_session.add(
            Category(
                user_id=user.id,
                name="Interest",
                kind="income",
                is_system=True,
                system_key="interest_income",
            )
        )
    db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            Category(
                user_id=users[0].id,
                name="Duplicate",
                kind="income",
                is_system=True,
                system_key="interest_income",
            )
        )
        db_session.flush()


def test_session_token_partial_unique(db_session: Session, users: tuple[User, User]) -> None:
    now = datetime.now(UTC)
    first = LoginSession(
        user_id=users[0].id,
        token_hash=b"x" * 32,
        last_seen_at=now,
        expires_at=now + timedelta(days=1),
    )
    db_session.add(first)
    db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            LoginSession(
                user_id=users[1].id,
                token_hash=first.token_hash,
                last_seen_at=now,
                expires_at=now + timedelta(days=1),
            )
        )
        db_session.flush()
    first.deleted_at = now
    db_session.flush()
    db_session.add(
        LoginSession(
            user_id=users[1].id,
            token_hash=first.token_hash,
            last_seen_at=now,
            expires_at=now + timedelta(days=1),
        )
    )
    db_session.flush()


def test_google_sub_partial_unique(db_session: Session, users: tuple[User, User]) -> None:
    first, second = users
    first.google_sub = "synthetic-subject"
    db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        second.google_sub = first.google_sub
        db_session.flush()
    first.deleted_at = datetime.now(UTC)
    db_session.flush()
    second.google_sub = first.google_sub
    db_session.flush()


def test_defaults_money_aliases_and_updated_at(
    db_session: Session, users: tuple[User, User]
) -> None:
    user = users[0]
    assert user.timezone == "America/Lima" and user.base_currency == "PEN" and user.locale == "es"
    assert user.pin_failed_attempts == 0 and user.preferences == {}
    account = Account(user_id=user.id, name="Cash", type="cash", currency="PEN")
    person = Person(user_id=user.id, name="Person")
    db_session.add_all([account, person])
    db_session.flush()
    assert account.initial_balance == Decimal("0.00")
    assert account.sort_order == 0 and person.aliases == []
    assert account.created_at.utcoffset() == timedelta(0)
    before = account.updated_at
    account.name = "Renamed"
    db_session.flush()
    assert account.updated_at > before
    category = Category(user_id=user.id, name="Standard", kind="expense")
    db_session.add(category)
    db_session.flush()
    assert not category.is_system


def test_account_composite_fk_usable(db_session: Session, users: tuple[User, User]) -> None:
    account = Account(user_id=users[0].id, name="Cash", type="cash", currency="PEN")
    db_session.add(account)
    db_session.flush()
    # La tabla auxiliar se revierte con la transacción del fixture.
    db_session.execute(
        text(
            "CREATE TABLE fk_probe (account_id uuid, currency char(3), "
            "FOREIGN KEY (account_id, currency) REFERENCES accounts(id, currency))"
        )
    )
    insert = text("INSERT INTO fk_probe VALUES (:id, :currency)")
    db_session.execute(insert, {"id": account.id, "currency": "PEN"})
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(insert, {"id": account.id, "currency": "USD"})


def test_session_dependency_commit_rollback(
    database_url: str, db_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MONETAE_DATABASE_URL", database_url)
    iterator = session_module.get_session()
    session = next(iterator)
    user = User(email="committed@example.test", report_currency="PEN")
    session.add(user)
    with pytest.raises(StopIteration):
        next(iterator)
    with Session(db_engine) as observer:
        assert observer.get(User, user.id) is not None
    iterator = session_module.get_session()
    session = next(iterator)
    user = User(email="rolledback@example.test", report_currency="PEN")
    session.add(user)
    session.flush()
    failed_id = user.id
    with pytest.raises(ValueError, match="abort"):
        iterator.throw(ValueError("abort"))
    with Session(db_engine) as observer:
        assert observer.get(User, failed_id) is None
    session_module.get_engine(Settings(database_url=database_url)).dispose()


def test_missing_database_url() -> None:
    with pytest.raises(ValueError, match="MONETAE_DATABASE_URL"):
        session_module.get_engine(Settings(database_url=None))


def test_repository_rejects_deleted_add(db_session: Session, users: tuple[User, User]) -> None:
    repo = UserScopedRepository(db_session, Person, users[0].id)
    with pytest.raises(ValueError, match="deleted"):
        repo.add(Person(name="Deleted", deleted_at=datetime.now(UTC)))
