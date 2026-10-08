"""Tasas: unidades de destino por una unidad de origen, sin I/O."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext

from .currency import PEN, Currency
from .errors import CurrencyMismatchError, InvalidExchangeRateError, InvalidMoneyError
from .money import Money, _context, _decimal


def _normalize_rate(value: Decimal | int, source: Currency, target: Currency) -> Decimal:
    try:
        decimal = _decimal(value)
    except InvalidMoneyError as error:
        raise InvalidExchangeRateError(str(error), source, target) from error
    with localcontext(_context(decimal)):
        normalized = decimal.quantize(Decimal("0.000001"))
    if normalized <= 0:
        raise InvalidExchangeRateError("Rate must be positive after rounding", source, target)
    return normalized


@dataclass(frozen=True, slots=True, init=False)
class ExchangeRate:
    """Unidades de to_currency por 1 from_currency, redondeadas a 6 decimales."""

    from_currency: Currency
    to_currency: Currency
    rate: Decimal

    def __init__(self, from_currency: Currency, to_currency: Currency, rate: Decimal | int) -> None:
        if from_currency == to_currency:
            raise InvalidExchangeRateError("Currencies must differ", from_currency, to_currency)
        object.__setattr__(self, "from_currency", from_currency)
        object.__setattr__(self, "to_currency", to_currency)
        object.__setattr__(self, "rate", _normalize_rate(rate, from_currency, to_currency))

    def inverse(self) -> ExchangeRate:
        with localcontext(_context(self.rate)):
            return ExchangeRate(self.to_currency, self.from_currency, Decimal(1) / self.rate)


def convert(money: Money, rate: ExchangeRate) -> Money:
    if money.currency != rate.from_currency:
        raise CurrencyMismatchError(rate.from_currency, money.currency)
    with localcontext(_context(money.amount, rate.rate)):
        return Money(money.amount * rate.rate, rate.to_currency)


def convert_back(money: Money, rate: ExchangeRate) -> Money:
    """Importe del préstamo = importe de cuenta / fx_rate_applied (ARCH §5.5)."""
    if money.currency != rate.to_currency:
        raise CurrencyMismatchError(rate.to_currency, money.currency)
    with localcontext(_context(money.amount, rate.rate)):
        return Money(money.amount / rate.rate, rate.from_currency)


def implied_rate(from_money: Money, to_money: Money) -> ExchangeRate:
    """Tasa positiva entre magnitudes reales de las dos patas de una transferencia."""
    if from_money.is_zero() or to_money.is_zero():
        raise InvalidExchangeRateError(
            "Transfer amounts must be nonzero", from_money.currency, to_money.currency
        )
    with localcontext(_context(from_money.amount, to_money.amount)):
        return ExchangeRate(
            from_money.currency,
            to_money.currency,
            to_money.amount.copy_abs() / from_money.amount.copy_abs(),
        )


def apply_rate_to_base(
    money: Money, rate_to_base: Decimal | int, base_currency: Currency = PEN
) -> Money:
    """Aplica la tasa guardada hacia la base (PEN por defecto).

    Si la moneda ya es la base, la tasa debe ser exactamente 1 y no hay
    conversión entre monedas. No consulta ni recalcula tasas históricas.
    """
    normalized = _normalize_rate(rate_to_base, money.currency, base_currency)
    if money.currency == base_currency:
        if _decimal(rate_to_base) != 1:
            raise InvalidExchangeRateError(
                "Base currency requires rate 1", money.currency, base_currency
            )
        return money
    return convert(money, ExchangeRate(money.currency, base_currency, normalized))
