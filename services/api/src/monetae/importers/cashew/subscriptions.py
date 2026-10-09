"""Paso reservado a T-403: no inventa reglas ni transacciones recurrentes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import JsonValue

if TYPE_CHECKING:
    from monetae.importers.cashew.runner import ImportContext


def run(context: ImportContext) -> dict[str, JsonValue]:
    context.defer(context.plan.deferred_recurring, "deferred_recurring")
    return {}
