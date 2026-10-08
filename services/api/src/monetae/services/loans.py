"""Libro de préstamos: escritura atómica, serialización por préstamo y lecturas sin locks."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import case, func, select, text, tuple_
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Subquery

from monetae import domain
from monetae.api.pagination import decode_cursor, encode_cursor
from monetae.api.schemas import loans as schema
from monetae.db.models import Loan, LoanMovement, Person, Transaction
from monetae.db.repository import UserScopedRepository
from monetae.services.auth import AuthError
from monetae.services.transactions import TransactionService


class LoanError(AuthError):
    def __init__(self, status: int, code: str, detail: str, **extra: object) -> None:
        super().__init__(status, code, detail)
        self.extra = extra


def balances_query(user_id: UUID) -> Subquery:
    """Equivalente SQL de loan_balances, aislado antes de agregar."""
    signed = case(
        (LoanMovement.kind.in_(["interest", "adjustment"]), LoanMovement.amount_in_loan_currency),
        (LoanMovement.kind.in_(["payment", "write_off"]), -LoanMovement.amount_in_loan_currency),
        else_=0,
    )
    totals = (
        select(
            LoanMovement.loan_id.label("loan_id"),
            func.sum(signed).label("delta"),
            *[
                func.sum(
                    case((LoanMovement.kind == kind, LoanMovement.amount_in_loan_currency), else_=0)
                ).label(f"{kind}_total")
                for kind in ("interest", "adjustment", "payment", "write_off")
            ],
        )
        .where(LoanMovement.user_id == user_id, LoanMovement.deleted_at.is_(None))
        .group_by(LoanMovement.loan_id)
        .subquery()
    )
    outstanding = Loan.principal + func.coalesce(totals.c.delta, 0)
    return (
        select(
            Loan.id.label("loan_id"),
            Loan.person_id,
            Loan.currency,
            Loan.direction,
            Loan.principal,
            Loan.deleted_at,
            outstanding.label("outstanding"),
            case((outstanding == 0, "settled"), else_="open").label("status"),
            *[
                func.coalesce(totals.c[f"{kind}_total"], 0).label(f"{kind}_total")
                for kind in ("interest", "adjustment", "payment", "write_off")
            ],
        )
        .outerjoin(totals, totals.c.loan_id == Loan.id)
        .where(Loan.user_id == user_id)
        .subquery()
    )


class LoanService:
    def __init__(self, db: Session, cursor_secret: str) -> None:
        self.db = db
        self.cursor_secret = cursor_secret
        self.transactions = TransactionService(db, cursor_secret)

    def get(self, user_id: UUID, loan_id: UUID, *, include_deleted: bool = False) -> Loan:
        row = UserScopedRepository(self.db, Loan, user_id).get(
            loan_id, include_deleted=include_deleted
        )
        if row is None:
            raise AuthError(404, "not_found", "Loan not found.")
        return row

    def _advisory_lock(self, user_id: UUID, loan_id: UUID) -> None:
        self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"loan:{user_id}:{loan_id}"},
        )

    def lock(self, user_id: UUID, loan_id: UUID, *, include_deleted: bool = False) -> Loan:
        self._advisory_lock(user_id, loan_id)
        self.db.expire_all()
        return self.get(user_id, loan_id, include_deleted=include_deleted)

    def person(self, user_id: UUID, person_id: UUID, *, restoring: bool = False) -> None:
        row = self.db.scalar(
            select(Person)
            .where(Person.user_id == user_id, Person.id == person_id)
            .with_for_update(read=True)
        )
        if row is None or row.deleted_at is not None:
            raise AuthError(
                409 if restoring else 404,
                "restore_conflict" if restoring else "not_found",
                "Restore the person first." if restoring else "Person not found.",
            )

    def rows(self, loan: Loan, *, include_deleted: bool = False) -> list[LoanMovement]:
        query = select(LoanMovement).where(
            LoanMovement.user_id == loan.user_id, LoanMovement.loan_id == loan.id
        )
        if not include_deleted:
            query = query.where(LoanMovement.deleted_at.is_(None))
        return list(
            self.db.scalars(query.order_by(LoanMovement.occurred_at, LoanMovement.sequence))
        )

    @staticmethod
    def money(loan: Loan, amount: Decimal | str) -> domain.Money:
        return domain.Money(Decimal(amount), domain.Currency(loan.currency))

    def movement(self, loan: Loan, row: LoanMovement) -> domain.Movement:
        return domain.Movement(
            domain.MovementKind(row.kind),
            self.money(loan, row.amount_in_loan_currency),
            row.occurred_at,
            row.sequence,
            self.money(loan, row.interest_part) if row.interest_part is not None else None,
            self.money(loan, row.principal_part) if row.principal_part is not None else None,
        )

    def replay(self, loan: Loan, rows: list[LoanMovement] | None = None) -> domain.LoanBalance:
        try:
            return domain.replay(
                self.money(loan, loan.principal),
                [self.movement(loan, row) for row in (self.rows(loan) if rows is None else rows)],
            )
        except domain.LedgerError as exc:
            raise LoanError(409, "ledger_inconsistent", str(exc), movement_index=exc.index) from exc
        except domain.DomainError as exc:
            raise AuthError(422, "invalid_movement", str(exc)) from exc

    def balance(self, loan: Loan) -> schema.LoanBalance:
        q = balances_query(loan.user_id)
        row = self.db.execute(select(q).where(q.c.loan_id == loan.id)).mappings().one()
        return schema.LoanBalance.model_validate(
            {
                "loan_id": loan.id,
                "currency": loan.currency,
                **{
                    key: f"{row[key]:.2f}"
                    for key in (
                        "principal",
                        "interest_total",
                        "adjustment_total",
                        "payment_total",
                        "write_off_total",
                        "outstanding",
                    )
                },
                "status": row["status"],
            }
        )

    def serialize(self, loan: Loan, *, outstanding: Decimal | None = None) -> schema.Loan:
        balance = self.balance(loan) if outstanding is None else None
        values = {
            name: getattr(loan, name)
            for name in schema.Loan.model_fields
            if name not in {"status", "outstanding", "principal"}
        }
        values.update(
            principal=f"{loan.principal:.2f}",
            outstanding=balance.outstanding if balance else f"{outstanding:.2f}",
            status=balance.status if balance else ("settled" if outstanding == 0 else "open"),
        )
        return schema.Loan.model_validate(values)

    def create(self, user_id: UUID, payload: schema.LoanCreate) -> Loan:
        loan_id = uuid4()
        self._advisory_lock(user_id, loan_id)
        self.person(user_id, payload.person_id)
        row = UserScopedRepository(self.db, Loan, user_id).add(
            Loan(
                id=loan_id,
                user_id=user_id,
                **payload.model_dump(exclude={"disbursement", "principal"}),
                principal=Decimal(payload.principal),
            )
        )
        self._insert(row, payload.disbursement)
        self.replay(row)
        return row

    def update(self, user_id: UUID, loan_id: UUID, payload: schema.LoanUpdate) -> Loan:
        loan = self.lock(user_id, loan_id)
        if payload.person_id is not None:
            self.person(user_id, payload.person_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(loan, key, value)
        self.db.flush()
        return loan

    def _transaction(self, loan: Loan, row: LoanMovement) -> Transaction | None:
        if row.transaction_id is None:
            return None
        return self.transactions.get(loan.user_id, row.transaction_id, include_deleted=True)

    def _cash(
        self,
        loan: Loan,
        payload: schema.CashRequest,
        kind: str,
        amount: Decimal,
        existing: Transaction | None = None,
    ) -> Transaction:
        account = self.transactions._references(loan.user_id, payload.account_id, None)
        base = self.transactions._base_currency(loan.user_id)
        normalized, rate = self.transactions._normalize(
            "income" if amount > 0 else "expense",
            amount,
            payload.account_currency,
            account.currency,
            base,
            Decimal(payload.fx_rate_to_base),
        )
        row = existing or Transaction(user_id=loan.user_id)
        row.account_id, row.currency, row.kind = account.id, account.currency, kind
        row.amount, row.fx_rate_to_base = normalized, rate
        row.occurred_at, row.note = payload.occurred_at, payload.note
        row.status, row.source, row.fx_rate_source = "posted", "web", payload.fx_rate_source
        row.category_id = None
        row.title = (
            "Desembolso de préstamo"
            if isinstance(payload, schema.DisbursementRequest)
            else "Pago de préstamo"
        )
        self.db.add(row)
        self.db.flush()
        return row

    def _fx(self, loan: Loan, payload: schema.CashRequest) -> domain.ExchangeRate | None:
        if payload.account_currency == loan.currency:
            if payload.fx_rate_applied is not None:
                raise AuthError(
                    422, "invalid_fx_rate", "Same-currency movements require a null applied rate."
                )
            rate = None
        else:
            if payload.fx_rate_applied is None:
                raise AuthError(
                    422, "invalid_fx_rate", "A cross-currency movement requires an applied rate."
                )
            rate = domain.ExchangeRate(
                domain.Currency(loan.currency),
                domain.Currency(payload.account_currency),
                Decimal(payload.fx_rate_applied),
            )
        converted = domain.loan_amount_from_account(
            domain.Money(
                Decimal(payload.account_amount), domain.Currency(payload.account_currency)
            ),
            rate,
        )
        if converted != self.money(loan, payload.amount_in_loan_currency):
            raise AuthError(
                422, "invalid_amount", "Account amount and applied loan amount do not match."
            )
        return rate

    def _sequence(self, loan: Loan) -> int:
        maximum = self.db.scalar(
            select(func.max(LoanMovement.sequence)).where(
                LoanMovement.user_id == loan.user_id, LoanMovement.loan_id == loan.id
            )
        )
        return int(maximum or 0) + 1

    def _prefix(
        self,
        loan: Loan,
        payload: schema.MovementCreate,
        sequence: int,
        excluded: UUID | None = None,
    ) -> domain.LoanBalance:
        rows = [
            row
            for row in self.rows(loan)
            if row.id != excluded
            and (row.occurred_at, row.sequence) < (payload.occurred_at, sequence)
        ]
        return self.replay(loan, rows)

    def _fill(
        self,
        loan: Loan,
        row: LoanMovement,
        payload: schema.MovementCreate,
        *,
        cash_amount: Decimal | None = None,
    ) -> None:
        interest_part = principal_part = None
        transaction_id = fx_rate = None
        if isinstance(payload, (schema.PaymentRequest, schema.WriteOffRequest)):
            state = self._prefix(loan, payload, row.sequence, row.id)
            if payload.interest_part is None:
                split = domain.split_payment(
                    self.money(loan, payload.amount_in_loan_currency), state
                )
            else:
                assert payload.principal_part is not None
                split = domain.validate_split(
                    self.money(loan, payload.amount_in_loan_currency),
                    self.money(loan, payload.interest_part),
                    self.money(loan, payload.principal_part),
                    state,
                )
            interest_part, principal_part = split.interest_part.amount, split.principal_part.amount
        if isinstance(payload, schema.CashRequest):
            if cash_amount is None:
                self._fx(loan, payload)
            sign = domain.cash_sign(
                domain.Direction(loan.direction), domain.MovementKind(payload.kind)
            )
            txn = self._cash(
                loan,
                payload,
                "loan",
                sign
                * (cash_amount if cash_amount is not None else Decimal(payload.account_amount)),
                self._transaction(loan, row),
            )
            transaction_id = txn.id
            fx_rate = (
                Decimal(payload.fx_rate_applied) if payload.fx_rate_applied is not None else None
            )
        row.kind, row.amount_in_loan_currency = (
            payload.kind,
            Decimal(payload.amount_in_loan_currency),
        )
        row.occurred_at, row.note = payload.occurred_at, payload.note
        row.interest_part, row.principal_part = interest_part, principal_part
        row.transaction_id, row.fx_rate_applied = transaction_id, fx_rate

    def _insert(
        self, loan: Loan, payload: schema.MovementCreate, *, cash_amount: Decimal | None = None
    ) -> LoanMovement:
        row = LoanMovement(user_id=loan.user_id, loan_id=loan.id, sequence=self._sequence(loan))
        try:
            self._fill(loan, row, payload, cash_amount=cash_amount)
            self.movement(loan, row)
        except domain.OverpaymentError as exc:
            raise self.overpayment(exc) from exc
        except domain.DomainError as exc:
            raise AuthError(422, "invalid_movement", str(exc)) from exc
        self.db.add(row)
        self.db.flush()
        return row

    @staticmethod
    def overpayment(exc: domain.OverpaymentError) -> LoanError:
        return LoanError(
            422,
            "loan_overpayment",
            "El pago supera el saldo; elige cómo registrar el exceso.",
            excess_amount=exc.excess.format(),
            currency=exc.excess.currency.code,
            outstanding=exc.outstanding.format(),
            options=[
                {
                    "action": "adjustment",
                    "description": "Crear ajuste y aplicar el pago completo.",
                    "applied_amount": (exc.outstanding + exc.excess).format(),
                },
                {
                    "action": "income_expense",
                    "description": "Aplicar saldo y registrar el exceso como ingreso/gasto.",
                    "applied_amount": exc.outstanding.format(),
                },
            ],
        )

    def add_movement(
        self, user_id: UUID, loan_id: UUID, payload: schema.MovementCreate
    ) -> schema.LoanMovement:
        loan = self.lock(user_id, loan_id)
        if payload.kind == "disbursement":
            raise AuthError(409, "disbursement_exists", "Edit the existing disbursement.")
        effects: list[schema.LoanSideEffect] = []
        cash_amount = None
        if isinstance(payload, schema.PaymentRequest):
            rate = self._fx(loan, payload)
            state = self._prefix(loan, payload, self._sequence(loan))
            amount = self.money(loan, payload.amount_in_loan_currency)
            if amount > state.outstanding:
                if payload.excess_handling is None:
                    raise self.overpayment(
                        domain.OverpaymentError(amount - state.outstanding, state.outstanding)
                    )
                if state.outstanding.is_zero() and payload.excess_handling == "income_expense":
                    raise AuthError(
                        409,
                        "loan_already_settled",
                        (
                            "El préstamo ya está saldado: usa excess_handling=adjustment para "
                            "reabrirlo y pagar, o registra un ingreso/gasto normal "
                            "en /transactions."
                        ),
                    )
                operations = domain.plan_excess(payload.excess_handling, amount, state)
                for operation in operations:
                    if isinstance(operation, domain.Adjustment):
                        adjustment = self._insert(
                            loan,
                            schema.AdjustmentRequest(
                                kind="adjustment",
                                amount_in_loan_currency=operation.amount.format(),
                                occurred_at=payload.occurred_at,
                                note=payload.note,
                            ),
                        )
                        effects.append(
                            schema.LoanSideEffect.model_validate(
                                dict(
                                    kind="adjustment",
                                    transaction_id=None,
                                    account_id=None,
                                    amount=operation.amount.format(),
                                    currency=loan.currency,
                                    adjustment_id=adjustment.id,
                                )
                            )
                        )
                    elif isinstance(operation, domain.Payment):
                        applied = operation.amount
                    else:
                        cash_amount = domain.account_amount_from_loan(applied, rate).amount
                        extra = Decimal(payload.account_amount) - cash_amount
                        if extra <= 0:
                            raise AuthError(
                                422,
                                "invalid_amount",
                                "The excess rounds to zero in the account currency.",
                            )
                        kind = "income" if loan.direction == "lent" else "expense"
                        txn = self._cash(loan, payload, kind, extra if kind == "income" else -extra)
                        effects.append(
                            schema.LoanSideEffect.model_validate(
                                dict(
                                    kind=kind,
                                    transaction_id=txn.id,
                                    account_id=txn.account_id,
                                    amount=f"{extra:.2f}",
                                    currency=txn.currency,
                                    adjustment_id=None,
                                )
                            )
                        )
                if payload.excess_handling == "income_expense":
                    payload = payload.model_copy(
                        update={
                            "amount_in_loan_currency": applied.format(),
                            "account_amount": f"{cash_amount:.2f}",
                        }
                    )
            elif payload.excess_handling is not None:
                raise AuthError(
                    422, "invalid_excess_handling", "Excess handling requires an overpayment."
                )
        row = self._insert(loan, payload, cash_amount=cash_amount)
        self.replay(loan)
        return self.serialize_movements(loan, [row], effects)[0]

    def get_movement(
        self, loan: Loan, movement_id: UUID, *, include_deleted: bool = False
    ) -> LoanMovement:
        row = UserScopedRepository(self.db, LoanMovement, loan.user_id).get(
            movement_id, include_deleted=include_deleted
        )
        if row is None or row.loan_id != loan.id:
            raise AuthError(404, "not_found", "Movement not found.")
        return row

    def update_movement(
        self, user_id: UUID, loan_id: UUID, movement_id: UUID, payload: schema.MovementCreate
    ) -> schema.LoanMovement:
        loan = self.lock(user_id, loan_id)
        row = self.get_movement(loan, movement_id)
        if payload.kind != row.kind:
            raise AuthError(422, "movement_kind_immutable", "A movement's kind cannot change.")
        if isinstance(payload, schema.PaymentRequest) and payload.excess_handling is not None:
            raise AuthError(
                422,
                "invalid_excess_handling",
                "Excess handling is only available when creating a payment.",
            )
        if row.kind == "disbursement":
            loan.principal = Decimal(payload.amount_in_loan_currency)
        try:
            self._fill(loan, row, payload)
            self.replay(loan)
        except domain.DomainError as exc:
            ordered = sorted(self.rows(loan), key=lambda item: (item.occurred_at, item.sequence))
            raise LoanError(
                409, "ledger_inconsistent", str(exc), movement_index=ordered.index(row)
            ) from exc
        self.db.flush()
        return self.serialize_movements(loan, [row])[0]

    def toggle_movement(
        self, user_id: UUID, loan_id: UUID, movement_id: UUID, *, restore: bool
    ) -> LoanMovement:
        loan = self.lock(user_id, loan_id)
        row = self.get_movement(loan, movement_id, include_deleted=restore)
        if row.kind == "disbursement" and not restore:
            raise AuthError(
                409, "disbursement_required", "The disbursement cannot be deleted independently."
            )
        txn = self._transaction(loan, row)
        if restore and txn is not None:
            self.transactions._references(user_id, txn.account_id, None, restoring=True)
        row.deleted_at = None if restore else datetime.now(UTC)
        if txn is not None:
            txn.deleted_at = row.deleted_at
        self.db.flush()
        self.replay(loan)
        return row

    def toggle_loan(self, user_id: UUID, loan_id: UUID, *, restore: bool) -> Loan:
        loan = self.lock(user_id, loan_id, include_deleted=restore)
        marker = loan.deleted_at
        if restore and marker is None:
            return loan
        if restore:
            self.person(user_id, loan.person_id, restoring=True)
        rows = [row for row in self.rows(loan, include_deleted=True) if row.deleted_at == marker]
        txns = [txn for row in rows if (txn := self._transaction(loan, row)) is not None]
        if restore:
            for account_id in sorted({txn.account_id for txn in txns}):
                self.transactions._references(user_id, account_id, None, restoring=True)
        now = None if restore else datetime.now(UTC)
        loan.deleted_at = now
        for row in rows:
            row.deleted_at = now
        for txn in txns:
            txn.deleted_at = now
        self.db.flush()
        if restore:
            self.replay(loan)
        return loan

    def serialize_movements(
        self,
        loan: Loan,
        rows: list[LoanMovement],
        effects: list[schema.LoanSideEffect] | None = None,
    ) -> list[schema.LoanMovement]:
        ledger = self.rows(loan, include_deleted=True)
        running: dict[UUID, str] = {}
        balance = loan.principal
        for row in ledger:
            if row.deleted_at is None:
                if row.kind in {"interest", "adjustment"}:
                    balance += row.amount_in_loan_currency
                elif row.kind in {"payment", "write_off"}:
                    balance -= row.amount_in_loan_currency
            running[row.id] = f"{balance:.2f}"
        ids = [row.transaction_id for row in rows if row.transaction_id is not None]
        txns = {
            row.id: row
            for row in self.db.scalars(
                select(Transaction).where(
                    Transaction.user_id == loan.user_id, Transaction.id.in_(ids)
                )
            )
        }
        result = []
        for row in rows:
            txn = txns.get(row.transaction_id) if row.transaction_id else None
            values = {
                name: getattr(row, name)
                for name in (
                    "kind",
                    "occurred_at",
                    "note",
                    "id",
                    "created_at",
                    "updated_at",
                    "deleted_at",
                    "loan_id",
                    "transaction_id",
                )
            }
            values.update(
                amount_in_loan_currency=f"{row.amount_in_loan_currency:.2f}",
                interest_part=f"{row.interest_part:.2f}" if row.interest_part is not None else None,
                principal_part=f"{row.principal_part:.2f}"
                if row.principal_part is not None
                else None,
                fx_rate_applied=f"{row.fx_rate_applied:.6f}"
                if row.fx_rate_applied is not None
                else None,
                account_id=txn.account_id if txn else None,
                account_amount=f"{abs(txn.amount):.2f}" if txn else None,
                account_currency=txn.currency if txn else None,
                fx_rate_to_base=f"{txn.fx_rate_to_base:.6f}" if txn else None,
                fx_rate_source=txn.fx_rate_source if txn else None,
                running_balance=running[row.id],
                side_effects=effects or [],
            )
            result.append(schema.LoanMovement.model_validate(values))
        return result

    def _cursor(
        self, cursor: str | None, resource: str, fingerprint: str, size: int
    ) -> list[str] | None:
        key = decode_cursor(cursor, resource, fingerprint, self.cursor_secret)
        if key is not None and len(key) != size:
            raise AuthError(400, "invalid_cursor", "The pagination cursor is invalid.")
        return key

    def list(
        self,
        user_id: UUID,
        person_id: UUID | None,
        currency: str | None,
        status: str | None,
        include_deleted: bool,
        limit: int,
        cursor: str | None,
    ) -> schema.LoanPage:
        fingerprint = json.dumps([str(user_id), str(person_id), currency, status, include_deleted])
        key = self._cursor(cursor, "loans", fingerprint, 1)
        q = balances_query(user_id)
        query = (
            select(Loan, cast(ColumnElement[Decimal], q.c.outstanding))
            .join(q, q.c.loan_id == Loan.id)
            .where(Loan.user_id == user_id)
        )
        if not include_deleted:
            query = query.where(Loan.deleted_at.is_(None))
        for column, value in (
            (Loan.person_id, person_id),
            (Loan.currency, currency),
            (q.c.status, status),
        ):
            if value is not None:
                query = query.where(column == value)
        if key:
            try:
                query = query.where(Loan.id > UUID(key[0]))
            except ValueError as exc:
                raise AuthError(400, "invalid_cursor", "Invalid loan cursor.") from exc
        rows = self.db.execute(query.order_by(Loan.id).limit(limit + 1)).all()
        page = rows[:limit]
        next_cursor = (
            encode_cursor("loans", fingerprint, [str(page[-1][0].id)], self.cursor_secret)
            if len(rows) > limit
            else None
        )
        return schema.LoanPage(
            items=[self.serialize(row, outstanding=amount) for row, amount in page],
            next_cursor=next_cursor,
        )

    def list_movements(
        self, loan: Loan, include_deleted: bool, limit: int, cursor: str | None
    ) -> schema.LoanMovementPage:
        fingerprint = json.dumps([str(loan.user_id), str(loan.id), include_deleted])
        key = self._cursor(cursor, "loan_movements", fingerprint, 2)
        query = select(LoanMovement).where(
            LoanMovement.user_id == loan.user_id, LoanMovement.loan_id == loan.id
        )
        if not include_deleted:
            query = query.where(LoanMovement.deleted_at.is_(None))
        if key:
            try:
                timestamp, sequence = datetime.fromisoformat(key[0]), int(key[1])
                if timestamp.tzinfo is None:
                    raise ValueError
                query = query.where(
                    tuple_(LoanMovement.occurred_at, LoanMovement.sequence)
                    > tuple_(timestamp, sequence)
                )
            except ValueError as exc:
                raise AuthError(400, "invalid_cursor", "Invalid movement cursor.") from exc
        rows = list(
            self.db.scalars(
                query.order_by(LoanMovement.occurred_at, LoanMovement.sequence).limit(limit + 1)
            )
        )
        page = rows[:limit]
        next_cursor = (
            encode_cursor(
                "loan_movements",
                fingerprint,
                [page[-1].occurred_at.isoformat(), str(page[-1].sequence)],
                self.cursor_secret,
            )
            if len(rows) > limit
            else None
        )
        return schema.LoanMovementPage(
            items=self.serialize_movements(loan, page), next_cursor=next_cursor
        )

    def summary(
        self,
        user_id: UUID,
        person_id: UUID | None,
        currency: str | None,
        limit: int,
        cursor: str | None,
    ) -> schema.LoanSummaryPage:
        fingerprint = json.dumps([str(user_id), str(person_id), currency])
        key = self._cursor(cursor, "loan_summary", fingerprint, 2)
        q = balances_query(user_id)
        query = select(
            q.c.person_id,
            q.c.currency,
            func.sum(case((q.c.direction == "lent", q.c.outstanding), else_=0)).label(
                "lent_outstanding"
            ),
            func.sum(case((q.c.direction == "borrowed", q.c.outstanding), else_=0)).label(
                "borrowed_outstanding"
            ),
            func.count().filter(q.c.outstanding != 0).label("open_count"),
            func.count().filter(q.c.outstanding == 0).label("settled_count"),
        ).where(q.c.deleted_at.is_(None))
        if person_id is not None:
            query = query.where(q.c.person_id == person_id)
        if currency is not None:
            query = query.where(q.c.currency == currency)
        if key:
            try:
                query = query.where(
                    tuple_(q.c.person_id, q.c.currency) > tuple_(UUID(key[0]), key[1])
                )
            except ValueError as exc:
                raise AuthError(400, "invalid_cursor", "Invalid summary cursor.") from exc
        rows = (
            self.db.execute(
                query.group_by(q.c.person_id, q.c.currency)
                .order_by(q.c.person_id, q.c.currency)
                .limit(limit + 1)
            )
            .mappings()
            .all()
        )
        page = rows[:limit]
        next_cursor = (
            encode_cursor(
                "loan_summary",
                fingerprint,
                [str(page[-1]["person_id"]), page[-1]["currency"]],
                self.cursor_secret,
            )
            if len(rows) > limit
            else None
        )
        items = [
            schema.LoanSummary.model_validate(
                {
                    **row,
                    "lent_outstanding": f"{row['lent_outstanding']:.2f}",
                    "borrowed_outstanding": f"{row['borrowed_outstanding']:.2f}",
                }
            )
            for row in page
        ]
        return schema.LoanSummaryPage(items=items, next_cursor=next_cursor)

    def payment_proposal(
        self, loan: Loan, payload: schema.PaymentProposalRequest
    ) -> schema.PaymentProposal:
        state = self.replay(loan)
        try:
            split = domain.split_payment(self.money(loan, payload.amount_in_loan_currency), state)
        except domain.OverpaymentError as exc:
            raise self.overpayment(exc) from exc
        return schema.PaymentProposal(
            amount_in_loan_currency=payload.amount_in_loan_currency,
            interest_part=split.interest_part.format(),
            principal_part=split.principal_part.format(),
            outstanding=state.outstanding.format(),
        )

    def interest_proposal(
        self, loan: Loan, payload: schema.InterestProposalRequest
    ) -> schema.InterestProposal:
        state = self.replay(loan)
        try:
            amount = domain.propose_interest(Decimal(payload.percentage), state.outstanding)
        except domain.DomainError as exc:
            raise AuthError(422, "invalid_interest", str(exc)) from exc
        return schema.InterestProposal.model_validate(
            dict(
                percentage=payload.percentage,
                outstanding=state.outstanding.format(),
                amount_in_loan_currency=amount.format(),
                currency=loan.currency,
            )
        )
