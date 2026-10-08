"""Política pura de contraseñas y límites de intentos."""

from datetime import datetime, timedelta

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128
LOGIN_WINDOW = timedelta(minutes=15)
EMAIL_FAILURE_LIMIT = 5
IP_FAILURE_LIMIT = 20


def validate_password(password: str) -> None:
    if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        raise ValueError("Password must contain between 12 and 128 characters.")


def retry_after(failures: list[datetime], limit: int, now: datetime) -> int:
    recent = sorted(at for at in failures if at > now - LOGIN_WINDOW)
    if len(recent) < limit:
        return 0
    # The limit-th newest failure must leave the window before another attempt is allowed.
    remaining = recent[-limit] + LOGIN_WINDOW - now
    return max(1, (remaining // timedelta(seconds=1)) + bool(remaining.microseconds))
