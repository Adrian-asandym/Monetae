from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from monetae.domain import PEN, USD, Currency, DomainError


@pytest.mark.parametrize("code", ["pen", "Pen", " PEN", "PEN ", "PE", "PENN", "P3N", "ÑEN", ""])
def test_invalid_currency(code: str) -> None:
    with pytest.raises(DomainError, match="uppercase ASCII"):
        Currency(code)


def test_currency_non_string_and_value_semantics() -> None:
    with pytest.raises(DomainError):
        Currency(cast(str, 123))
    assert PEN == Currency("PEN")
    assert PEN != USD
    assert len({PEN, USD, Currency("PEN")}) == 2
    assert {PEN: "sol"}[Currency("PEN")] == "sol"
    assert repr(PEN) == "Currency(code='PEN')"
    attribute = "code"
    with pytest.raises(FrozenInstanceError):
        setattr(PEN, attribute, "USD")
