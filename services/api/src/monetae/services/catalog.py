"""Reglas y persistencia de catálogos, siempre acotadas al usuario autenticado."""

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import Text, column, exists, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from monetae.api.pagination import decode_cursor, encode_cursor, keyset_predicate
from monetae.db.models import Account, Category, Person, Tag, Transaction
from monetae.db.repository import UserScopedRepository
from monetae.services.auth import AuthError

EntityT = TypeVar("EntityT", Account, Category, Person, Tag)


class CatalogService:
    def __init__(self, db: Session, cursor_secret: str) -> None:
        self.db = db
        self.cursor_secret = cursor_secret

    @staticmethod
    def _repository(
        db: Session, model: type[EntityT], user_id: UUID
    ) -> UserScopedRepository[EntityT]:
        return UserScopedRepository(db, model, user_id)

    def _name_lock(self, user_id: UUID, model: str, name: str) -> None:
        self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"catalog:{user_id}:{model}:{name.casefold()}"},
        )

    def _duplicate(
        self, model: type[EntityT], user_id: UUID, name: str, *, active_tags: bool = False
    ) -> bool:
        conditions: list[ColumnElement[bool]] = [
            model.user_id == user_id,
            model.deleted_at.is_(None),
            func.lower(model.name) == name.casefold(),
        ]
        if active_tags and model is Tag:
            conditions.append(Tag.archived_at.is_(None))
        return self.db.scalar(select(model.id).where(*conditions).limit(1)) is not None

    def _flush(self, operation: Callable[[], EntityT], *, duplicate_code: bool = True) -> EntityT:
        try:
            with self.db.begin_nested():
                return operation()
        except IntegrityError as exc:
            constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", "")
            if duplicate_code and constraint in {
                "uq_accounts_user_id_name",
                "uq_tags_user_id_name",
            }:
                raise AuthError(
                    409, "duplicate_name", "A resource with this name already exists."
                ) from exc
            if isinstance(exc.orig, Exception) and "23514" in str(
                getattr(exc.orig, "sqlstate", "")
            ):
                raise AuthError(
                    422, "invalid_category_hierarchy", "The category hierarchy is invalid."
                ) from exc
            raise

    def _list(
        self,
        model: type[EntityT],
        user_id: UUID,
        limit: int,
        cursor: str | None,
        resource: str,
        filters: str,
        # SQLAlchemy's mapped attributes use a dynamic overloaded expression API.
        columns: Sequence[Any],
        order: Sequence[Any],
        key: Callable[[EntityT], list[str]],
        criteria: Sequence[ColumnElement[bool]] = (),
    ) -> tuple[list[EntityT], str | None]:
        after = decode_cursor(cursor, resource, filters, self.cursor_secret)
        conditions = list(criteria)
        if after is not None:
            try:
                values = [
                    (
                        str(value)
                        if column.type.python_type is object
                        else column.type.python_type(value)
                    )
                    for column, value in zip(columns, after, strict=True)
                ]
            except (IndexError, TypeError, ValueError) as exc:
                raise AuthError(400, "invalid_cursor", "The pagination cursor is invalid.") from exc
            conditions.append(keyset_predicate(columns, values))
        repo = self._repository(self.db, model, user_id)
        rows = repo.list_matching(*conditions, order_by=tuple(order), limit=limit + 1)
        page = rows[:limit]
        next_cursor = (
            encode_cursor(resource, filters, key(page[-1]), self.cursor_secret)
            if len(rows) > limit
            else None
        )
        return page, next_cursor

    def list_accounts(
        self, user_id: UUID, limit: int, cursor: str | None, include_archived: bool
    ) -> tuple[list[Account], str | None]:
        criteria = () if include_archived else (Account.archived_at.is_(None),)

        def key(row: Account) -> list[str]:
            return [str(row.sort_order), row.name.lower(), str(row.id)]

        return self._list(
            Account,
            user_id,
            limit,
            cursor,
            "accounts",
            str(include_archived),
            (Account.sort_order, func.lower(Account.name), Account.id),
            (Account.sort_order, func.lower(Account.name), Account.id),
            key,
            criteria,
        )

    def list_categories(
        self, user_id: UUID, limit: int, cursor: str | None
    ) -> tuple[list[Category], str | None]:
        def key(row: Category) -> list[str]:
            return [row.kind, row.name.lower(), str(row.id)]

        return self._list(
            Category,
            user_id,
            limit,
            cursor,
            "categories",
            "",
            (Category.kind, func.lower(Category.name), Category.id),
            (Category.kind, func.lower(Category.name), Category.id),
            key,
        )

    def list_people(
        self, user_id: UUID, limit: int, cursor: str | None, q: str | None
    ) -> tuple[list[Person], str | None]:
        normalized = q.casefold() if q else ""
        criteria: tuple[ColumnElement[bool], ...] = ()
        if q:
            aliases = (
                func.unnest(Person.aliases)
                .table_valued(column("alias", Text))
                .alias("person_alias")
                .render_derived()
            )
            criteria = (
                or_(
                    func.lower(Person.name).startswith(normalized, autoescape=True),
                    exists(
                        select(1)
                        .select_from(aliases)
                        .where(func.lower(aliases.c.alias) == normalized)
                    ),
                ),
            )

        def key(row: Person) -> list[str]:
            return [row.name.lower(), str(row.id)]

        return self._list(
            Person,
            user_id,
            limit,
            cursor,
            "people",
            normalized,
            (func.lower(Person.name), Person.id),
            (func.lower(Person.name), Person.id),
            key,
            criteria,
        )

    def list_tags(
        self, user_id: UUID, limit: int, cursor: str | None, include_archived: bool
    ) -> tuple[list[Tag], str | None]:
        criteria = () if include_archived else (Tag.archived_at.is_(None),)

        def key(row: Tag) -> list[str]:
            return [str(row.sort_order), row.name.lower(), str(row.id)]

        return self._list(
            Tag,
            user_id,
            limit,
            cursor,
            "tags",
            str(include_archived),
            (Tag.sort_order, func.lower(Tag.name), Tag.id),
            (Tag.sort_order, func.lower(Tag.name), Tag.id),
            key,
            criteria,
        )

    def get(self, model: type[EntityT], user_id: UUID, entity_id: UUID) -> EntityT:
        entity = self._repository(self.db, model, user_id).get(entity_id)
        if entity is None:
            raise AuthError(404, "not_found", "The requested resource was not found.")
        return entity

    def _lock_category(self, user_id: UUID, entity_id: UUID) -> Category:
        row = self.db.scalar(
            select(Category)
            .where(
                Category.id == entity_id,
                Category.user_id == user_id,
                Category.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if row is None:
            raise AuthError(404, "not_found", "The requested resource was not found.")
        return row

    @staticmethod
    def _validated_parent_id(value: object) -> UUID:
        if not isinstance(value, UUID):
            raise AuthError(422, "invalid_category_hierarchy", "The category hierarchy is invalid.")
        return value

    def create_account(self, user_id: UUID, values: dict[str, object]) -> Account:
        name = str(values["name"])
        self._name_lock(user_id, "accounts", name)
        if self._duplicate(Account, user_id, name):
            raise AuthError(409, "duplicate_name", "A resource with this name already exists.")
        normalized = dict(values)
        normalized["initial_balance"] = Decimal(str(values["initial_balance"]))
        row = Account(user_id=user_id, **normalized)
        return self._flush(lambda: self._repository(self.db, Account, user_id).add(row))

    def update_account(self, user_id: UUID, entity_id: UUID, values: dict[str, object]) -> Account:
        row = self.db.scalar(
            select(Account)
            .where(
                Account.user_id == user_id, Account.id == entity_id, Account.deleted_at.is_(None)
            )
            .with_for_update()
        )
        if row is None:
            raise AuthError(404, "not_found", "Account not found.")
        if (
            "currency" in values
            and values["currency"] != row.currency
            and self.has_transactions(user_id, account_id=entity_id, include_deleted=True)
        ):
            raise AuthError(
                409,
                "account_currency_locked",
                "Account currency cannot change after its first transaction.",
            )
        if "name" in values:
            name = str(values["name"])
            self._name_lock(user_id, "accounts", name)
            if name.casefold() != row.name.casefold() and self._duplicate(Account, user_id, name):
                raise AuthError(409, "duplicate_name", "A resource with this name already exists.")
        normalized = dict(values)
        if "initial_balance" in normalized:
            normalized["initial_balance"] = Decimal(str(normalized["initial_balance"]))
        repo = self._repository(self.db, Account, user_id)
        return self._flush(lambda: repo.update(entity_id, normalized) or row)

    def create_category(self, user_id: UUID, values: dict[str, object]) -> Category:
        parent_id = values.get("parent_id")
        if parent_id is not None:
            parent = self.get(Category, user_id, self._validated_parent_id(parent_id))
            if parent.parent_id is not None or parent.kind != values["kind"]:
                raise AuthError(
                    422, "invalid_category_hierarchy", "The category hierarchy is invalid."
                )
        row = Category(user_id=user_id, **values)
        return self._flush(lambda: self._repository(self.db, Category, user_id).add(row))

    def update_category(
        self, user_id: UUID, entity_id: UUID, values: dict[str, object]
    ) -> Category:
        row = self._lock_category(user_id, entity_id)
        if row.is_system:
            raise AuthError(
                409, "system_category_immutable", "System categories cannot be changed."
            )
        if "parent_id" in values and values["parent_id"] is not None:
            parent = self.get(Category, user_id, self._validated_parent_id(values["parent_id"]))
            if parent.parent_id is not None or parent.kind != values.get("kind", row.kind):
                raise AuthError(
                    422, "invalid_category_hierarchy", "The category hierarchy is invalid."
                )
        if "kind" in values and values["kind"] != row.kind:
            has_children = self.db.scalar(
                select(Category.id)
                .where(
                    Category.parent_id == entity_id,
                    Category.user_id == user_id,
                    Category.deleted_at.is_(None),
                )
                .limit(1)
            )
            if has_children:
                raise AuthError(
                    409, "category_has_children", "A category with children cannot change kind."
                )
        repo = self._repository(self.db, Category, user_id)
        return self._flush(lambda: repo.update(entity_id, values) or row)

    def delete_category(self, user_id: UUID, entity_id: UUID) -> Category:
        row = self._lock_category(user_id, entity_id)
        if row.is_system:
            raise AuthError(
                409, "system_category_immutable", "System categories cannot be deleted."
            )
        has_children = self.db.scalar(
            select(Category.id)
            .where(
                Category.parent_id == entity_id,
                Category.user_id == user_id,
                Category.deleted_at.is_(None),
            )
            .limit(1)
        )
        if has_children:
            raise AuthError(
                409, "category_has_children", "A category with children cannot be deleted."
            )
        if self.has_transactions(user_id, category_id=entity_id):
            raise AuthError(409, "category_in_use", "The category has active transactions.")
        repo = self._repository(self.db, Category, user_id)
        return self._flush(lambda: repo.soft_delete(entity_id) or row)

    def create_person(self, user_id: UUID, values: dict[str, object]) -> Person:
        row = Person(user_id=user_id, **values)
        return self._flush(lambda: self._repository(self.db, Person, user_id).add(row))

    def update_person(self, user_id: UUID, entity_id: UUID, values: dict[str, object]) -> Person:
        row = self.get(Person, user_id, entity_id)
        repo = self._repository(self.db, Person, user_id)
        return self._flush(lambda: repo.update(entity_id, values) or row)

    def create_tag(self, user_id: UUID, values: dict[str, object]) -> Tag:
        name = str(values["name"])
        self._name_lock(user_id, "tags", name)
        if self._duplicate(Tag, user_id, name, active_tags=True):
            raise AuthError(409, "duplicate_name", "A resource with this name already exists.")
        row = Tag(user_id=user_id, **values)
        return self._flush(lambda: self._repository(self.db, Tag, user_id).add(row))

    def update_tag(self, user_id: UUID, entity_id: UUID, values: dict[str, object]) -> Tag:
        row = self.get(Tag, user_id, entity_id)
        if "name" in values:
            name = str(values["name"])
            self._name_lock(user_id, "tags", name)
            if name.casefold() != row.name.casefold() and self._duplicate(
                Tag, user_id, name, active_tags=True
            ):
                raise AuthError(409, "duplicate_name", "A resource with this name already exists.")
        repo = self._repository(self.db, Tag, user_id)
        return self._flush(lambda: repo.update(entity_id, values) or row)

    def delete(self, model: type[EntityT], user_id: UUID, entity_id: UUID) -> EntityT:
        if model is Account:
            row = self.db.scalar(
                select(model)
                .where(model.user_id == user_id, model.id == entity_id, model.deleted_at.is_(None))
                .with_for_update()
            )
            if row is None:
                raise AuthError(404, "not_found", "Account not found.")
            if self.has_transactions(user_id, account_id=entity_id):
                raise AuthError(
                    409,
                    "account_in_use",
                    "The account has active transactions; archive it instead.",
                )
        else:
            row = self.get(model, user_id, entity_id)
        if isinstance(row, Category) and row.is_system:
            raise AuthError(
                409, "system_category_immutable", "System categories cannot be deleted."
            )
        self._repository(self.db, model, user_id).soft_delete(entity_id)
        return row

    def archive(self, model: type[EntityT], user_id: UUID, entity_id: UUID) -> EntityT:
        row = self.get(model, user_id, entity_id)

        def set_archived() -> EntityT:
            if isinstance(row, (Account, Tag)):
                row.archived_at = datetime.now(UTC)
            else:
                raise ValueError("Only accounts and tags can be archived.")
            self.db.flush()
            return row

        return self._flush(set_archived)

    def reactivate(self, model: type[EntityT], user_id: UUID, entity_id: UUID) -> EntityT:
        row = self.get(model, user_id, entity_id)
        if isinstance(row, Tag):
            self._name_lock(user_id, "tags", row.name)
            if self._duplicate(Tag, user_id, row.name, active_tags=True):
                raise AuthError(409, "duplicate_name", "A resource with this name already exists.")

        def set_reactivated() -> EntityT:
            if isinstance(row, (Account, Tag)):
                row.archived_at = None
            else:
                raise ValueError("Only accounts and tags can be reactivated.")
            self.db.flush()
            return row

        return self._flush(set_reactivated)

    def has_transactions(
        self,
        user_id: UUID,
        *,
        account_id: UUID | None = None,
        category_id: UUID | None = None,
        include_deleted: bool = False,
    ) -> bool:
        query = select(Transaction.id).where(Transaction.user_id == user_id)
        if account_id is not None:
            query = query.where(Transaction.account_id == account_id)
        if category_id is not None:
            query = query.where(Transaction.category_id == category_id)
        if not include_deleted:
            query = query.where(Transaction.deleted_at.is_(None))
        return self.db.scalar(query.limit(1)) is not None

    def balances(self, user_id: UUID, rows: Sequence[Account]) -> dict[UUID, Decimal]:
        if not rows:
            return {}
        # Una sola suma agrupada para todas las cuentas de la página.
        totals: dict[UUID, Decimal] = dict(
            self.db.execute(
                select(Transaction.account_id, func.sum(Transaction.amount))
                .where(
                    Transaction.user_id == user_id,
                    Transaction.account_id.in_([row.id for row in rows]),
                    Transaction.status == "posted",
                    Transaction.deleted_at.is_(None),
                )
                .group_by(Transaction.account_id)
            ).all()
        )
        return {row.id: row.initial_balance + totals.get(row.id, Decimal(0)) for row in rows}
