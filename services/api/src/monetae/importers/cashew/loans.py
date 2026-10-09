"""Conversión de préstamos según ADR-008 y resolución explícita de tasas J3."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from pydantic import JsonValue
from sqlalchemy import select, text

from monetae.db.models import ImportReviewItem, Loan, LoanMovement, Person, Transaction, User
from monetae.domain.currency import Currency
from monetae.domain.errors import DomainError
from monetae.domain.fx import ExchangeRate
from monetae.domain.loans import (
    ExcessCash,
    InvalidMovementError,
    Movement,
    MovementKind,
    OverpaymentError,
    Payment,
    account_amount_from_loan,
    loan_amount_from_account,
    plan_excess,
    replay,
    split_payment,
)
from monetae.domain.money import Money
from monetae.domain.subscriptions import normalize_title
from monetae.importers.cashew.mapping import TransactionPlan, external_id, map_transaction
from monetae.importers.cashew.reader import TransactionRow
from monetae.importers.cashew.report import ReviewItem

if TYPE_CHECKING:
    from monetae.importers.cashew.runner import ImportContext


@dataclass(frozen=True)
class Cash:
    source: TransactionRow
    amount: Decimal
    kind: str
    identity: str


@dataclass(frozen=True)
class PlannedMovement:
    movement: Movement
    cash: Cash | None = None
    fx_rate: Decimal | None = None


@dataclass
class LedgerPlan:
    identity: str
    name: str
    direction: str
    currency: str
    principal: Money
    rows: tuple[TransactionRow, ...]
    movements: list[PlannedMovement] = field(default_factory=list)
    cash: list[Cash] = field(default_factory=list)
    reviews: list[ReviewItem] = field(default_factory=list)


class AmbiguousLoan(ValueError):
    """Códigos seguros; detalles privados solo en el ítem de revisión."""

    def __init__(self, reason: str, candidates: list[JsonValue] | None = None) -> None:
        self.reason = reason
        self.candidates = candidates or []
        super().__init__(reason)


def _review(kind: str, identity: str, **payload: JsonValue) -> ReviewItem:
    key = "objective_pk" if ":objective:" in identity else "transaction_pk"
    return ReviewItem(
        kind=kind,
        payload={"loan_external_id": identity, key: identity.rsplit(":", 1)[-1], **payload},
    )


def _transaction_plan(ctx: ImportContext, cash: Cash) -> TransactionPlan:
    account = next(p for p in ctx.plan.accounts if p.source.pk == cash.source.wallet_pk)
    persisted = ctx.accounts[cash.source.wallet_pk]
    if persisted.deleted_at is not None or persisted.currency != account.currency:
        raise InvalidMovementError("account_unavailable")
    base = ctx.session.scalar(select(User.base_currency).where(User.id == ctx.user_id))
    assert base is not None
    mapped = replace(
        map_transaction(cash.source, account, base),
        amount=Money(cash.amount, Currency(account.currency)).amount,
        status="posted",
        category_pk=None
        if cash.kind == "loan" or cash.identity.endswith(":excess")
        else (cash.source.subcategory_pk or cash.source.category_pk),
    )
    if mapped.amount == 0:
        raise InvalidMovementError("zero_cash_amount")
    return mapped


def _mapped(ctx: ImportContext, cash: Cash) -> Transaction:
    return ctx.insert_transaction(
        _transaction_plan(ctx, cash), kind=cash.kind, external_id_override=cash.identity
    )


def _ordinary(ctx: ImportContext, rows: tuple[TransactionRow, ...]) -> None:
    for row in rows:
        if not row.paid:
            ctx.report.entity("transactions").skipped += 1
            ctx.skipped_pks.add(row.pk)
        elif row.amount == 0:
            ctx.report.entity("transactions").skipped += 1
            ctx.skipped_pks.add(row.pk)
            ctx.report.review_items.append(
                ReviewItem(kind="zero_amount_transaction", payload={"transaction_pk": row.pk})
            )
        else:
            try:
                _mapped(
                    ctx,
                    Cash(
                        row,
                        row.amount,
                        "income" if row.amount > 0 else "expense",
                        external_id(row.pk),
                    ),
                )
            except DomainError as exc:
                ctx.report.entity("transactions").skipped += 1
                ctx.skipped_pks.add(row.pk)
                ctx.report.review_items.append(
                    ReviewItem(
                        kind="ledger_invalid",
                        payload={"transaction_pk": row.pk, "reason": type(exc).__name__},
                    )
                )


def _append(
    plan: LedgerPlan,
    kind: MovementKind,
    amount: Money,
    source: TransactionRow,
    cash: Cash | None = None,
    rate: ExchangeRate | None = None,
) -> None:
    split = (
        split_payment(amount, replay(plan.principal, [p.movement for p in plan.movements]))
        if kind == MovementKind.PAYMENT
        else None
    )
    movement = Movement(
        kind,
        amount,
        source.occurred_at,
        len(plan.movements),
        split.interest_part if split else None,
        split.principal_part if split else None,
    )
    plan.movements.append(PlannedMovement(movement, cash, rate.rate if rate else None))
    if cash:
        plan.cash.append(cash)


def _payment(
    plan: LedgerPlan, row: TransactionRow, currency: str, rate_value: Decimal | None
) -> None:
    rate = (
        ExchangeRate(Currency(plan.currency), Currency(currency), rate_value)
        if currency != plan.currency and rate_value is not None
        else None
    )
    if currency != plan.currency and rate is None:
        plan.cash.append(
            Cash(row, row.amount, "income" if row.amount > 0 else "expense", external_id(row.pk))
        )
        plan.reviews.append(
            _review("fx_rate_required", plan.identity, transaction_pk=row.pk, currency=currency)
        )
        return
    amount = loan_amount_from_account(Money(abs(row.amount), Currency(currency)), rate)
    state = replay(plan.principal, [p.movement for p in plan.movements])
    try:
        split = split_payment(amount, state)
        operations: tuple[Payment | ExcessCash, ...] = (Payment(amount, split),)
    except OverpaymentError:
        # income_expense produce solo Payment/ExcessCash; nunca ajuste de capital.
        operations = tuple(
            op
            for op in plan_excess("income_expense", amount, state)
            if isinstance(op, Payment | ExcessCash)
        )
        plan.reviews.append(
            _review(
                "overpayment_detected",
                plan.identity,
                transaction_pk=row.pk,
                excess=str((amount - state.outstanding).amount),
            )
        )
    sign = Decimal(1) if row.amount > 0 else Decimal(-1)
    applied_cash = Decimal("0.00")
    for op in operations:
        if isinstance(op, Payment):
            applied_cash = (
                abs(row.amount)
                if len(operations) == 1
                else account_amount_from_loan(op.amount, rate).amount
            )
            if applied_cash <= 0 or applied_cash > abs(row.amount):
                raise InvalidMovementError("invalid_account_split")
            _append(
                plan,
                MovementKind.PAYMENT,
                op.amount,
                row,
                Cash(row, sign * applied_cash, "loan", external_id(row.pk)),
                rate,
            )
        else:
            extra = abs(row.amount) - applied_cash
            if extra <= 0:
                raise InvalidMovementError("excess_rounds_to_zero")
            plan.cash.append(
                Cash(
                    row,
                    sign * extra,
                    "income" if sign > 0 else "expense",
                    external_id(row.pk) + ":excess",
                )
            )


def _plan(
    ctx: ImportContext,
    identity: str,
    name: str,
    direction: str,
    wallet_pk: str,
    rows: tuple[TransactionRow, ...],
    *,
    single: bool = False,
    rates: dict[str, Decimal] | None = None,
) -> LedgerPlan:
    account = ctx.accounts.get(wallet_pk)
    if account is None:
        raise InvalidMovementError("objective_account_missing")
    ordered = tuple(sorted(rows, key=lambda r: (r.occurred_at, r.pk)))
    eligible = [r for r in ordered if single or r.paid]
    first = next((r for r in eligible if r.income == (direction == "borrowed")), None)
    if first is None:
        replay(Money(Decimal("0.01"), Currency(account.currency)), [])
        raise AssertionError("unreachable")
    principal = Money(abs(first.amount), Currency(account.currency))
    plan = LedgerPlan(identity, name, direction, account.currency, principal, ordered)
    selected_rates = ctx.options.loan_fx_rates if rates is None else rates
    for row in ordered:
        if not single and not row.paid:
            plan.reviews.append(_review("unpaid_loan_transaction", identity, transaction_pk=row.pk))
            continue
        if row.amount == 0 or (row.amount > 0) != row.income:
            raise InvalidMovementError("invalid_cash_polarity_or_amount")
        currency = ctx.accounts[row.wallet_pk].currency
        if row.income == (direction == "borrowed"):
            if currency != plan.currency:
                raise InvalidMovementError("disbursement_currency_mismatch")
            cash = Cash(row, row.amount, "loan", external_id(row.pk))
            if row.pk == first.pk:
                _append(plan, MovementKind.DISBURSEMENT, principal, row, cash)
            else:
                _append(
                    plan,
                    MovementKind.ADJUSTMENT,
                    Money(abs(row.amount), Currency(plan.currency)),
                    row,
                )
                plan.cash.append(cash)
                plan.reviews.append(_review("extra_disbursement", identity, transaction_pk=row.pk))
        else:
            _payment(plan, row, currency, selected_rates.get(row.pk))
    if single and not first.paid:
        synthetic = replace(
            first,
            occurred_at=first.modified_at or first.occurred_at,
            amount=-first.amount,
            income=not first.income,
            paid=True,
        )
        _append(
            plan,
            MovementKind.PAYMENT,
            principal,
            synthetic,
            Cash(
                synthetic, synthetic.amount, "loan", external_id(first.pk) + ":synthesized_payment"
            ),
        )
        plan.reviews.append(_review("synthesized_payment", identity, transaction_pk=first.pk))
    replay(principal, [p.movement for p in plan.movements])
    return plan


def _person(ctx: ImportContext, plan: LedgerPlan) -> Person:
    normalized = normalize_title(plan.name)
    if not normalized:
        raise AmbiguousLoan("empty_counterparty")
    people = list(ctx.session.scalars(select(Person).where(Person.user_id == ctx.user_id)))
    matches = [
        p
        for p in people
        if p.deleted_at is None and normalized in {normalize_title(s) for s in [p.name, *p.aliases]}
    ]
    if len(matches) > 1:
        raise AmbiguousLoan("multiple_counterparties", [str(p.id) for p in matches])
    if matches:
        return matches[0]
    identity = external_id("person:" + normalized)
    if any(p.import_external_id == identity for p in people):
        raise AmbiguousLoan("deleted_counterparty")
    person = Person(
        user_id=ctx.user_id,
        name=plan.name,
        aliases=[],
        note="Creada por la importación de Cashew; revisar",
        import_external_id=identity,
    )
    ctx.session.add(person)
    ctx.session.flush()
    ctx.report.entity("people").created += 1
    plan.reviews.append(_review("provisional_person", plan.identity, person_id=str(person.id)))
    return person


def _persist_movement(
    ctx: ImportContext, loan: Loan, planned: PlannedMovement, transaction: Transaction | None
) -> None:
    movement = planned.movement
    ctx.session.add(
        LoanMovement(
            user_id=ctx.user_id,
            loan_id=loan.id,
            kind=movement.kind.value,
            amount_in_loan_currency=movement.amount.amount,
            occurred_at=movement.occurred_at,
            sequence=movement.sequence,
            interest_part=movement.interest_part.amount if movement.interest_part else None,
            principal_part=movement.principal_part.amount if movement.principal_part else None,
            transaction_id=transaction.id if transaction else None,
            fx_rate_applied=planned.fx_rate,
            note=planned.cash.source.note if planned.cash else None,
        )
    )
    ctx.report.entity("loan_movements").created += 1
    ctx.report.entity("loan_movements_" + movement.kind.value).created += 1


def _create(ctx: ImportContext, plan: LedgerPlan) -> None:
    identities = [cash.identity for cash in plan.cash]
    if (
        identities
        and ctx.session.scalar(
            select(Transaction.id).where(
                Transaction.user_id == ctx.user_id, Transaction.import_external_id.in_(identities)
            )
        )
        is not None
    ):
        raise AmbiguousLoan("second_pass_conflict")
    for cash in plan.cash:
        _transaction_plan(ctx, cash)
    person = _person(ctx, plan)
    first = plan.movements[0].movement
    loan = Loan(
        user_id=ctx.user_id,
        person_id=person.id,
        direction=plan.direction,
        currency=plan.currency,
        principal=plan.principal.amount,
        opened_on=first.occurred_at.astimezone(ZoneInfo("America/Lima")).date(),
        import_external_id=plan.identity,
    )
    ctx.session.add(loan)
    ctx.session.flush()
    transactions = {cash.identity: _mapped(ctx, cash) for cash in plan.cash}
    for planned in plan.movements:
        _persist_movement(
            ctx, loan, planned, transactions[planned.cash.identity] if planned.cash else None
        )
    ctx.session.flush()
    ctx.report.review_items.extend(plan.reviews)
    ctx.report.entity("loans").created += 1


def _domain_movement(loan: Loan, row: LoanMovement) -> Movement:
    currency = Currency(loan.currency)
    return Movement(
        MovementKind(row.kind),
        Money(row.amount_in_loan_currency, currency),
        row.occurred_at,
        row.sequence,
        Money(row.interest_part, currency) if row.interest_part is not None else None,
        Money(row.principal_part, currency) if row.principal_part is not None else None,
    )


def _orphan_interest(ctx: ImportContext) -> None:
    names = {c.pk: normalize_title(c.name) for c in ctx.snapshot.categories}
    people = {
        p.id: {normalize_title(s) for s in [p.name, *p.aliases] if normalize_title(s)}
        for p in ctx.session.scalars(
            select(Person).where(Person.user_id == ctx.user_id, Person.deleted_at.is_(None))
        )
    }
    loans = list(
        ctx.session.scalars(
            select(Loan).where(Loan.user_id == ctx.user_id, Loan.deleted_at.is_(None))
        )
    )
    for row in ctx.snapshot.transactions:
        title, note = normalize_title(row.name), normalize_title(row.note or "")
        if row.objective_loan_pk is None and any(
            "interes" in value
            for value in (
                title,
                names.get(row.category_pk or "", ""),
                names.get(row.subcategory_pk or "", ""),
            )
        ):
            candidates: list[JsonValue] = [
                str(loan.id)
                for loan in loans
                if any(
                    value in title or value in note for value in people.get(loan.person_id, set())
                )
            ]
            ctx.report.review_items.append(
                ReviewItem(
                    kind="orphan_interest",
                    payload={"transaction_pk": row.pk, "candidates": candidates},
                )
            )


def _cash_rows(ctx: ImportContext, plan: LedgerPlan) -> dict[str, Transaction]:
    identities = [cash.identity for cash in plan.cash]
    return {
        row.import_external_id: row
        for row in ctx.session.scalars(
            select(Transaction).where(
                Transaction.user_id == ctx.user_id, Transaction.import_external_id.in_(identities)
            )
        )
        if row.import_external_id
    }


def _cash_matches(ctx: ImportContext, cash: Cash, transaction: Transaction) -> bool:
    mapped = _transaction_plan(ctx, cash)
    category = ctx.categories.get(mapped.category_pk or "")
    return (
        transaction.category_id == (category.id if category else None)
        and transaction.deleted_at is None
        and transaction.source == "import"
        and transaction.kind == cash.kind
        and transaction.status == "posted"
        and transaction.amount == Money(cash.amount, Currency(transaction.currency)).amount
        and transaction.account_id == ctx.accounts[cash.source.wallet_pk].id
        and transaction.currency == ctx.accounts[cash.source.wallet_pk].currency
        and transaction.occurred_at == cash.source.occurred_at
        and transaction.title == cash.source.name
        and transaction.note == cash.source.note
    )


def _movement_matches(
    loan: Loan,
    planned: PlannedMovement,
    stored: LoanMovement,
    transactions: dict[str, Transaction],
    *,
    sequence: bool = True,
) -> bool:
    original = _domain_movement(loan, stored)
    expected = planned.movement
    if not sequence:
        original = replace(original, sequence=expected.sequence)
    transaction = transactions.get(planned.cash.identity) if planned.cash else None
    return (
        original == expected
        and stored.fx_rate_applied == planned.fx_rate
        and stored.transaction_id == (transaction.id if transaction else None)
        and stored.note == (planned.cash.source.note if planned.cash else None)
    )


@dataclass(frozen=True)
class FxResolution:
    transactions: dict[str, Transaction]
    cash: list[Cash]
    movements: list[PlannedMovement]
    pending: list[ImportReviewItem]
    reviews: list[ReviewItem]
    resolved: int


def _verify_original(
    ctx: ImportContext,
    loan: Loan,
    name: str,
    direction: str,
    wallet_pk: str,
    rows: tuple[TransactionRow, ...],
    single: bool,
    stored: list[LoanMovement],
    prior_rates: dict[str, Decimal],
    supplied: dict[str, Decimal],
) -> tuple[LedgerPlan, dict[str, Transaction], list[ImportReviewItem]]:
    identity = loan.import_external_id or ""
    if loan.deleted_at is not None or any(r.deleted_at is not None for r in stored):
        raise AmbiguousLoan("second_pass_conflict")
    reviews = list(
        ctx.session.scalars(
            select(ImportReviewItem).where(
                ImportReviewItem.user_id == ctx.user_id,
                ImportReviewItem.kind == "fx_rate_required",
                ImportReviewItem.resolved_at.is_(None),
                ImportReviewItem.deleted_at.is_(None),
            )
        )
    )
    pending = [
        item
        for item in reviews
        if item.payload.get("loan_external_id") == identity
        and item.payload.get("transaction_pk") in supplied
    ]
    if any(
        not any(item.payload.get("transaction_pk") == pk for item in pending) for pk in supplied
    ):
        raise AmbiguousLoan("second_pass_conflict")
    baseline = _plan(
        ctx, identity, name, direction, wallet_pk, rows, single=single, rates=prior_rates
    )
    transactions = _cash_rows(ctx, baseline)
    if (
        loan.currency != baseline.currency
        or loan.direction != direction
        or loan.principal != baseline.principal.amount
        or loan.note is not None
        or loan.due_on is not None
        or loan.opened_on
        != baseline.movements[0].movement.occurred_at.astimezone(ZoneInfo("America/Lima")).date()
        or len(stored) != len(baseline.movements)
    ):
        raise AmbiguousLoan("second_pass_conflict")
    for planned, movement in zip(baseline.movements, stored, strict=True):
        if not _movement_matches(loan, planned, movement, transactions, sequence=False):
            raise AmbiguousLoan("second_pass_conflict")
    for cash in baseline.cash:
        transaction = transactions.get(cash.identity)
        if transaction is None or not _cash_matches(ctx, cash, transaction):
            raise AmbiguousLoan("second_pass_conflict")
    return baseline, transactions, pending


def _plan_conversions(
    ctx: ImportContext,
    loan: Loan,
    baseline: LedgerPlan,
    stored: list[LoanMovement],
    transactions: dict[str, Transaction],
    pending: list[ImportReviewItem],
    supplied: dict[str, Decimal],
) -> FxResolution:
    identity, name, direction, rows = (
        baseline.identity,
        baseline.name,
        baseline.direction,
        baseline.rows,
    )
    # El nuevo pago recibe MAX(sequence)+1, aun si su fecha es anterior.
    # Mantener todos los repartos y movimientos existentes intactos.
    all_movements = [_domain_movement(loan, row) for row in stored]
    new_movements: list[PlannedMovement] = []
    new_cash: list[Cash] = []
    new_reviews: list[ReviewItem] = []
    sequence = max((row.sequence for row in stored), default=-1) + 1
    for source in sorted(rows, key=lambda row: (row.occurred_at, row.pk)):
        if source.pk not in supplied:
            continue
        prefix = [
            m for m in all_movements if (m.occurred_at, m.sequence) < (source.occurred_at, sequence)
        ]
        candidate = LedgerPlan(
            identity, name, direction, loan.currency, baseline.principal, (source,)
        )
        candidate.movements = [PlannedMovement(m) for m in prefix]
        _payment(candidate, source, ctx.accounts[source.wallet_pk].currency, supplied[source.pk])
        added = candidate.movements[len(prefix) :]
        if not added:
            raise AmbiguousLoan("second_pass_conflict")
        for planned in added:
            planned = replace(planned, movement=replace(planned.movement, sequence=sequence))
            sequence += 1
            new_movements.append(planned)
            all_movements.append(planned.movement)
        new_cash.extend(candidate.cash)
        new_reviews.extend(candidate.reviews)
    replay(baseline.principal, all_movements)
    for cash in new_cash:
        if (
            cash.identity.endswith(":excess")
            and ctx.session.scalar(
                select(Transaction.id).where(
                    Transaction.user_id == ctx.user_id,
                    Transaction.import_external_id == cash.identity,
                )
            )
            is not None
        ):
            raise AmbiguousLoan("second_pass_conflict")
    for cash in new_cash:
        _transaction_plan(ctx, cash)
    return FxResolution(transactions, new_cash, new_movements, pending, new_reviews, len(supplied))


def _apply_fx(ctx: ImportContext, loan: Loan, resolution: FxResolution) -> int:
    transactions, new_cash, new_movements = (
        resolution.transactions,
        resolution.cash,
        resolution.movements,
    )
    pending, new_reviews = resolution.pending, resolution.reviews
    # Todo está validado antes de cambiar efectivo o insertar movimientos.
    for cash in new_cash:
        if cash.identity == external_id(cash.source.pk):
            transaction = transactions[cash.identity]
            transaction.kind, transaction.amount, transaction.category_id = (
                "loan",
                cash.amount,
                None,
            )
        else:
            transactions[cash.identity] = _mapped(ctx, cash)
    for planned in new_movements:
        assert planned.cash is not None
        _persist_movement(ctx, loan, planned, transactions[planned.cash.identity])
    for item in pending:
        item.resolved_at = datetime.now(UTC)
    ctx.report.review_items.extend(new_reviews)
    ctx.session.flush()
    return resolution.resolved


def _resolve_fx(
    ctx: ImportContext,
    loan: Loan,
    name: str,
    direction: str,
    wallet_pk: str,
    rows: tuple[TransactionRow, ...],
    single: bool,
) -> int:
    supplied = {
        r.pk: ctx.options.loan_fx_rates[r.pk]
        for r in rows
        if r.pk in ctx.options.loan_fx_rates and ctx.accounts[r.wallet_pk].currency != loan.currency
    }
    if not supplied:
        return 0
    ctx.session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"loan:{ctx.user_id}:{loan.id}"},
    )
    ctx.session.refresh(loan)
    stored = list(
        ctx.session.scalars(
            select(LoanMovement)
            .where(LoanMovement.user_id == ctx.user_id, LoanMovement.loan_id == loan.id)
            .order_by(LoanMovement.occurred_at, LoanMovement.sequence)
        )
    )
    transaction_ids = [r.transaction_id for r in stored if r.transaction_id]
    known = {
        row.id: row
        for row in ctx.session.scalars(
            select(Transaction).where(
                Transaction.user_id == ctx.user_id, Transaction.id.in_(transaction_ids)
            )
        )
    }
    prior_rates: dict[str, Decimal] = {}
    for movement in stored:
        transaction = known.get(movement.transaction_id) if movement.transaction_id else None
        if transaction and transaction.import_external_id and movement.fx_rate_applied is not None:
            prior_rates[transaction.import_external_id.removeprefix("cashew:sqlite:")] = (
                movement.fx_rate_applied
            )
    # Reimportar una tasa ya resuelta no cambia el historial.
    supplied = {pk: rate for pk, rate in supplied.items() if pk not in prior_rates}
    if not supplied:
        return 0
    identity = loan.import_external_id or ""
    try:
        baseline, transactions, pending = _verify_original(
            ctx, loan, name, direction, wallet_pk, rows, single, stored, prior_rates, supplied
        )
        resolution = _plan_conversions(ctx, loan, baseline, stored, transactions, pending, supplied)
    except (DomainError, AmbiguousLoan):
        ctx.report.review_items.append(
            _review("ambiguous_loan", identity, reason="second_pass_conflict")
        )
        return 0
    return _apply_fx(ctx, loan, resolution)


def run(ctx: ImportContext) -> dict[str, JsonValue]:
    before_reviews = len(ctx.report.review_items)
    invalid = resolved = 0
    grouped: dict[str, list[TransactionRow]] = {}
    singles: list[TransactionRow] = []
    for row in ctx.plan.deferred_loans:
        if row.objective_loan_pk is not None:
            grouped.setdefault(row.objective_loan_pk, []).append(row)
        else:
            singles.append(row)
    specs = [
        (
            external_id("objective:" + obj.pk),
            obj.name,
            "lent" if obj.income else "borrowed",
            obj.wallet_pk,
            tuple(grouped.pop(obj.pk, [])),
            False,
        )
        for obj in ctx.snapshot.objectives
        if obj.type == 1
    ]
    specs.extend(
        (
            external_id("tx:" + row.pk),
            row.name,
            "lent" if row.type == 3 else "borrowed",
            row.wallet_pk,
            (row,),
            True,
        )
        for row in singles
    )
    for identity, name, direction, wallet_pk, rows, single in specs:
        existing = ctx.session.scalar(
            select(Loan).where(Loan.user_id == ctx.user_id, Loan.import_external_id == identity)
        )
        if existing is not None:
            ctx.report.entity("loans").already_imported += 1
            resolved += _resolve_fx(ctx, existing, name, direction, wallet_pk, rows, single)
            continue
        try:
            plan = _plan(ctx, identity, name, direction, wallet_pk, rows, single=single)
            _create(ctx, plan)
            unpaid = [r.pk for r in rows if not r.paid] if not single else []
            ctx.report.entity("transactions").skipped += len(unpaid)
            ctx.skipped_pks.update(unpaid)
        except (DomainError, AmbiguousLoan) as exc:
            invalid += 1
            ctx.report.entity("loans").skipped += 1
            reason = (
                exc.reason
                if isinstance(exc, AmbiguousLoan)
                else str(exc)
                if isinstance(exc, InvalidMovementError)
                else type(exc).__name__
            )
            ctx.report.review_items.append(
                _review(
                    "ambiguous_loan" if isinstance(exc, AmbiguousLoan) else "ledger_invalid",
                    identity,
                    reason=reason,
                    **(
                        {"candidate_person_ids": exc.candidates}
                        if isinstance(exc, AmbiguousLoan) and exc.candidates
                        else {}
                    ),
                )
            )
            _ordinary(ctx, rows)
    for pk, orphan_rows in grouped.items():
        invalid += 1
        ctx.report.entity("loans").skipped += 1
        ctx.report.review_items.append(
            _review(
                "ledger_invalid",
                external_id("objective:" + pk),
                reason="objective_missing_or_not_loan",
            )
        )
        _ordinary(ctx, tuple(orphan_rows))
    _orphan_interest(ctx)
    reviews = Counter(item.kind for item in ctx.report.review_items[before_reviews:])
    counts = ctx.report.entity("loans")
    movements: dict[str, JsonValue] = {
        kind.value: ctx.report.entity("loan_movements_" + kind.value).created
        for kind in MovementKind
    }
    return {
        "created": counts.created,
        "already_imported": counts.already_imported,
        "invalid": invalid,
        "resolved_fx": resolved,
        "modified": resolved,
        "deferred": 0,
        "processed_transactions": len(ctx.plan.deferred_loans),
        "movements": movements,
        "review_items": dict(reviews),
    }
