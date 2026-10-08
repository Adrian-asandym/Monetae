from datetime import UTC, datetime, timedelta

import pytest

from monetae.domain.passwords import retry_after, validate_password


@pytest.mark.parametrize("length", [0, 11, 129])
def test_invalid_password_length(length: int) -> None:
    with pytest.raises(ValueError):
        validate_password("a" * length)


@pytest.mark.parametrize("length", [12, 128])
def test_valid_password_length(length: int) -> None:
    validate_password("a" * length)


def test_blocking_window_boundary_and_round_up() -> None:
    now = datetime(2026, 10, 7, tzinfo=UTC)
    assert retry_after([now] * 4, 5, now) == 0
    assert retry_after([now] * 5, 5, now) == 900
    assert retry_after([now] * 5, 5, now + timedelta(seconds=899, microseconds=1)) == 1
    assert retry_after([now] * 5, 5, now + timedelta(minutes=15)) == 0
