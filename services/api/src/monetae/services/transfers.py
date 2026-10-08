"""Transferencias atómicas: dos filas, bloqueo de grupo y lecturas sin locks."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select, text, tuple_
from sqlalchemy.orm import Session, aliased

from monetae.api.pagination import decode_cursor, encode_cursor
from monetae.api.schemas.transfers import TransferCreate, TransferUpdate
from monetae.db.models import Account, Transaction
from monetae.domain.currency import Currency
from monetae.domain.errors import InvalidExchangeRateError
from monetae.domain.money import Money
from monetae.domain.transfers import (
    InvalidTransferAmountError,
    TransferAmountMismatchError,
    validate_transfer_amounts,
)
from monetae.services.auth import AuthError
from monetae.services.transactions import TransactionService


@dataclass(frozen=True)
class TransferPair:
    outgoing: Transaction
    incoming: Transaction

    def implicit_rate(self) -> Decimal:
        return validate_transfer_amounts(
            Money(-self.outgoing.amount, Currency(self.outgoing.currency)),
            Money(self.incoming.amount, Currency(self.incoming.currency)),
        )


class TransferService:
    def __init__(self, db: Session, cursor_secret: str) -> None:
        self.db = db
        self.cursor_secret = cursor_secret
        self.transactions = TransactionService(db, cursor_secret)

    def _write_lock(self, user_id: UUID, group_id: UUID) -> None:
        self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"transfer:{user_id}:{group_id}"},
        )
        self.db.expire_all()

    def get(self, user_id: UUID, group_id: UUID, *, include_deleted: bool = False) -> TransferPair:
        rows = list(
            self.db.scalars(
                select(Transaction)
                .where(
                    Transaction.user_id == user_id,
                    Transaction.kind == "transfer",
                    Transaction.transfer_group_id == group_id,
                )
                .order_by(Transaction.amount)
            )
        )
        if len(rows) != 2 or (not include_deleted and any(r.deleted_at for r in rows)):
            raise AuthError(404, "not_found", "Transfer not found.")
        return TransferPair(rows[0], rows[1])

    def _accounts(
        self, user_id: UUID, payload: TransferCreate, *, restoring: bool = False
    ) -> tuple[Account, Account]:
        if payload.from_account_id == payload.to_account_id:
            raise AuthError(422, "transfer_accounts_equal", "Transfer accounts must differ.")
        # Todos los locks de cuentas se toman en el mismo orden, incluso al intercambiarlas.
        accounts = {
            id: self.transactions._references(user_id, id, None, restoring=restoring)
            for id in sorted({payload.from_account_id, payload.to_account_id})
        }
        return accounts[payload.from_account_id], accounts[payload.to_account_id]

    def _apply(
        self,
        user_id: UUID,
        pair: TransferPair,
        payload: TransferCreate,
        base: str,
        *,
        changed_rates: set[str] | None = None,
    ) -> None:
        outgoing_account, incoming_account = self._accounts(user_id, payload)
        try:
            validate_transfer_amounts(
                Money(Decimal(payload.from_amount), Currency(outgoing_account.currency)),
                Money(Decimal(payload.to_amount), Currency(incoming_account.currency)),
            )
        except TransferAmountMismatchError as exc:
            raise AuthError(422, "transfer_amount_mismatch", str(exc)) from exc
        except InvalidTransferAmountError as exc:
            raise AuthError(422, "invalid_amount", str(exc)) from exc
        except InvalidExchangeRateError as exc:
            raise AuthError(422, "invalid_fx_rate", str(exc)) from exc
        for direction, row, account in (
            ("from", pair.outgoing, outgoing_account),
            ("to", pair.incoming, incoming_account),
        ):
            if (
                changed_rates is not None
                and row.currency != account.currency
                and f"{direction}_fx_rate_to_base" not in changed_rates
            ):
                raise AuthError(422, "invalid_fx_rate", "A changed currency requires its rate.")
            amount = Decimal(getattr(payload, f"{direction}_amount"))
            amount, rate = self.transactions._normalize(
                "expense" if direction == "from" else "income",
                -amount if direction == "from" else amount,
                account.currency,
                account.currency,
                base,
                Decimal(getattr(payload, f"{direction}_fx_rate_to_base")),
            )
            row.account_id, row.currency = account.id, account.currency
            row.amount, row.fx_rate_to_base = amount, rate
            row.fx_rate_source = payload.fx_rate_source
            row.occurred_at, row.title, row.note = payload.occurred_at, payload.title, payload.note
        self.db.add_all([pair.outgoing, pair.incoming])
        self.db.flush()

    def create(self, user_id: UUID, payload: TransferCreate) -> TransferPair:
        base = self.transactions._base_currency(user_id)
        group_id = uuid4()
        self._write_lock(user_id, group_id)
        pair = TransferPair(
            *(
                Transaction(
                    user_id=user_id,
                    kind="transfer",
                    transfer_group_id=group_id,
                    category_id=None,
                    status="posted",
                    source="web",
                )
                for _ in range(2)
            )
        )
        self._apply(user_id, pair, payload, base)
        return pair

    @staticmethod
    def payload(pair: TransferPair) -> TransferCreate:
        outgoing, incoming = pair.outgoing, pair.incoming
        return TransferCreate.model_validate(
            {
                "from_account_id": outgoing.account_id,
                "to_account_id": incoming.account_id,
                "from_amount": f"{-outgoing.amount:.2f}",
                "to_amount": f"{incoming.amount:.2f}",
                "from_fx_rate_to_base": f"{outgoing.fx_rate_to_base:.6f}",
                "to_fx_rate_to_base": f"{incoming.fx_rate_to_base:.6f}",
                "fx_rate_source": outgoing.fx_rate_source,
                "occurred_at": outgoing.occurred_at,
                "title": outgoing.title,
                "note": outgoing.note,
            }
        )

    def update(self, user_id: UUID, group_id: UUID, changes: TransferUpdate) -> TransferPair:
        base = self.transactions._base_currency(user_id)
        self._write_lock(user_id, group_id)
        pair = self.get(user_id, group_id)
        values = self.payload(pair).model_dump()
        values.update(changes.model_dump(exclude_unset=True))
        self._apply(
            user_id,
            pair,
            TransferCreate.model_validate(values),
            base,
            changed_rates=changes.model_fields_set,
        )
        return pair

    def delete(self, user_id: UUID, group_id: UUID) -> None:
        self._write_lock(user_id, group_id)
        pair = self.get(user_id, group_id)
        pair.outgoing.deleted_at = pair.incoming.deleted_at = datetime.now(UTC)
        self.db.flush()

    def restore(self, user_id: UUID, group_id: UUID) -> TransferPair:
        self._write_lock(user_id, group_id)
        pair = self.get(user_id, group_id, include_deleted=True)
        self._accounts(user_id, self.payload(pair), restoring=True)
        pair.outgoing.deleted_at = pair.incoming.deleted_at = None
        self.db.flush()
        return pair

    def list(
        self, user_id: UUID, limit: int, cursor: str | None
    ) -> tuple[list[TransferPair], str | None]:
        fingerprint = str(user_id)
        after = decode_cursor(cursor, "transfers", fingerprint, self.cursor_secret)
        outgoing, incoming = aliased(Transaction), aliased(Transaction)
        query = (
            select(outgoing, incoming)
            .join(
                incoming,
                (
                    (incoming.user_id == outgoing.user_id)
                    & (incoming.transfer_group_id == outgoing.transfer_group_id)
                    & (incoming.kind == "transfer")
                    & (incoming.amount > 0)
                    & incoming.deleted_at.is_(None)
                ),
            )
            .where(
                outgoing.user_id == user_id,
                outgoing.kind == "transfer",
                outgoing.amount < 0,
                outgoing.deleted_at.is_(None),
            )
        )
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
        page = [TransferPair(outgoing, incoming) for outgoing, incoming in rows[:limit]]
        next_cursor = (
            encode_cursor(
                "transfers",
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
