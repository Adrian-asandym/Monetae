"""Libro mayor puro de préstamos, interés en base caja y planes de exceso."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, localcontext
from enum import StrEnum
from typing import Literal

from .errors import CurrencyMismatchError, DomainError
from .fx import ExchangeRate, convert, convert_back
from .money import Money, _context


class Direction(StrEnum):
    LENT = "lent"
    BORROWED = "borrowed"


class MovementKind(StrEnum):
    DISBURSEMENT = "disbursement"
    INTEREST = "interest"
    PAYMENT = "payment"
    ADJUSTMENT = "adjustment"
    WRITE_OFF = "write_off"


class InvalidMovementError(DomainError):
    """Importe, reparto, fecha o secuencia de movimiento inválidos."""


class InvalidSplitError(DomainError):
    """El reparto no suma el importe o supera un concepto pendiente."""


class InvalidAdjustmentError(DomainError):
    """El ajuste es cero o dejaría el capital pendiente negativo."""


class InvalidInterestError(DomainError):
    """La propuesta de interés tiene porcentaje o saldo inválido."""


class InvalidExcessHandlingError(DomainError):
    """El plan requiere una opción admitida y un exceso positivo."""


class InvalidDirectionError(DomainError):
    """El efecto en dinero requiere una dirección de préstamo válida."""


class OverpaymentError(DomainError):
    def __init__(self, excess: Money, outstanding: Money) -> None:
        self.excess = excess
        self.outstanding = outstanding
        super().__init__(
            f"Payment exceeds outstanding {outstanding.format()} "
            f"by {excess.format()} {excess.currency.code}"
        )


class LedgerError(DomainError):
    """Índice desde cero en orden de reproducción; sin desembolso usa len(ledger)."""

    def __init__(self, index: int, message: str) -> None:
        self.index = index
        super().__init__(f"Movement {index}: {message}")


class MissingDisbursementError(LedgerError):
    pass


class DuplicateDisbursementError(LedgerError):
    pass


class DisbursementMismatchError(LedgerError):
    pass


class LedgerMovementError(LedgerError):
    """La causa conserva el error de reparto/ajuste y sus detalles de dominio."""


class LedgerCurrencyMismatchError(LedgerError, CurrencyMismatchError):
    def __init__(self, index: int, error: CurrencyMismatchError) -> None:
        self.expected = error.expected
        self.actual = error.actual
        self.index = index
        # Se inicializa la base común: las firmas de los dos padres difieren.
        DomainError.__init__(self, f"Movement {index}: {error}")


def _same_currency(amount: Money, *others: Money) -> None:
    for other in others:
        if other.currency != amount.currency:
            raise CurrencyMismatchError(amount.currency, other.currency)


def _positive(amount: Money) -> None:
    if amount.amount <= 0:
        raise InvalidMovementError("Amount must be positive")


def _validate_parts(amount: Money, interest_part: Money, principal_part: Money) -> None:
    _same_currency(amount, interest_part, principal_part)
    if interest_part.is_negative() or principal_part.is_negative():
        raise InvalidSplitError("Interest and principal parts must be nonnegative")
    if interest_part + principal_part != amount:
        raise InvalidSplitError("Interest and principal parts must sum exactly to amount")


@dataclass(frozen=True, slots=True)
class Movement:
    """Efecto en moneda del préstamo; el llamador conserva las transacciones.

    sequence desempata fechas (incluye ajuste inmediatamente anterior al pago).
    La cuenta y la tasa histórica pertenecen a cada transacción correspondiente;
    este libro nunca deduce la cuenta de pago a partir del desembolso original.
    """

    kind: MovementKind
    amount: Money
    occurred_at: datetime
    sequence: int
    interest_part: Money | None = None
    principal_part: Money | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, MovementKind):
            raise InvalidMovementError("kind must be a MovementKind")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise InvalidMovementError("occurred_at must be timezone-aware")
        if (
            isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 0
        ):
            raise InvalidMovementError("sequence must be a nonnegative integer")
        if self.kind == MovementKind.ADJUSTMENT:
            if self.amount.is_zero():
                raise InvalidAdjustmentError("Adjustment must be nonzero")
        else:
            _positive(self.amount)
        if self.kind in {MovementKind.PAYMENT, MovementKind.WRITE_OFF}:
            if self.interest_part is None or self.principal_part is None:
                raise InvalidSplitError("Payment and write-off require both parts")
            _validate_parts(self.amount, self.interest_part, self.principal_part)
        elif self.interest_part is not None or self.principal_part is not None:
            raise InvalidSplitError("Only payment and write-off may have split parts")


@dataclass(frozen=True, slots=True)
class LoanBalance:
    principal: Money
    interest_total: Money
    adjustment_total: Money
    payment_total: Money
    write_off_total: Money
    interest_pending: Money
    principal_outstanding: Money
    outstanding: Money
    running: tuple[Money, ...]

    @property
    def status(self) -> Literal["open", "settled"]:
        return "settled" if self.outstanding.is_zero() else "open"


@dataclass(frozen=True, slots=True)
class PaymentSplit:
    interest_part: Money
    principal_part: Money


def validate_split(
    amount: Money, interest_part: Money, principal_part: Money, state: LoanBalance
) -> PaymentSplit:
    _same_currency(state.principal, amount, interest_part, principal_part)
    _positive(amount)
    _validate_parts(amount, interest_part, principal_part)
    if interest_part > state.interest_pending:
        raise InvalidSplitError(
            f"Interest part {interest_part.format()} exceeds pending "
            f"{state.interest_pending.format()}"
        )
    if principal_part > state.principal_outstanding:
        raise InvalidSplitError(
            f"Principal part {principal_part.format()} exceeds pending "
            f"{state.principal_outstanding.format()}"
        )
    return PaymentSplit(interest_part, principal_part)


def split_payment(amount: Money, state: LoanBalance) -> PaymentSplit:
    _same_currency(state.principal, amount)
    _positive(amount)
    if amount > state.outstanding:
        raise OverpaymentError(amount - state.outstanding, state.outstanding)
    interest_part = min(amount, state.interest_pending)
    return validate_split(amount, interest_part, amount - interest_part, state)


def split_write_off(amount: Money, state: LoanBalance) -> PaymentSplit:
    """Condona primero interés, sin dinero ni gasto/ingreso reconocido."""
    return split_payment(amount, state)


def validate_adjustment(amount: Money, state: LoanBalance) -> None:
    _same_currency(state.principal, amount)
    if amount.is_zero():
        raise InvalidAdjustmentError("Adjustment must be nonzero")
    if (state.principal_outstanding + amount).is_negative():
        raise InvalidAdjustmentError(
            f"Adjustment {amount.format()} exceeds pending principal "
            f"{state.principal_outstanding.format()}"
        )


def replay(principal: Money, movements: Iterable[Movement]) -> LoanBalance:
    """Reproduce repartos guardados, sin reasignar silenciosamente pagos editados."""
    _positive(principal)
    zero = Money(0, principal.currency)
    state = LoanBalance(principal, zero, zero, zero, zero, zero, principal, principal, ())
    ordered = sorted(movements, key=lambda movement: (movement.occurred_at, movement.sequence))
    running: list[Money] = []
    disbursed = False
    for index, movement in enumerate(ordered):
        try:
            _same_currency(principal, movement.amount)
            if movement.kind == MovementKind.DISBURSEMENT:
                if disbursed:
                    raise DuplicateDisbursementError(index, "Exactly one disbursement is allowed")
                if movement.amount != principal:
                    raise DisbursementMismatchError(
                        index,
                        f"Disbursement {movement.amount.format()} must equal principal "
                        f"{principal.format()} {principal.currency.code}",
                    )
                disbursed = True
            elif movement.kind == MovementKind.INTEREST:
                state = replace(
                    state,
                    interest_total=state.interest_total + movement.amount,
                    interest_pending=state.interest_pending + movement.amount,
                )
            elif movement.kind == MovementKind.ADJUSTMENT:
                validate_adjustment(movement.amount, state)
                state = replace(
                    state,
                    adjustment_total=state.adjustment_total + movement.amount,
                    principal_outstanding=state.principal_outstanding + movement.amount,
                )
            else:
                # Movement garantiza estos campos en payment/write_off al construirse.
                assert movement.interest_part is not None and movement.principal_part is not None
                validate_split(
                    movement.amount, movement.interest_part, movement.principal_part, state
                )
                state = replace(
                    state,
                    interest_pending=state.interest_pending - movement.interest_part,
                    principal_outstanding=state.principal_outstanding - movement.principal_part,
                    payment_total=state.payment_total
                    + (movement.amount if movement.kind == MovementKind.PAYMENT else zero),
                    write_off_total=state.write_off_total
                    + (movement.amount if movement.kind == MovementKind.WRITE_OFF else zero),
                )
            outstanding = state.interest_pending + state.principal_outstanding
            totals = (
                principal.amount,
                state.interest_total.amount,
                state.adjustment_total.amount,
                state.payment_total.amount,
                state.write_off_total.amount,
            )
            # Capital+interés acumulados pueden superar el límite de Money aunque
            # pagos anteriores dejen saldo válido. Se redondea solo el resultado.
            with localcontext(_context(*totals)):
                identity = Money(
                    totals[0] + totals[1] + totals[2] - totals[3] - totals[4], principal.currency
                )
            assert outstanding == identity, "Loan ledger balance identity violated"
            state = replace(state, outstanding=outstanding)
            running.append(outstanding)
        except LedgerError:
            raise
        except CurrencyMismatchError as error:
            raise LedgerCurrencyMismatchError(index, error) from error
        except DomainError as error:
            raise LedgerMovementError(index, str(error)) from error
    if not disbursed:
        raise MissingDisbursementError(len(ordered), "Exactly one disbursement is required")
    return replace(state, running=tuple(running))


@dataclass(frozen=True, slots=True)
class Adjustment:
    amount: Money


@dataclass(frozen=True, slots=True)
class Payment:
    amount: Money
    split: PaymentSplit


@dataclass(frozen=True, slots=True)
class ExcessCash:
    """Ingreso normal (lent) o gasto (borrowed), fuera del libro del préstamo."""

    amount: Money


def plan_excess(
    handling: str, amount: Money, state: LoanBalance
) -> tuple[Adjustment | Payment | ExcessCash, ...]:
    """Operaciones en orden de ejecución; el llamador las persiste atómicamente."""
    if handling not in {"adjustment", "income_expense"}:
        raise InvalidExcessHandlingError("handling must be adjustment or income_expense")
    _same_currency(state.principal, amount)
    _positive(amount)
    if amount <= state.outstanding:
        raise InvalidExcessHandlingError("Excess handling requires an amount above outstanding")
    excess = amount - state.outstanding
    if handling == "adjustment":
        adjusted = replace(
            state,
            adjustment_total=state.adjustment_total + excess,
            principal_outstanding=state.principal_outstanding + excess,
            outstanding=state.outstanding + excess,
        )
        return Adjustment(excess), Payment(amount, split_payment(amount, adjusted))
    # Un préstamo saldado no admite pago positivo: todo el dinero es exceso.
    if state.outstanding.is_zero():
        return (ExcessCash(excess),)
    return Payment(state.outstanding, split_payment(state.outstanding, state)), ExcessCash(excess)


def propose_interest(percentage: Decimal, outstanding: Money) -> Money:
    """Propone interés con un único redondeo HALF_UP al construir el dinero."""
    if not isinstance(percentage, Decimal) or not percentage.is_finite():
        raise InvalidInterestError("Percentage must be a finite Decimal")
    if percentage <= 0 or percentage > 1000:
        raise InvalidInterestError("Percentage must be greater than 0 and at most 1000")
    with localcontext(_context(percentage, outstanding.amount)):
        if percentage != percentage.quantize(Decimal("0.0001")):
            raise InvalidInterestError("Percentage must have at most four decimal places")
        if outstanding.is_negative():
            raise InvalidInterestError("Outstanding must be nonnegative")
        return Money(outstanding.amount * percentage / Decimal(100), outstanding.currency)


def loan_amount_from_account(account_money: Money, fx_rate_applied: ExchangeRate | None) -> Money:
    """Tasa en unidades de cuenta por unidad de préstamo; None = misma moneda."""
    if fx_rate_applied is None:
        return abs(account_money)
    return convert_back(abs(account_money), fx_rate_applied)


def account_amount_from_loan(loan_money: Money, fx_rate_applied: ExchangeRate | None) -> Money:
    if fx_rate_applied is None:
        return abs(loan_money)
    return convert(abs(loan_money), fx_rate_applied)


def _validate_direction(direction: Direction) -> None:
    if not isinstance(direction, Direction):
        raise InvalidDirectionError("direction must be a Direction")


def cash_sign(direction: Direction, kind: MovementKind) -> Literal[-1, 0, 1]:
    _validate_direction(direction)
    if not isinstance(kind, MovementKind):
        raise InvalidMovementError("kind must be a MovementKind")
    if kind == MovementKind.DISBURSEMENT:
        return -1 if direction == Direction.LENT else 1
    if kind == MovementKind.PAYMENT:
        return 1 if direction == Direction.LENT else -1
    return 0


@dataclass(frozen=True, slots=True)
class RecognizedInterest:
    amount: Money
    occurred_at: datetime
    side: Literal["income", "expense"]


def recognized_interest(
    direction: Direction, movements: Iterable[Movement]
) -> tuple[RecognizedInterest, ...]:
    """Proyecta pagos de un libro validado; nunca reconoce interés condonado."""
    _validate_direction(direction)
    result: list[RecognizedInterest] = []
    for movement in sorted(movements, key=lambda item: (item.occurred_at, item.sequence)):
        if movement.kind == MovementKind.PAYMENT:
            assert movement.interest_part is not None
            if not movement.interest_part.is_zero():
                result.append(
                    RecognizedInterest(
                        movement.interest_part,
                        movement.occurred_at,
                        "income" if direction == Direction.LENT else "expense",
                    )
                )
    return tuple(result)
