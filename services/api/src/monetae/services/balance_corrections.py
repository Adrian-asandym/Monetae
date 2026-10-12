"""Atomic creation and cursor listing; subsequent leg edits use transactions."""

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session, aliased

from monetae.api.pagination import decode_cursor, encode_cursor
from monetae.api.schemas.balance_corrections import BalanceCorrectionCreate
from monetae.db.models import Category, Transaction
from monetae.services.auth import AuthError, Clock
from monetae.services.transactions import TransactionService


@dataclass(frozen=True)
class CorrectionPair:
    outgoing: Transaction
    incoming: Transaction

    def implicit_rate(self) -> Decimal:
        return (self.incoming.amount / -self.outgoing.amount).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )


@dataclass(frozen=True)
class CorrectionFilters:
    from_account_id: UUID | None = None
    to_account_id: UUID | None = None
    from_currency: str | None = None
    to_currency: str | None = None

    def fingerprint(self, user_id: UUID) -> str:
        return json.dumps(
            [
                str(user_id),
                str(self.from_account_id),
                str(self.to_account_id),
                self.from_currency,
                self.to_currency,
            ],
            separators=(",", ":"),
        )


class BalanceCorrectionService:
    def __init__(self, db: Session, cursor_secret: str, clock: Clock) -> None:
        self.db, self.cursor_secret, self.clock = db, cursor_secret, clock
        self.transactions = TransactionService(db, cursor_secret)

    def create(self, user_id: UUID, payload: BalanceCorrectionCreate) -> CorrectionPair:
        if payload.from_account_id == payload.to_account_id:
            raise AuthError(422, "correction_accounts_equal", "Correction accounts must differ.")
        base = self.transactions._base_currency(user_id)
        # All account locks follow UUID order, consistent with transfers.
        accounts = {
            id: self.transactions._references(user_id, id, None)
            for id in sorted({payload.from_account_id, payload.to_account_id})
        }
        if any(account.archived_at is not None for account in accounts.values()):
            raise AuthError(422, "account_archived", "An archived account cannot be used.")
        categories = {
            row.system_key: row
            for row in self.db.scalars(
                select(Category)
                .where(
                    Category.user_id == user_id,
                    Category.deleted_at.is_(None),
                    Category.system_key.in_(
                        ["balance_correction_expense", "balance_correction_income"]
                    ),
                )
                .order_by(Category.id)
                .with_for_update(read=True)
            )
        }
        group_id, now = uuid4(), self.clock.now()
        rows = []
        # A savepoint also makes direct service calls atomic if the caller catches an error.
        with self.db.begin_nested():
            for kind, account_id, raw_amount, raw_rate, occurred_at in (
                (
                    "expense",
                    payload.from_account_id,
                    payload.from_amount,
                    payload.from_fx_rate_to_base,
                    payload.occurred_at,
                ),
                (
                    "income",
                    payload.to_account_id,
                    payload.to_amount,
                    payload.to_fx_rate_to_base,
                    payload.to_occurred_at,
                ),
            ):
                assert occurred_at is not None
                account = accounts[account_id]
                amount = Decimal(raw_amount)
                amount, rate = self.transactions._normalize(
                    kind,
                    -amount if kind == "expense" else amount,
                    account.currency,
                    account.currency,
                    base,
                    Decimal(raw_rate),
                )
                category = categories.get(f"balance_correction_{kind}")
                if category is None:
                    raise AuthError(409, "system_category_missing", "Correction category missing.")
                row = Transaction(
                    user_id=user_id,
                    account_id=account.id,
                    category_id=category.id,
                    kind=kind,
                    amount=amount,
                    currency=account.currency,
                    fx_rate_to_base=rate,
                    fx_rate_source=payload.fx_rate_source,
                    transfer_group_id=group_id,
                    occurred_at=occurred_at,
                    status="scheduled" if occurred_at > now else "posted",
                    title=payload.title,
                    note=payload.note,
                    source="web",
                    categorization_source="manual",
                )
                self.db.add(row)
                self.db.flush()
                rows.append(row)
        return CorrectionPair(rows[0], rows[1])

    def list(
        self, user_id: UUID, filters: CorrectionFilters, limit: int, cursor: str | None
    ) -> tuple[list[CorrectionPair], str | None]:
        fingerprint = filters.fingerprint(user_id)
        resource = "balance-corrections"
        after = decode_cursor(cursor, resource, fingerprint, self.cursor_secret)
        outgoing, incoming = aliased(Transaction), aliased(Transaction)
        expense, income = aliased(Category), aliased(Category)
        query = (
            select(outgoing, incoming)
            .join(
                incoming,
                (incoming.user_id == outgoing.user_id)
                & (incoming.transfer_group_id == outgoing.transfer_group_id)
                & (incoming.kind == "income")
                & incoming.deleted_at.is_(None),
            )
            .join(
                expense,
                (expense.id == outgoing.category_id)
                & (expense.user_id == user_id)
                & (expense.system_key == "balance_correction_expense"),
            )
            .join(
                income,
                (income.id == incoming.category_id)
                & (income.user_id == user_id)
                & (income.system_key == "balance_correction_income"),
            )
            .where(
                outgoing.user_id == user_id,
                outgoing.kind == "expense",
                outgoing.deleted_at.is_(None),
                outgoing.transfer_group_id.is_not(None),
            )
        )
        for column, value in (
            (outgoing.account_id, filters.from_account_id),
            (incoming.account_id, filters.to_account_id),
            (outgoing.currency, filters.from_currency),
            (incoming.currency, filters.to_currency),
        ):
            if value is not None:
                query = query.where(column == value)
        if after is not None:
            try:
                if len(after) != 2:
                    raise ValueError
                occurred_at, group_id = datetime.fromisoformat(after[0]), UUID(after[1])
                if occurred_at.tzinfo is None:
                    raise ValueError
            except (ValueError, TypeError) as exc:
                raise AuthError(400, "invalid_cursor", "The pagination cursor is invalid.") from exc
            query = query.where(
                tuple_(outgoing.occurred_at, outgoing.transfer_group_id)
                < tuple_(occurred_at, group_id)
            )
        rows = self.db.execute(
            query.order_by(outgoing.occurred_at.desc(), outgoing.transfer_group_id.desc()).limit(
                limit + 1
            )
        ).all()
        page = [CorrectionPair(left, right) for left, right in rows[:limit]]
        next_cursor = (
            encode_cursor(
                resource,
                fingerprint,
                [
                    page[-1].outgoing.occurred_at.isoformat(),
                    str(page[-1].outgoing.transfer_group_id),
                ],
                self.cursor_secret,
            )
            if len(rows) > limit
            else None
        )
        return page, next_cursor
