"""Reglas puras de importes y tasa implícita entre las dos patas."""

from decimal import Decimal

from monetae.domain.errors import DomainError
from monetae.domain.fx import implied_rate
from monetae.domain.money import Money


class InvalidTransferAmountError(DomainError):
    pass


class TransferAmountMismatchError(DomainError):
    pass


def validate_transfer_amounts(outgoing: Money, incoming: Money) -> Decimal:
    if outgoing.amount <= 0 or incoming.amount <= 0:
        raise InvalidTransferAmountError("Transfer amounts must be positive.")
    if outgoing.currency == incoming.currency:
        if outgoing != incoming:
            raise TransferAmountMismatchError("Amounts in the same currency must match.")
        return Decimal("1.000000")
    return implied_rate(outgoing, incoming).rate
