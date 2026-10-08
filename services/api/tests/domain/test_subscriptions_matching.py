from dataclasses import replace
from datetime import UTC, date, datetime
from typing import cast

import pytest

from monetae.domain import PEN, Money
from monetae.domain.subscriptions import (
    Period,
    Subscription,
    SubscriptionValidationError,
    archive,
    matching_archived,
    normalize_title,
)


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("  NÉTFLIX  ", "netflix"),
        ("NETFLIX", "netflix"),
        (" NetFlix \t Premium\n", "netflix premium"),
        ("Cafe\u0301", "cafe"),
        ("Straße", "strasse"),
        ("", ""),
        (" \t\n ", ""),
    ],
)
def test_normalize_title(title: str, expected: str) -> None:
    assert normalize_title(title) == expected
    assert normalize_title(normalize_title(title)) == expected


def test_matching_is_exact_archived_only_and_never_reactivates() -> None:
    sub = Subscription(
        "Netflix", Money(1, PEN), Period.MONTHLY, 1, date(2024, 1, 1), date(2024, 1, 1)
    )
    archived = archive(sub, datetime(2024, 1, 1, tzinfo=UTC))
    accented = replace(archived, title="  Nétflix ")
    premium = replace(archived, title="Netflix Premium")
    assert matching_archived("NETFLIX", iter([sub, archived, premium, accented])) == [
        archived,
        accented,
    ]
    assert matching_archived("flix", [archived]) == []
    assert matching_archived("", [archived]) == []
    assert matching_archived("   ", [archived]) == []
    assert archived.status == accented.status == "archived"
    with pytest.raises(SubscriptionValidationError):
        normalize_title(cast(str, 1))
