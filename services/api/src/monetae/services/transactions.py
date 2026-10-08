"""CRUD y consultas del libro mayor, con aislamiento de usuario obligatorio."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import exists, func, literal_column, or_, select, text, tuple_
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from monetae.api.pagination import decode_cursor, encode_cursor
from monetae.api.schemas.transactions import TransactionBatch, TransactionCreate, TransactionUpdate
from monetae.db.models import (
    Account,
    Category,
    Loan,
    LoanMovement,
    Tag,
    Transaction,
    TransactionTag,
    User,
)
from monetae.db.models.ledger import SEARCH_VECTOR
from monetae.db.repository import UserScopedRepository
from monetae.domain.currency import Currency
from monetae.domain.errors import CurrencyMismatchError, InvalidExchangeRateError
from monetae.domain.transactions import InvalidTransactionError, normalize_transaction
from monetae.services.auth import AuthError


@dataclass(frozen=True)
class TransactionFilters:
    date_from: datetime | None = None
    date_to: datetime | None = None
    account_id: UUID | None = None
    category_id: UUID | None = None
    currency: str | None = None
    kind: str | None = None
    status: str | None = None
    tag_ids: tuple[UUID, ...] = ()
    q: str | None = None
    include_deleted: bool = False
    loan_id: UUID | None = None
    person_id: UUID | None = None

    def fingerprint(self, user_id: UUID) -> str:
        return json.dumps(
            [
                str(user_id),
                self.date_from.astimezone(UTC).isoformat() if self.date_from else None,
                self.date_to.astimezone(UTC).isoformat() if self.date_to else None,
                str(self.account_id),
                str(self.category_id),
                self.currency,
                self.kind,
                self.status,
                sorted({str(tag) for tag in self.tag_ids}),
                self.q,
                self.include_deleted,
                str(self.loan_id),
                str(self.person_id),
            ],
            separators=(",", ":"),
        )


class TransactionService:
    def __init__(self, db: Session, cursor_secret: str) -> None:
        self.db = db
        self.cursor_secret = cursor_secret

    def repository(self, user_id: UUID) -> UserScopedRepository[Transaction]:
        return UserScopedRepository(self.db, Transaction, user_id)

    def get(self, user_id: UUID, entity_id: UUID, *, include_deleted: bool = False) -> Transaction:
        row = self.repository(user_id).get(entity_id, include_deleted=include_deleted)
        if row is None:
            raise AuthError(404, "not_found", "The requested transaction was not found.")
        return row

    def _write_lock(self, user_id: UUID, entity_id: UUID) -> Transaction:
        # Serializa solamente escrituras de esta transacción, nunca sus lecturas.
        self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"transaction:{user_id}:{entity_id}"},
        )
        self.db.expire_all()
        row = self.get(user_id, entity_id, include_deleted=True)
        return row

    def _base_currency(self, user_id: UUID) -> str:
        # Compatible con update_user: impide una primera alta con base obsoleta.
        self.db.execute(
            text("SELECT pg_advisory_xact_lock_shared(hashtextextended(:key, 0))"),
            {"key": f"transaction-history:{user_id}"},
        )
        base = self.db.scalar(select(User.base_currency).where(User.id == user_id))
        if base is None:
            raise AuthError(404, "not_found", "User not found.")
        return base

    def _references(
        self, user_id: UUID, account_id: UUID, category_id: UUID | None, *, restoring: bool = False
    ) -> Account:
        # Los locks compartidos solo se toman al escribir; coordinan con DELETE
        # de catálogo y cambio de moneda. La FK sigue siendo la defensa de dueño.
        account = self.db.scalar(
            select(Account)
            .where(Account.user_id == user_id, Account.id == account_id)
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        category = None
        if category_id is not None:
            category = self.db.scalar(
                select(Category)
                .where(Category.user_id == user_id, Category.id == category_id)
                .with_for_update(read=True)
                .execution_options(populate_existing=True)
            )
        if account is None or (category_id is not None and category is None):
            raise AuthError(404, "not_found", "Account or category not found.")
        if account.deleted_at is not None or (category and category.deleted_at is not None):
            if restoring:
                raise AuthError(409, "restore_conflict", "Restore the account and category first.")
            raise AuthError(404, "not_found", "Account or category not found.")
        return account

    @staticmethod
    def _normalize(
        kind: str,
        amount: Decimal,
        currency: str,
        account_currency: str,
        base_currency: str,
        rate: Decimal,
    ) -> tuple[Decimal, Decimal]:
        try:
            money, normalized_rate = normalize_transaction(
                kind,
                amount,
                Currency(currency),
                Currency(account_currency),
                Currency(base_currency),
                rate,
            )
            return money.amount, normalized_rate
        except CurrencyMismatchError as exc:
            raise AuthError(
                422, "currency_mismatch", "Transaction currency must match its account."
            ) from exc
        except InvalidExchangeRateError as exc:
            raise AuthError(
                422, "invalid_fx_rate", "The historical exchange rate is invalid."
            ) from exc
        except InvalidTransactionError as exc:
            raise AuthError(422, "invalid_amount", str(exc)) from exc

    def create(self, user_id: UUID, payload: TransactionCreate) -> Transaction:
        base = self._base_currency(user_id)
        account = self._references(user_id, payload.account_id, payload.category_id)
        amount, rate = self._normalize(
            payload.kind,
            Decimal(payload.amount),
            payload.currency,
            account.currency,
            base,
            Decimal(payload.fx_rate_to_base),
        )
        values = payload.model_dump(exclude={"tag_ids"})
        values.update(
            amount=amount,
            fx_rate_to_base=rate,
            source="web",
            categorization_source="manual" if payload.category_id else None,
        )
        row = self.repository(user_id).add(Transaction(user_id=user_id, **values))
        self._replace_tags(user_id, row, payload.tag_ids)
        return row

    def update(self, user_id: UUID, entity_id: UUID, payload: TransactionUpdate) -> Transaction:
        base = self._base_currency(user_id)
        row = self._write_lock(user_id, entity_id)
        if row.deleted_at is not None:
            raise AuthError(404, "not_found", "Transaction not found.")
        if row.kind not in {"income", "expense"}:
            raise AuthError(409, "transaction_flow_required", "Use the transfer or loan resource.")
        if row.status == "posted" and payload.status == "scheduled":
            raise AuthError(
                409, "already_posted", "A posted transaction cannot be scheduled again."
            )
        account_id = payload.account_id if payload.account_id is not None else row.account_id
        category_id = (
            payload.category_id if "category_id" in payload.model_fields_set else row.category_id
        )
        account = self._references(user_id, account_id, category_id)
        amount, rate = self._normalize(
            payload.kind or row.kind,
            Decimal(payload.amount) if payload.amount is not None else row.amount,
            row.currency,
            account.currency,
            base,
            Decimal(payload.fx_rate_to_base)
            if payload.fx_rate_to_base is not None
            else row.fx_rate_to_base,
        )
        values = payload.model_dump(exclude_unset=True, exclude={"tag_ids"})
        values.update(amount=amount, fx_rate_to_base=rate)
        if "category_id" in values:
            values["categorization_source"] = "manual" if category_id else None
        for key, value in values.items():
            setattr(row, key, value)
        if payload.tag_ids is not None:
            self._replace_tags(user_id, row, payload.tag_ids)
        self.db.flush()
        return row

    def delete(self, user_id: UUID, entity_id: UUID) -> None:
        row = self._write_lock(user_id, entity_id)
        if row.deleted_at is not None:
            raise AuthError(404, "not_found", "Transaction not found.")
        if row.kind not in {"income", "expense"}:
            raise AuthError(409, "transaction_flow_required", "Use the transfer or loan resource.")
        row.deleted_at = datetime.now(UTC)
        self.db.flush()

    def restore(self, user_id: UUID, entity_id: UUID) -> Transaction:
        row = self._write_lock(user_id, entity_id)
        if row.kind not in {"income", "expense"}:
            raise AuthError(409, "transaction_flow_required", "Use the transfer or loan resource.")
        self._references(user_id, row.account_id, row.category_id, restoring=True)
        row.deleted_at = None
        self.db.flush()
        return row

    def replace_tags(self, user_id: UUID, entity_id: UUID, tag_ids: list[UUID]) -> Transaction:
        row = self._write_lock(user_id, entity_id)
        if row.deleted_at is not None:
            raise AuthError(404, "not_found", "Transaction not found.")
        self._replace_tags(user_id, row, tag_ids)
        return row

    def _replace_tags(self, user_id: UUID, row: Transaction, tag_ids: list[UUID]) -> None:
        desired = set(tag_ids)
        links = list(
            self.db.scalars(
                select(TransactionTag)
                .where(TransactionTag.user_id == user_id, TransactionTag.transaction_id == row.id)
                .order_by(TransactionTag.created_at.desc(), TransactionTag.id.desc())
            )
        )
        active = {link.tag_id for link in links if link.deleted_at is None}
        tags = (
            list(
                self.db.scalars(
                    select(Tag)
                    .where(Tag.user_id == user_id, Tag.id.in_(desired), Tag.deleted_at.is_(None))
                    .order_by(Tag.id)
                    .with_for_update(read=True)
                )
            )
            if desired
            else []
        )
        if len(tags) != len(desired):
            raise AuthError(404, "not_found", "A requested tag was not found.")
        if any(tag.archived_at is not None and tag.id not in active for tag in tags):
            raise AuthError(422, "tag_archived", "An archived tag cannot be added.")
        now = datetime.now(UTC)
        for link in links:
            if link.deleted_at is None and link.tag_id not in desired:
                link.deleted_at = now
        # Retirar antes de restaurar mantiene el índice único parcial.
        self.db.flush()
        for tag_id in desired - active:
            previous = next((link for link in links if link.tag_id == tag_id), None)
            if previous is not None:
                previous.deleted_at = None
            else:
                self.db.add(TransactionTag(user_id=user_id, transaction_id=row.id, tag_id=tag_id))
        row.updated_at = now
        self.db.flush()

    def batch(self, user_id: UUID, payload: TransactionBatch) -> int:
        if payload.changes is not None and payload.changes.model_fields_set - {
            "category_id",
            "occurred_at",
            "status",
            "title",
            "note",
        }:
            raise AuthError(
                422, "batch_field_not_allowed", "This field cannot be edited in a batch."
            )
        # El orden UUID es común a todos los lotes, independientemente del orden de entrada.
        self._base_currency(user_id)
        rows = [self._write_lock(user_id, id) for id in sorted(payload.transaction_ids)]
        if any(row.deleted_at is not None for row in rows) and payload.action != "restore":
            raise AuthError(404, "not_found", "Transaction not found.")
        if any(row.kind not in {"income", "expense"} for row in rows):
            raise AuthError(409, "transaction_flow_required", "Use the transfer or loan resource.")
        requested = set(payload.tag_ids or [])
        if requested:
            tags = list(
                self.db.scalars(
                    select(Tag)
                    .where(Tag.user_id == user_id, Tag.id.in_(requested), Tag.deleted_at.is_(None))
                    .order_by(Tag.id)
                    .with_for_update(read=True)
                )
            )
            if len(tags) != len(requested):
                raise AuthError(404, "not_found", "A requested tag was not found.")
            current_tags = self.tag_ids(user_id, rows)
            if any(
                tag.archived_at is not None and tag.id not in current_tags[row.id]
                for row in rows
                for tag in tags
            ):
                raise AuthError(422, "tag_archived", "An archived tag cannot be added.")
        else:
            current_tags = {}
        for row in rows:
            if payload.action == "delete":
                row.deleted_at = datetime.now(UTC)
            elif payload.action == "restore":
                self.restore(user_id, row.id)
            elif payload.action == "edit":
                assert payload.changes is not None
                self.update(user_id, row.id, payload.changes)
            else:
                active = set(current_tags[row.id])
                desired = active | requested if payload.action == "add_tags" else active - requested
                self._replace_tags(user_id, row, sorted(desired))
        self.db.flush()
        return len(rows)

    def post(
        self, user_id: UUID, entity_id: UUID, payload: TransactionUpdate | None = None
    ) -> Transaction:
        self._base_currency(user_id)
        row = self._write_lock(user_id, entity_id)
        if row.deleted_at is not None:
            raise AuthError(404, "not_found", "Transaction not found.")
        if row.kind not in {"income", "expense"} or row.status != "scheduled":
            raise AuthError(
                409, "not_scheduled", "Only scheduled direct transactions can be posted."
            )
        values = payload.model_dump(exclude_unset=True) if payload is not None else {}
        values["status"] = "posted"
        return self.update(user_id, entity_id, TransactionUpdate.model_validate(values))

    def loan_ids(self, user_id: UUID, rows: list[Transaction]) -> dict[UUID, UUID]:
        transaction_ids = [row.id for row in rows if row.kind == "loan"]
        if not transaction_ids:
            return {}
        links = self.db.execute(
            select(LoanMovement.transaction_id, LoanMovement.loan_id).where(
                LoanMovement.user_id == user_id,
                LoanMovement.transaction_id.in_(transaction_ids),
            )
        ).all()
        return {
            transaction_id: loan_id
            for transaction_id, loan_id in links
            if transaction_id is not None
        }

    def tag_ids(self, user_id: UUID, rows: list[Transaction]) -> dict[UUID, list[UUID]]:
        result: dict[UUID, list[UUID]] = {row.id: [] for row in rows}
        if not rows:
            return result
        links = self.db.execute(
            select(TransactionTag.transaction_id, TransactionTag.tag_id)
            .join(Tag, (Tag.id == TransactionTag.tag_id) & (Tag.user_id == TransactionTag.user_id))
            .where(
                TransactionTag.user_id == user_id,
                Tag.user_id == user_id,
                TransactionTag.transaction_id.in_(result),
                TransactionTag.deleted_at.is_(None),
                Tag.deleted_at.is_(None),
            )
            .order_by(TransactionTag.tag_id)
        )
        for transaction_id, tag_id in links:
            result[transaction_id].append(tag_id)
        return result

    def list(
        self, user_id: UUID, filters: TransactionFilters, limit: int, cursor: str | None
    ) -> tuple[list[Transaction], str | None]:
        fingerprint = filters.fingerprint(user_id)
        after = decode_cursor(cursor, "transactions", fingerprint, self.cursor_secret)
        criteria: list[ColumnElement[bool]] = []
        if after is not None:
            try:
                if len(after) != 2:
                    raise ValueError
                occurred_at = datetime.fromisoformat(after[0])
                if occurred_at.tzinfo is None:
                    raise ValueError
                entity_id = UUID(after[1])
            except (ValueError, TypeError) as exc:
                raise AuthError(400, "invalid_cursor", "The pagination cursor is invalid.") from exc
            criteria.append(
                tuple_(Transaction.occurred_at, Transaction.id) < tuple_(occurred_at, entity_id)
            )
        for name in ("account_id", "category_id", "currency", "kind", "status"):
            value = getattr(filters, name)
            if value is not None:
                criteria.append(getattr(Transaction, name) == value)
        if filters.date_from is not None:
            criteria.append(Transaction.occurred_at >= filters.date_from)
        if filters.date_to is not None:
            criteria.append(Transaction.occurred_at < filters.date_to)
        if filters.loan_id is not None or filters.person_id is not None:
            linked = (
                select(1)
                .select_from(LoanMovement)
                .join(
                    Loan, (Loan.id == LoanMovement.loan_id) & (Loan.user_id == LoanMovement.user_id)
                )
                .where(
                    LoanMovement.user_id == user_id,
                    Loan.user_id == user_id,
                    LoanMovement.transaction_id == Transaction.id,
                )
            )
            if filters.loan_id is not None:
                linked = linked.where(Loan.id == filters.loan_id)
            if filters.person_id is not None:
                linked = linked.where(Loan.person_id == filters.person_id)
            criteria.append(exists(linked))
        if filters.tag_ids:
            criteria.append(
                exists(
                    select(1)
                    .select_from(TransactionTag)
                    .join(
                        Tag,
                        (Tag.id == TransactionTag.tag_id) & (Tag.user_id == TransactionTag.user_id),
                    )
                    .where(
                        TransactionTag.user_id == user_id,
                        Tag.user_id == user_id,
                        TransactionTag.transaction_id == Transaction.id,
                        TransactionTag.tag_id.in_(filters.tag_ids),
                        TransactionTag.deleted_at.is_(None),
                        Tag.deleted_at.is_(None),
                    )
                )
            )
        if filters.q:
            escaped = filters.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            criteria.append(
                or_(
                    literal_column(SEARCH_VECTOR).op("@@")(
                        func.plainto_tsquery("spanish", filters.q)
                    ),
                    Transaction.title.ilike(f"%{escaped}%", escape="\\"),
                    Transaction.note.ilike(f"%{escaped}%", escape="\\"),
                )
            )
        rows = self.repository(user_id).list_matching(
            *criteria,
            order_by=(Transaction.occurred_at.desc(), Transaction.id.desc()),
            limit=limit + 1,
            include_deleted=filters.include_deleted,
        )
        page = rows[:limit]
        next_cursor = (
            encode_cursor(
                "transactions",
                fingerprint,
                [page[-1].occurred_at.isoformat(), str(page[-1].id)],
                self.cursor_secret,
            )
            if len(rows) > limit
            else None
        )
        return page, next_cursor
