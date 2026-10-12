import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response

from monetae.api.routers.auth import ERROR_RESPONSES
from monetae.api.routers.transactions import Csrf, result
from monetae.api.schemas.auth import Currency
from monetae.api.schemas.balance_corrections import (
    BalanceCorrection,
    BalanceCorrectionCreate,
    BalanceCorrectionLeg,
    BalanceCorrectionPage,
    BalanceCorrectionSummary,
)
from monetae.api.security import Authenticated, Database, settings_for
from monetae.services.balance_corrections import BalanceCorrectionService, CorrectionFilters
from monetae.services.idempotency import IdempotencyService, StoredResponse

router = APIRouter(
    prefix="/api/v1/balance-corrections", tags=["balance-corrections"], responses=ERROR_RESPONSES
)


def correction_service(request: Request, db: Database) -> BalanceCorrectionService:
    return BalanceCorrectionService(db, settings_for(request).secret_key, request.app.state.clock)


Corrections = Annotated[BalanceCorrectionService, Depends(correction_service)]


@router.post(
    "", response_model=BalanceCorrection, status_code=201, operation_id="create_balance_correction"
)
def create_balance_correction(
    payload: BalanceCorrectionCreate,
    identity: Authenticated,
    service: Corrections,
    csrf: Csrf,
    response: Response,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", min_length=1, max_length=128)
    ] = None,
) -> BalanceCorrection:
    def create() -> StoredResponse:
        pair = service.create(identity.user.id, payload)
        value = BalanceCorrection.model_validate(
            {
                "group_id": pair.outgoing.transfer_group_id,
                "outgoing": result(service.transactions, identity.user.id, pair.outgoing),
                "incoming": result(service.transactions, identity.user.id, pair.incoming),
            }
        )
        return StoredResponse(201, value.model_dump(mode="json"))

    stored = IdempotencyService(service.db).execute(
        identity.user.id,
        idempotency_key,
        "POST /api/v1/balance-corrections",
        payload.model_dump(mode="json"),
        create,
    )
    response.status_code = stored.status
    return BalanceCorrection.model_validate_json(json.dumps(stored.body))


@router.get("", response_model=BalanceCorrectionPage, operation_id="list_balance_corrections")
def list_balance_corrections(
    identity: Authenticated,
    service: Corrections,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
    from_account_id: UUID | None = None,
    to_account_id: UUID | None = None,
    from_currency: Currency | None = None,
    to_currency: Currency | None = None,
) -> BalanceCorrectionPage:
    pairs, next_cursor = service.list(
        identity.user.id,
        CorrectionFilters(from_account_id, to_account_id, from_currency, to_currency),
        limit,
        cursor,
    )
    items = []
    for pair in pairs:
        legs = [
            BalanceCorrectionLeg.model_validate(
                {
                    "id": row.id,
                    "account_id": row.account_id,
                    "currency": row.currency,
                    "amount": f"{row.amount:.2f}",
                    "occurred_at": row.occurred_at,
                }
            )
            for row in (pair.outgoing, pair.incoming)
        ]
        items.append(
            BalanceCorrectionSummary.model_validate(
                {
                    "group_id": pair.outgoing.transfer_group_id,
                    "outgoing": legs[0],
                    "incoming": legs[1],
                    "implicit_rate": f"{pair.implicit_rate():.6f}",
                }
            )
        )
    return BalanceCorrectionPage(items=items, next_cursor=next_cursor)
