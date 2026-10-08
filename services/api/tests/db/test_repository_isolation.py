import pytest
from sqlalchemy.orm import Session

from monetae.db.models import Account, Category, Person, Tag, User
from monetae.db.repository import UserScopedRepository


def verify_isolation[T: Account | Category | Person | Tag](
    session: Session, users: tuple[User, User], first: T, second: T
) -> None:
    user_a, user_b = users
    model = type(first)
    repo_a = UserScopedRepository(session, model, user_a.id)
    repo_b = UserScopedRepository(session, model, user_b.id)
    repo_a.add(first)
    repo_b.add(second)
    assert first.user_id == user_a.id
    assert second.user_id == user_b.id
    for include_deleted in (False, True):
        assert repo_a.get(second.id, include_deleted=include_deleted) is None
        assert repo_a.list(include_deleted=include_deleted) == [first]
        assert repo_a.count(include_deleted=include_deleted) == 1
        assert (
            repo_a.update(second.id, {"name": "Intrusion"}, include_deleted=include_deleted) is None
        )
        assert repo_a.soft_delete(second.id, include_deleted=include_deleted) is None
        assert repo_a.restore(second.id, include_deleted=include_deleted) is None
    assert second.name == "Second"
    assert repo_a.soft_delete(first.id) is first
    assert repo_a.get(first.id) is None
    assert repo_a.list() == []
    assert repo_a.count() == 0
    assert repo_a.update(first.id, {"name": "Hidden"}) is None
    assert repo_a.restore(first.id) is None
    assert repo_a.get(first.id, include_deleted=True) is first
    assert repo_b.get(second.id) is second
    assert second.deleted_at is None
    assert repo_b.count() == 1
    assert repo_b.soft_delete(second.id) is second
    assert repo_a.restore(second.id, include_deleted=True) is None
    assert repo_a.get(second.id, include_deleted=True) is None
    assert repo_a.count(include_deleted=True) == 1
    assert repo_a.restore(first.id, include_deleted=True) is first
    assert repo_a.update(first.id, {"name": "Updated"}) is first
    with pytest.raises(ValueError, match="another user"):
        repo_a.add(second)
    for field in ("id", "user_id", "deleted_at", "created_at", "updated_at", "unknown"):
        with pytest.raises(ValueError, match="editable"):
            repo_a.update(first.id, {field: user_b.id})


def test_accounts_isolation(db_session: Session, users: tuple[User, User]) -> None:
    verify_isolation(
        db_session,
        users,
        Account(name="First", type="cash", currency="PEN"),
        Account(name="Second", type="bank", currency="USD"),
    )


def test_categories_isolation(db_session: Session, users: tuple[User, User]) -> None:
    verify_isolation(
        db_session,
        users,
        Category(name="First", kind="expense"),
        Category(name="Second", kind="income"),
    )


def test_people_isolation(db_session: Session, users: tuple[User, User]) -> None:
    verify_isolation(db_session, users, Person(name="First"), Person(name="Second"))


def test_tags_isolation(db_session: Session, users: tuple[User, User]) -> None:
    verify_isolation(db_session, users, Tag(name="First"), Tag(name="Second"))
