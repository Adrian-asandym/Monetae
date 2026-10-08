"""Regresiones de concurrencia con transacciones PostgreSQL independientes."""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Barrier, Lock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Connection, Engine, delete, event, select, text
from sqlalchemy.engine import ExecutionContext
from sqlalchemy.engine.interfaces import DBAPICursor
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session as DbSession

from monetae.config import Settings
from monetae.db.models import Category, LoginAttempt, Session, User
from monetae.services.auth import AuthError, AuthService

from .conftest import PASSWORD, FakeClock


@dataclass(frozen=True)
class AuthData:
    user_id: UUID
    email: str
    tokens: tuple[str, str]
    settings: Settings
    clock: FakeClock


@pytest.fixture
def committed_auth(db_engine: Engine) -> Iterator[AuthData]:
    email = f"concurrency-{uuid4().hex}@example.test"
    settings = Settings(environment="test", session_idle_minutes=10, session_absolute_days=1)
    clock = FakeClock()
    with DbSession(db_engine, expire_on_commit=False) as db:
        service = AuthService(db, settings, clock)
        user = service.create_user(email, PASSWORD)
        db.commit()
        first_token = service.login(email, PASSWORD, email, "synthetic-client")[2]
        db.commit()
        second_token = service.login(email, PASSWORD, email, "synthetic-client")[2]
        db.commit()
        data = AuthData(user.id, email, (first_token, second_token), settings, clock)
    try:
        yield data
    finally:
        with DbSession(db_engine) as db:
            db.execute(delete(Session).where(Session.user_id == data.user_id))
            db.execute(delete(Category).where(Category.user_id == data.user_id))
            db.execute(delete(LoginAttempt).where(LoginAttempt.email_lower == email))
            db.execute(delete(User).where(User.id == data.user_id))
            db.commit()


@pytest.mark.parametrize("touch_due", [False, True])
@pytest.mark.parametrize("same_session", [False, True])
def test_open_authenticated_transaction_does_not_lock_other_requests(
    db_engine: Engine, committed_auth: AuthData, touch_due: bool, same_session: bool
) -> None:
    data = committed_auth
    if touch_due:
        data.clock.advance(minutes=1)
    with DbSession(db_engine) as first, DbSession(db_engine) as second:
        service = AuthService(first, data.settings, data.clock)
        user, session = service.authenticate(data.tokens[0])
        assert first.in_transaction()
        assert user.id == data.user_id
        first_session_id = session.id
        second.execute(text("SET LOCAL lock_timeout = '500ms'"))
        token = data.tokens[0 if same_session else 1]
        other_user, other_session = AuthService(second, data.settings, data.clock).authenticate(
            token
        )
        assert other_user.id == data.user_id and second.in_transaction()
        if touch_due:
            assert session.last_seen_at == other_session.last_seen_at == data.clock.now()
        # Authentication succeeds even with a retained user lock if it only reads. Check
        # actual lock freedom on both rows as well, including the first request's touch.
        second.execute(select(User.id).where(User.id == data.user_id).with_for_update(nowait=True))
        second.execute(
            select(Session.id).where(Session.id == first_session_id).with_for_update(nowait=True)
        )


def test_concurrent_touch_updates_once_and_commits_before_handler(
    db_engine: Engine, committed_auth: AuthData
) -> None:
    data = committed_auth
    data.clock.advance(minutes=1)
    both_updates_ready = Barrier(2)
    counts: list[int] = []
    counts_lock = Lock()

    # SQLAlchemy event parameters are a DBAPI boundary; leave unused parameters opaque.
    def before_update(
        connection: Connection,
        cursor: DBAPICursor,
        statement: str,
        parameters: object,
        context: ExecutionContext,
        executemany: bool,
    ) -> None:
        if statement.startswith("UPDATE sessions SET"):
            both_updates_ready.wait(timeout=5)

    def after_update(
        connection: Connection,
        cursor: DBAPICursor,
        statement: str,
        parameters: object,
        context: ExecutionContext,
        executemany: bool,
    ) -> None:
        if statement.startswith("UPDATE sessions SET"):
            with counts_lock:
                counts.append(cursor.rowcount)

    def authenticate() -> UUID:
        with DbSession(db_engine) as db:
            db.execute(text("SET LOCAL lock_timeout = '500ms'"))
            user, session = AuthService(db, data.settings, data.clock).authenticate(data.tokens[0])
            assert user.id == data.user_id and session.last_seen_at == data.clock.now()
            return session.id

    event.listen(db_engine, "before_cursor_execute", before_update)
    event.listen(db_engine, "after_cursor_execute", after_update)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(authenticate)
            second = executor.submit(authenticate)
            assert first.result(timeout=10) == second.result(timeout=10)
        assert sorted(counts) == [0, 1]
        data.clock.advance(seconds=30)
        with DbSession(db_engine) as db:
            AuthService(db, data.settings, data.clock).authenticate(data.tokens[0])
        assert sorted(counts) == [0, 1]
    finally:
        event.remove(db_engine, "before_cursor_execute", before_update)
        event.remove(db_engine, "after_cursor_execute", after_update)


def test_touch_preserves_handler_rollback_and_expired_orm_objects(
    db_engine: Engine, committed_auth: AuthData
) -> None:
    data = committed_auth
    data.clock.advance(minutes=1)
    with DbSession(db_engine, expire_on_commit=True) as db:
        user, session = AuthService(db, data.settings, data.clock).authenticate(data.tokens[0])
        assert user.email == data.email and session.last_seen_at == data.clock.now()
        user.locale = "en"
        db.flush()
        db.rollback()
    with DbSession(db_engine) as db:
        user, session = AuthService(db, data.settings, data.clock).authenticate(data.tokens[0])
        assert user.locale == "es" and session.last_seen_at == data.clock.now()


@pytest.mark.parametrize("login_first", [True, False])
def test_login_and_logout_all_keep_exclusive_transaction_order(
    db_engine: Engine, committed_auth: AuthData, login_first: bool
) -> None:
    data = committed_auth
    with DbSession(db_engine, expire_on_commit=False) as first, DbSession(db_engine) as second:
        first_service = AuthService(first, data.settings, data.clock)
        second_service = AuthService(second, data.settings, data.clock)
        if login_first:
            new_token = first_service.login(data.email, PASSWORD, data.email, "new-client")[2]
        else:
            assert first_service.revoke(data.user_id) == 2
        second.execute(text("SET LOCAL lock_timeout = '500ms'"))
        # The retained user lock prevents the other operation from overtaking it.
        with pytest.raises(OperationalError) as blocked:
            if login_first:
                second_service.revoke(data.user_id)
            else:
                second_service.login(data.email, PASSWORD, data.email, "new-client")
        assert getattr(blocked.value.orig, "sqlstate", None) == "55P03"
        second.rollback()
        first.commit()
        if login_first:
            assert second_service.revoke(data.user_id) == 3
        else:
            new_token = second_service.login(data.email, PASSWORD, data.email, "new-client")[2]
        second.commit()
        for token in data.tokens:
            with pytest.raises(AuthError) as rejected:
                second_service.authenticate(token)
            assert rejected.value.status == 401
            second.rollback()
        if login_first:
            with pytest.raises(AuthError) as rejected:
                second_service.authenticate(new_token)
            assert rejected.value.status == 401
        else:
            assert second_service.authenticate(new_token)[0].id == data.user_id
