"""Errores de validación y aritmética del dominio puro."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .currency import Currency


class DomainError(ValueError):
    """Una operación incumple el contrato del dominio."""


class CurrencyMismatchError(DomainError):
    """Una operación necesita monedas iguales o una conversión explícita."""

    def __init__(self, expected: Currency, actual: Currency) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"Expected currency {expected.code}, received {actual.code}")


class InvalidMoneyError(DomainError):
    """Importe o escalar inválido para dinero."""


class InvalidExchangeRateError(DomainError):
    """Tasa inválida para el par de monedas indicado."""

    def __init__(self, message: str, from_currency: Currency, to_currency: Currency) -> None:
        self.from_currency = from_currency
        self.to_currency = to_currency
        super().__init__(f"{from_currency.code}->{to_currency.code}: {message}")
