"""Autenticación con argon2id, sesiones opacas y límites persistentes."""

import base64
import binascii
import hashlib
import json
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol, cast
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import object_session

from monetae.api.schemas.auth import UserPreferences
from monetae.config import Settings
from monetae.db.models import Account, Category, LoginAttempt, Session, User
from monetae.domain.passwords import (
    EMAIL_FAILURE_LIMIT,
    IP_FAILURE_LIMIT,
    LOGIN_WINDOW,
    PASSWORD_MAX_LENGTH,
    retry_after,
    validate_password,
)


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class AuthError(Exception):
    def __init__(self, status: int, code: str, detail: str, retry: int = 0) -> None:
        super().__init__(detail)
        self.status = status
        self.code = code
        self.detail = detail
        self.retry = retry


# One recommended-profile dummy hash per process, outside request handling.
PASSWORD_HASHER = PasswordHasher()
DUMMY_HASH = PASSWORD_HASHER.hash(secrets.token_urlsafe(32))


def token_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


class AuthService:
    def __init__(
        self,
        db: DbSession,
        settings: Settings,
        clock: Clock,
        hasher: PasswordHasher = PASSWORD_HASHER,
    ) -> None:
        self.db = db
        self.settings = settings
        self.clock = clock
        self.hasher = hasher

    def create_user(
        self,
        email: str,
        password: str,
        base_currency: str = "PEN",
        locale: str = "es",
        interest_income_name: str = "Intereses (ingreso)",
        interest_expense_name: str = "Intereses (gasto)",
    ) -> User:
        validate_password(password)
        user = User(
            email=email.lower(),
            password_hash=self.hasher.hash(password),
            base_currency=base_currency,
            report_currency=base_currency,
            locale=locale,
        )
        try:
            with self.db.begin_nested():
                self.db.add(user)
                self.db.flush()
                self.db.add_all(
                    [
                        Category(
                            user_id=user.id,
                            kind="income",
                            name=interest_income_name,
                            is_system=True,
                            system_key="interest_income",
                        ),
                        Category(
                            user_id=user.id,
                            kind="expense",
                            name=interest_expense_name,
                            is_system=True,
                            system_key="interest_expense",
                        ),
                    ]
                )
                self.db.flush()
        except IntegrityError as exc:
            # Do not include the SQL exception: its parameters contain email/hash.
            raise ValueError("A user with this email already exists.") from exc
        return user

    def _limit_attempts(self, email: str, ip: str, now: datetime) -> None:
        # Serialize both buckets across workers, including non-existent users.
        # Sorted advisory keys avoid deadlocks for requests sharing either bucket.
        keys = sorted(
            {
                cast(int, self.db.scalar(select(func.hashtextextended("email:" + email, 0)))),
                cast(int, self.db.scalar(select(func.hashtextextended("ip:" + ip, 0)))),
            }
        )
        for key in keys:
            self.db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
        self.db.execute(
            delete(LoginAttempt).where(LoginAttempt.attempted_at < now - timedelta(days=7))
        )
        failures = self.db.scalars(
            select(LoginAttempt).where(
                LoginAttempt.succeeded.is_(False),
                LoginAttempt.attempted_at > now - LOGIN_WINDOW,
                (LoginAttempt.email_lower == email) | (LoginAttempt.ip == ip),
            )
        ).all()
        wait = max(
            retry_after(
                [a.attempted_at for a in failures if a.email_lower == email],
                EMAIL_FAILURE_LIMIT,
                now,
            ),
            retry_after([a.attempted_at for a in failures if a.ip == ip], IP_FAILURE_LIMIT, now),
        )
        if wait:
            raise AuthError(429, "too_many_attempts", "Too many login attempts.", wait)

    def login(
        self, email: str, password: str, ip: str, user_agent: str
    ) -> tuple[User, Session, str]:
        now = self.clock.now()
        email = email.lower()
        self._limit_attempts(email, ip, now)
        user = self.db.scalar(
            select(User)
            .where(func.lower(User.email) == email, User.deleted_at.is_(None))
            .with_for_update()
        )
        stored_hash = user.password_hash if user is not None else None
        candidate = password if len(password) <= PASSWORD_MAX_LENGTH else "invalid-too-long"
        valid: bool
        try:
            valid = self.hasher.verify(stored_hash or DUMMY_HASH, candidate)
        except VerificationError:
            valid = False
        valid = valid and stored_hash is not None and len(password) <= PASSWORD_MAX_LENGTH
        self.db.add(LoginAttempt(email_lower=email, ip=ip, succeeded=valid, attempted_at=now))
        if not valid or user is None:
            # A failed response must not roll back its security record.
            self.db.commit()
            raise AuthError(401, "invalid_credentials", "Invalid email or password.")
        if self.hasher.check_needs_rehash(stored_hash or DUMMY_HASH):
            user.password_hash = self.hasher.hash(password)
        token = secrets.token_urlsafe(32)
        session = Session(
            user_id=user.id,
            token_hash=token_hash(token),
            created_at=now,
            updated_at=now,
            last_seen_at=now,
            expires_at=min(
                now + timedelta(minutes=self.settings.session_idle_minutes),
                now + timedelta(days=self.settings.session_absolute_days),
            ),
            user_agent=user_agent,
            ip=ip,
        )
        self.db.add(session)
        self.db.flush()
        return user, session, token

    def authenticate(self, token: str | None) -> tuple[User, Session]:
        now = self.clock.now()
        if not token or len(token) > 128:
            raise AuthError(401, "unauthenticated", "Authentication required.")
        # Token lookup is the identity boundary; all subsequent queries use its user_id.
        session = self.db.scalar(
            select(Session).where(
                Session.token_hash == token_hash(token),
                Session.deleted_at.is_(None),
                Session.revoked_at.is_(None),
            )
        )
        if session is None or self.expiration(session) <= now:
            raise AuthError(401, "unauthenticated", "Authentication required.")
        user = self.db.scalar(
            select(User).where(User.id == session.user_id, User.deleted_at.is_(None))
        )
        if user is None:
            raise AuthError(401, "unauthenticated", "Authentication required.")
        self.db.refresh(session)
        if (
            session.revoked_at is not None
            or session.deleted_at is not None
            or self.expiration(session) <= now
        ):
            raise AuthError(401, "unauthenticated", "Authentication required.")
        if now - session.last_seen_at >= timedelta(minutes=1):
            self._touch_session(session, user, now)
        return user, session

    def _touch_session(self, session: Session, user: User, now: datetime) -> None:
        # Authentication runs before handler writes. Commit this short atomic touch now,
        # so no session row lock remains held while the handler performs its work.
        self.db.execute(
            update(Session)
            .where(
                Session.id == session.id,
                Session.user_id == user.id,
                Session.last_seen_at <= now - timedelta(minutes=1),
                Session.last_seen_at > now - timedelta(minutes=self.settings.session_idle_minutes),
                Session.expires_at > now,
                Session.created_at > now - timedelta(days=self.settings.session_absolute_days),
                Session.deleted_at.is_(None),
                Session.revoked_at.is_(None),
            )
            .values(
                last_seen_at=now,
                expires_at=min(
                    now + timedelta(minutes=self.settings.session_idle_minutes),
                    session.created_at + timedelta(days=self.settings.session_absolute_days),
                ),
            )
            .execution_options(synchronize_session=False)
        )
        self.db.commit()
        # Also support callers whose Session uses expire_on_commit=True. Refresh reads
        # take no row locks and start only the handler's subsequent unit of work.
        self.db.refresh(user)
        self.db.refresh(session)

    def expiration(self, session: Session) -> datetime:
        return min(
            session.expires_at,
            session.last_seen_at + timedelta(minutes=self.settings.session_idle_minutes),
            session.created_at + timedelta(days=self.settings.session_absolute_days),
        )

    def list_sessions(
        self, user_id: UUID, limit: int, cursor: str | None
    ) -> tuple[list[Session], str | None]:
        now = self.clock.now()
        query = (
            select(Session)
            .where(
                Session.user_id == user_id,
                Session.deleted_at.is_(None),
                Session.revoked_at.is_(None),
                Session.expires_at > now,
                Session.last_seen_at > now - timedelta(minutes=self.settings.session_idle_minutes),
                Session.created_at > now - timedelta(days=self.settings.session_absolute_days),
            )
            .order_by(Session.id)
        )
        if cursor is not None:
            try:
                cursor_id = UUID(bytes=base64.urlsafe_b64decode(cursor.encode()))
            except (ValueError, binascii.Error) as exc:
                raise AuthError(400, "invalid_cursor", "Invalid pagination cursor.") from exc
            query = query.where(Session.id > cursor_id)
        rows = list(self.db.scalars(query.limit(limit + 1)))
        next_cursor = (
            base64.urlsafe_b64encode(rows[limit - 1].id.bytes).decode()
            if len(rows) > limit
            else None
        )
        return rows[:limit], next_cursor

    def revoke(self, user_id: UUID, session_id: UUID | None = None) -> int:
        # Serialize new logins against logout-all via the owning user row.
        self.db.execute(select(User.id).where(User.id == user_id).with_for_update())
        query = update(Session).where(
            Session.user_id == user_id, Session.deleted_at.is_(None), Session.revoked_at.is_(None)
        )
        if session_id is not None:
            query = query.where(Session.id == session_id)
        rows = self.db.scalars(
            query.values(revoked_at=self.clock.now()).returning(Session.id)
        ).all()
        if session_id is not None and not rows:
            raise AuthError(404, "not_found", "Session not found.")
        return len(rows)

    @staticmethod
    def preferences_for(user: User) -> UserPreferences:
        # jsonb is a JSON boundary: UUID strings are validated in JSON mode.
        preferences = UserPreferences.model_validate_json(json.dumps(user.preferences))
        if preferences.default_account_id is not None:
            db = object_session(user)
            if db is None:
                raise ValueError("Reading account preferences requires an attached user.")
            if not AuthService.active_account(db, user.id, preferences.default_account_id):
                preferences.default_account_id = None
        return preferences

    @staticmethod
    def active_account(db: DbSession, user_id: UUID, account_id: UUID) -> bool:
        return (
            db.scalar(
                select(Account.id).where(
                    Account.id == account_id,
                    Account.user_id == user_id,
                    Account.deleted_at.is_(None),
                    Account.archived_at.is_(None),
                )
            )
            is not None
        )

    def update_user(self, user: User, changes: dict[str, object]) -> User:
        if "preferences" in changes:
            preferences = UserPreferences.model_validate(changes["preferences"])
            if preferences.default_account_id is not None and not self.active_account(
                self.db, user.id, preferences.default_account_id
            ):
                raise AuthError(422, "account_not_found", "The default account was not found.")
            changes = {
                **changes,
                "preferences": preferences.model_dump(mode="json", exclude_unset=True),
            }
        if "base_currency" in changes:
            from monetae.db.models import Transaction

            self.db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                {"key": f"transaction-history:{user.id}"},
            )
            self.db.refresh(user, attribute_names=["base_currency"])
            if changes["base_currency"] != user.base_currency and self.db.scalar(
                select(Transaction.id).where(Transaction.user_id == user.id).limit(1)
            ):
                raise AuthError(
                    409,
                    "base_currency_locked",
                    "Base currency cannot change after the first transaction.",
                )
        for key, value in changes.items():
            setattr(user, key, value)
        self.db.flush()
        return user


ServiceFactory = Callable[[DbSession, Settings, Clock], AuthService]
