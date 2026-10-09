"""Paso reservado a T-402: conserva el importe diferido para el cuadre."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import JsonValue

if TYPE_CHECKING:
    from monetae.importers.cashew.runner import ImportContext


def run(context: ImportContext) -> dict[str, JsonValue]:
    context.defer(context.plan.deferred_loans, "deferred_loans")
    return {}
