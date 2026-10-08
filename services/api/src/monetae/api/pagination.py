"""Cursor firmado estructuralmente para listados keyset de catálogos."""

import base64
import binascii
import hashlib
import hmac
import json
from collections.abc import Sequence

from sqlalchemy import and_, or_
from sqlalchemy.sql.elements import ColumnElement

from monetae.services.auth import AuthError


def encode_cursor(resource: str, filters: str, key: Sequence[str], secret: str) -> str:
    raw = json.dumps([resource, filters, list(key)], separators=(",", ":")).encode()
    signature = hmac.new(secret.encode(), raw, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw + signature).decode().rstrip("=")


def decode_cursor(cursor: str | None, resource: str, filters: str, secret: str) -> list[str] | None:
    if cursor is None:
        return None
    try:
        raw = base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True)
        payload, signature = raw[:-32], raw[-32:]
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).digest()
        if len(signature) != 32 or not hmac.compare_digest(signature, expected):
            raise ValueError
        value = json.loads(payload)
        if (
            not isinstance(value, list)
            or len(value) != 3
            or value[0] != resource
            or value[1] != filters
            or not isinstance(value[2], list)
            or not all(isinstance(item, str) for item in value[2])
        ):
            raise ValueError
        return value[2]
    except (ValueError, TypeError, binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuthError(400, "invalid_cursor", "The pagination cursor is invalid.") from exc


def keyset_predicate(
    columns: Sequence[ColumnElement[object]], values: Sequence[object]
) -> ColumnElement[bool]:
    if len(columns) != len(values):
        raise AuthError(400, "invalid_cursor", "The pagination cursor is invalid.")
    comparisons: list[ColumnElement[bool]] = []
    for index, (column, value) in enumerate(zip(columns, values, strict=True)):
        comparison = column > value
        prefix = [columns[position] == values[position] for position in range(index)]
        comparisons.append(and_(*prefix, comparison) if prefix else comparison)
    return or_(*comparisons)
