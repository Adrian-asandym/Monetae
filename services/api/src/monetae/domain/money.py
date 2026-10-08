"""Dinero inmutable con redondeo explícito y límites NUMERIC(18,2)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Context, Decimal, DecimalException, localcontext

from .currency import Currency
from .errors import CurrencyMismatchError, InvalidMoneyError

_CENT = Decimal("0.01")
_LIMIT = Decimal("10000000000000000")


def _decimal(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal | int):
        raise InvalidMoneyError("Only Decimal and int are accepted; use Money.parse for strings")
    result = Decimal(value)
    if not result.is_finite():
        raise InvalidMoneyError("Value must be finite")
    return result


def _context(*values: Decimal) -> Context:
    # Cubre coeficientes y escalas completos: productos/sumas exactos y margen
    # para dividir antes del único redondeo a la escala de persistencia.
    precision = 40 + sum(
        len(value.as_tuple().digits) + abs(int(value.as_tuple().exponent)) for value in values
    )
    return Context(prec=precision, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True, init=False)
class Money:
    """Importe y moneda; negativos permitidos, sin coerción desde float/bool."""

    amount: Decimal
    currency: Currency

    def __init__(self, amount: Decimal | int, currency: Currency) -> None:
        value = _decimal(amount)
        if not isinstance(currency, Currency):
            raise InvalidMoneyError("currency must be a Currency value object")
        if value.copy_abs() >= _LIMIT:
            raise InvalidMoneyError("Amount exceeds NUMERIC(18,2)")
        with localcontext(_context(value)):
            normalized = value.quantize(_CENT)
        if normalized.copy_abs() >= _LIMIT:
            raise InvalidMoneyError("Rounded amount exceeds NUMERIC(18,2)")
        # El cero se serializa siempre como 0.00, también tras entradas negativas.
        object.__setattr__(self, "amount", Decimal("0.00") if normalized == 0 else normalized)
        object.__setattr__(self, "currency", currency)

    @classmethod
    def parse(cls, amount: str, currency: Currency) -> Money:
        if not isinstance(amount, str):
            raise InvalidMoneyError("Money.parse requires a decimal string")
        try:
            value = Decimal(amount)
        except DecimalException as error:
            raise InvalidMoneyError("Invalid decimal string") from error
        return cls(value, currency)

    def _check_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise CurrencyMismatchError(self.currency, other.currency)

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_currency(other)
        with localcontext(_context(self.amount, other.amount)):
            return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        return self + (-other)

    def __neg__(self) -> Money:
        return Money(self.amount.copy_negate(), self.currency)

    def __abs__(self) -> Money:
        return Money(self.amount.copy_abs(), self.currency)

    def __lt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_currency(other)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_currency(other)
        return self.amount >= other.amount

    def __mul__(self, scalar: Decimal | int) -> Money:
        value = _decimal(scalar)
        with localcontext(_context(self.amount, value)):
            return Money(self.amount * value, self.currency)

    def __rmul__(self, scalar: Decimal | int) -> Money:
        return self * scalar

    def __truediv__(self, scalar: Decimal | int) -> Money:
        value = _decimal(scalar)
        if value == 0:
            raise InvalidMoneyError("Cannot divide money by zero")
        with localcontext(_context(self.amount, value)):
            return Money(self.amount / value, self.currency)

    def is_zero(self) -> bool:
        return self.amount == 0

    def is_negative(self) -> bool:
        return self.amount < 0

    @classmethod
    def sum(cls, amounts: Iterable[Money], currency: Currency) -> Money:
        """Suma exacta; colección vacía produce cero en la moneda explícita."""
        result = cls(0, currency)
        for amount in amounts:
            result = result + amount
        return result

    def format(self) -> str:
        """Cadena decimal estable para los bordes de la API."""
        return format(self.amount, ".2f")
