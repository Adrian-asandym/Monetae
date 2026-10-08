"""Persistencia genérica acotada al usuario autenticado."""

from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from monetae.db.base import UserScopedModel


class UserScopedRepository[T: UserScopedModel]:
    """Toda operación filtra por user_id y excluye filas borradas por defecto.

    Solo include_deleted=True permite operar sobre filas borradas; incluso restore
    exige esa opción explícita. add fija el dueño y rechaza instancias ajenas.
    El llamador controla el commit de la unidad de trabajo.
    """

    def __init__(self, session: Session, model: type[T], user_id: UUID) -> None:
        self.session = session
        self.model = model
        self.user_id = user_id

    def _select(self, *, include_deleted: bool) -> Select[T]:
        query = select(self.model).where(self.model.user_id == self.user_id)
        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))
        return query

    def get(self, entity_id: UUID, *, include_deleted: bool = False) -> T | None:
        return self.session.scalar(
            self._select(include_deleted=include_deleted).where(self.model.id == entity_id)
        )

    def list(self, *, include_deleted: bool = False, limit: int = 50, offset: int = 0) -> list[T]:
        if not 1 <= limit <= 200 or offset < 0:
            raise ValueError("limit must be between 1 and 200; offset must be nonnegative")
        query = self._select(include_deleted=include_deleted).order_by(self.model.id)
        return list(self.session.scalars(query.limit(limit).offset(offset)))

    def count(self, *, include_deleted: bool = False) -> int:
        query = select(func.count()).select_from(
            self._select(include_deleted=include_deleted).subquery()
        )
        return self.session.scalar(query) or 0

    def add(self, entity: T) -> T:
        if entity.user_id is not None and entity.user_id != self.user_id:
            raise ValueError("Cannot add an entity belonging to another user")
        if entity.deleted_at is not None:
            raise ValueError("Cannot add a deleted entity")
        entity.user_id = self.user_id
        self.session.add(entity)
        self.session.flush()
        return entity

    def update(
        self, entity_id: UUID, values: Mapping[str, object], *, include_deleted: bool = False
    ) -> T | None:
        protected = {"id", "user_id", "created_at", "updated_at", "deleted_at"}
        allowed = set(self.model.__mapper__.columns.keys()) - protected
        if not set(values) <= allowed:
            raise ValueError("Only editable model columns may be updated")
        entity = self.get(entity_id, include_deleted=include_deleted)
        if entity is None:
            return None
        for name, value in values.items():
            setattr(entity, name, value)
        self.session.flush()
        return entity

    def soft_delete(self, entity_id: UUID, *, include_deleted: bool = False) -> T | None:
        entity = self.get(entity_id, include_deleted=include_deleted)
        if entity is not None:
            entity.deleted_at = datetime.now(UTC)
            self.session.flush()
        return entity

    def restore(self, entity_id: UUID, *, include_deleted: bool = False) -> T | None:
        entity = self.get(entity_id, include_deleted=include_deleted)
        if entity is not None:
            entity.deleted_at = None
            self.session.flush()
        return entity
