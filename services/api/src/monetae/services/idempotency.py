"""Idempotencia transaccional reutilizable, con retención de 24 horas."""

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from monetae.db.models import IdempotencyKey
from monetae.services.auth import AuthError


@dataclass(frozen=True)
class StoredResponse:
    status: int
    body: dict[str, object]


def request_hash(operation: str, body: dict[str, object]) -> bytes:
    # Incluye la operación: las claves comparten espacio entre endpoints.
    canonical = json.dumps(
        [operation, body],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode()).digest()


class IdempotencyService:
    """El llamador hace commit de resultado y efecto financiero juntos.

    El lock es por usuario/clave y dura hasta commit/rollback; las lecturas
    ordinarias no toman este bloqueo ni bloqueos de fila.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def execute(
        self,
        user_id: UUID,
        key: str | None,
        operation: str,
        body: dict[str, object],
        create: Callable[[], StoredResponse],
    ) -> StoredResponse:
        if key is None:
            return create()
        if not 1 <= len(key) <= 128:
            raise AuthError(
                422, "invalid_idempotency_key", "The key must have 1 to 128 characters."
            )
        digest = request_hash(operation, body)
        self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"idempotency:{user_id}:{key}"},
        )
        now = datetime.now(UTC)
        self.db.execute(
            delete(IdempotencyKey).where(
                IdempotencyKey.user_id == user_id, IdempotencyKey.expires_at <= now
            )
        )
        existing = self.db.scalar(
            select(IdempotencyKey).where(
                IdempotencyKey.user_id == user_id, IdempotencyKey.key == key
            )
        )
        if existing is not None:
            if existing.request_hash != digest:
                raise AuthError(
                    409, "idempotency_conflict", "This key was used for another request."
                )
            return StoredResponse(existing.response_status, existing.response_body)
        response = create()
        self.db.add(
            IdempotencyKey(
                user_id=user_id,
                key=key,
                request_hash=digest,
                response_status=response.status,
                response_body=response.body,
                created_at=now,
                expires_at=now + timedelta(hours=24),
            )
        )
        self.db.flush()
        return response
