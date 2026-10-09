"""Reporte estricto; las secciones de extensiones aceptan valores JSON tipados."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class ReportModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class EntityCounts(ReportModel):
    created: int = 0
    already_imported: int = 0
    deferred: int = 0
    skipped: int = 0


class ReviewItem(ReportModel):
    kind: str
    payload: dict[str, JsonValue] = Field(default_factory=dict)


class AccountBalance(ReportModel):
    source_wallet_pk: str
    account_id: UUID
    currency: str
    before: Decimal
    cashew_balance: Decimal
    monetae_balance: Decimal
    deferred_amount: Decimal
    unexplained: Decimal


class ImportReport(ReportModel):
    file_sha256: str
    source_schema_version: int
    tables: dict[str, int]
    unknown_tables: list[str] = Field(default_factory=list)
    unknown_columns: dict[str, list[str]] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    unmapped_fields: dict[str, list[str]] = Field(default_factory=dict)
    counts: dict[str, EntityCounts] = Field(default_factory=dict)
    steps: dict[str, dict[str, JsonValue]] = Field(default_factory=dict)
    balances: list[AccountBalance] = Field(default_factory=list)
    review_items: list[ReviewItem] = Field(default_factory=list)
    provisional_fx: int = 0
    outcome: str = "succeeded"

    def entity(self, name: str) -> EntityCounts:
        return self.counts.setdefault(name, EntityCounts())
