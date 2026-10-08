"""Rutas del libro de préstamos; las reglas pertenecen al dominio y servicio."""

import json
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from starlette.responses import JSONResponse

from monetae.api.routers.auth import ERROR_RESPONSES
from monetae.api.schemas import loans as schema
from monetae.api.schemas.auth import ActionResult, Currency
from monetae.api.security import Authenticated, Database, settings_for
from monetae.services.idempotency import IdempotencyService, StoredResponse
from monetae.services.loans import LoanError, LoanService

router = APIRouter(prefix="/api/v1/loans", tags=["loans"], responses=ERROR_RESPONSES)
Csrf = Annotated[str, Header(alias="X-CSRF-Token")]
Limit = Annotated[int, Query(ge=1, le=200)]
IdempotencyKey = Annotated[
    str | None, Header(alias="Idempotency-Key", min_length=1, max_length=128)
]


def loan_service(request: Request, db: Database) -> LoanService:
    return LoanService(db, settings_for(request).secret_key)


Loans = Annotated[LoanService, Depends(loan_service)]


async def loan_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, LoanError)
    return JSONResponse(
        status_code=exc.status,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": HTTPStatus(exc.status).phrase,
            "status": exc.status,
            "detail": exc.detail,
            "code": exc.code,
            "instance": request.url.path,
            **exc.extra,
        },
    )


@router.get("", response_model=schema.LoanPage, operation_id="list_loans")
def list_loans(
    identity: Authenticated,
    service: Loans,
    limit: Limit = 50,
    cursor: str | None = None,
    person_id: UUID | None = None,
    currency: Currency | None = None,
    status: schema.LoanStatus | None = None,
    include_deleted: bool = False,
) -> schema.LoanPage:
    return service.list(
        identity.user.id, person_id, currency, status, include_deleted, limit, cursor
    )


@router.get("/summary", response_model=schema.LoanSummaryPage, operation_id="summarize_loans")
def summarize_loans(
    identity: Authenticated,
    service: Loans,
    limit: Limit = 50,
    cursor: str | None = None,
    person_id: UUID | None = None,
    currency: Currency | None = None,
) -> schema.LoanSummaryPage:
    return service.summary(identity.user.id, person_id, currency, limit, cursor)


@router.post("", response_model=schema.Loan, status_code=201, operation_id="create_loan")
def create_loan(
    payload: schema.LoanCreate,
    identity: Authenticated,
    service: Loans,
    csrf: Csrf,
    response: Response,
    idempotency_key: IdempotencyKey = None,
) -> schema.Loan:
    def create() -> StoredResponse:
        row = service.create(identity.user.id, payload)
        return StoredResponse(201, service.serialize(row).model_dump(mode="json"))

    stored = IdempotencyService(service.db).execute(
        identity.user.id,
        idempotency_key,
        "POST /api/v1/loans",
        payload.model_dump(mode="json"),
        create,
    )
    response.status_code = stored.status
    return schema.Loan.model_validate_json(json.dumps(stored.body))


@router.get("/{id}", response_model=schema.Loan, operation_id="get_loan")
def get_loan(
    id: UUID, identity: Authenticated, service: Loans, include_deleted: bool = False
) -> schema.Loan:
    return service.serialize(service.get(identity.user.id, id, include_deleted=include_deleted))


@router.patch("/{id}", response_model=schema.Loan, operation_id="update_loan")
def update_loan(
    id: UUID, payload: schema.LoanUpdate, identity: Authenticated, service: Loans, csrf: Csrf
) -> schema.Loan:
    return service.serialize(service.update(identity.user.id, id, payload))


@router.delete("/{id}", response_model=ActionResult, operation_id="delete_loan")
def delete_loan(id: UUID, identity: Authenticated, service: Loans, csrf: Csrf) -> ActionResult:
    service.toggle_loan(identity.user.id, id, restore=False)
    return ActionResult(success=True, affected_count=1)


@router.post("/{id}/restore", response_model=schema.Loan, operation_id="restore_loan")
def restore_loan(id: UUID, identity: Authenticated, service: Loans, csrf: Csrf) -> schema.Loan:
    return service.serialize(service.toggle_loan(identity.user.id, id, restore=True))


@router.get("/{id}/balance", response_model=schema.LoanBalance, operation_id="get_loan_balance")
def get_loan_balance(
    id: UUID, identity: Authenticated, service: Loans, include_deleted: bool = False
) -> schema.LoanBalance:
    return service.balance(service.get(identity.user.id, id, include_deleted=include_deleted))


@router.get(
    "/{id}/movements", response_model=schema.LoanMovementPage, operation_id="list_loan_movements"
)
def list_loan_movements(
    id: UUID,
    identity: Authenticated,
    service: Loans,
    limit: Limit = 50,
    cursor: str | None = None,
    include_deleted: bool = False,
) -> schema.LoanMovementPage:
    return service.list_movements(
        service.get(identity.user.id, id, include_deleted=include_deleted),
        include_deleted,
        limit,
        cursor,
    )


@router.post(
    "/{id}/movements",
    response_model=schema.LoanMovement,
    status_code=201,
    operation_id="create_loan_movement",
)
def create_loan_movement(
    id: UUID,
    payload: schema.MovementCreate,
    identity: Authenticated,
    service: Loans,
    csrf: Csrf,
    response: Response,
    idempotency_key: IdempotencyKey = None,
) -> schema.LoanMovement:
    def create() -> StoredResponse:
        movement = service.add_movement(identity.user.id, id, payload)
        return StoredResponse(201, movement.model_dump(mode="json"))

    stored = IdempotencyService(service.db).execute(
        identity.user.id,
        idempotency_key,
        f"POST /api/v1/loans/{id}/movements",
        payload.model_dump(mode="json"),
        create,
    )
    response.status_code = stored.status
    return schema.LoanMovement.model_validate_json(json.dumps(stored.body))


@router.put(
    "/{id}/movements/{movement_id}",
    response_model=schema.LoanMovement,
    operation_id="update_loan_movement",
)
def update_loan_movement(
    id: UUID,
    movement_id: UUID,
    payload: schema.MovementCreate,
    identity: Authenticated,
    service: Loans,
    csrf: Csrf,
) -> schema.LoanMovement:
    return service.update_movement(identity.user.id, id, movement_id, payload)


@router.delete(
    "/{id}/movements/{movement_id}",
    response_model=ActionResult,
    operation_id="delete_loan_movement",
)
def delete_loan_movement(
    id: UUID, movement_id: UUID, identity: Authenticated, service: Loans, csrf: Csrf
) -> ActionResult:
    service.toggle_movement(identity.user.id, id, movement_id, restore=False)
    return ActionResult(success=True, affected_count=1)


@router.post(
    "/{id}/movements/{movement_id}/restore",
    response_model=schema.LoanMovement,
    operation_id="restore_loan_movement",
)
def restore_loan_movement(
    id: UUID, movement_id: UUID, identity: Authenticated, service: Loans, csrf: Csrf
) -> schema.LoanMovement:
    row = service.toggle_movement(identity.user.id, id, movement_id, restore=True)
    return service.serialize_movements(service.get(identity.user.id, id), [row])[0]


@router.post(
    "/{id}/payment-proposal",
    response_model=schema.PaymentProposal,
    operation_id="propose_loan_payment",
)
def propose_loan_payment(
    id: UUID,
    payload: schema.PaymentProposalRequest,
    identity: Authenticated,
    service: Loans,
    csrf: Csrf,
) -> schema.PaymentProposal:
    return service.payment_proposal(service.get(identity.user.id, id), payload)


@router.post(
    "/{id}/interest-proposal",
    response_model=schema.InterestProposal,
    operation_id="propose_loan_interest",
)
def propose_loan_interest(
    id: UUID,
    payload: schema.InterestProposalRequest,
    identity: Authenticated,
    service: Loans,
    csrf: Csrf,
) -> schema.InterestProposal:
    return service.interest_proposal(service.get(identity.user.id, id), payload)
