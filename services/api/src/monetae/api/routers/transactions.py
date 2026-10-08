import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response

from monetae.api.routers.auth import ERROR_RESPONSES
from monetae.api.schemas.auth import ActionResult, Currency
from monetae.api.schemas.transactions import (
    TagAssignment,
    Timestamp,
    Transaction,
    TransactionBatch,
    TransactionCreate,
    TransactionKind,
    TransactionPage,
    TransactionStatus,
    TransactionUpdate,
)
from monetae.api.security import Authenticated, Database, settings_for
from monetae.db.models import Transaction as TransactionRow
from monetae.services.idempotency import IdempotencyService, StoredResponse
from monetae.services.transactions import TransactionFilters, TransactionService

router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"], responses=ERROR_RESPONSES)
Csrf = Annotated[str, Header(alias="X-CSRF-Token")]


def transaction_service(request: Request, db: Database) -> TransactionService:
    return TransactionService(db, settings_for(request).secret_key)


Transactions = Annotated[TransactionService, Depends(transaction_service)]


def transaction(
    row: TransactionRow, tag_ids: list[UUID], loan_id: UUID | None = None
) -> Transaction:
    values = {
        name: getattr(row, name)
        for name in Transaction.model_fields
        if name not in {"tag_ids", "loan_id", "reactivation_suggestions"}
    }
    values.update(
        amount=f"{row.amount:.2f}",
        fx_rate_to_base=f"{row.fx_rate_to_base:.6f}",
        tag_ids=tag_ids,
        loan_id=loan_id,
        reactivation_suggestions=[],
    )
    return Transaction.model_validate(values)


def result(service: TransactionService, user_id: UUID, row: TransactionRow) -> Transaction:
    return transaction(
        row, service.tag_ids(user_id, [row])[row.id], service.loan_ids(user_id, [row]).get(row.id)
    )


@router.get("", response_model=TransactionPage, operation_id="list_transactions")
def list_transactions(
    identity: Authenticated,
    service: Transactions,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
    date_from: Timestamp | None = None,
    date_to: Timestamp | None = None,
    account_id: UUID | None = None,
    category_id: UUID | None = None,
    currency: Currency | None = None,
    kind: TransactionKind | None = None,
    status: TransactionStatus | None = None,
    tag_ids: Annotated[list[UUID] | None, Query()] = None,
    q: str | None = None,
    include_deleted: bool = False,
    loan_id: UUID | None = None,
    person_id: UUID | None = None,
) -> TransactionPage:
    filters = TransactionFilters(
        date_from=date_from,
        date_to=date_to,
        account_id=account_id,
        category_id=category_id,
        currency=currency,
        kind=kind,
        status=status,
        tag_ids=tuple(tag_ids or []),
        q=q,
        include_deleted=include_deleted,
        loan_id=loan_id,
        person_id=person_id,
    )
    rows, cursor = service.list(identity.user.id, filters, limit, cursor)
    tags = service.tag_ids(identity.user.id, rows)
    loans = service.loan_ids(identity.user.id, rows)
    return TransactionPage(
        items=[transaction(row, tags[row.id], loans.get(row.id)) for row in rows],
        next_cursor=cursor,
    )


@router.post("", response_model=Transaction, status_code=201, operation_id="create_transaction")
def create_transaction(
    payload: TransactionCreate,
    identity: Authenticated,
    service: Transactions,
    csrf: Csrf,
    response: Response,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", min_length=1, max_length=128)
    ] = None,
) -> Transaction:
    def create() -> StoredResponse:
        row = service.create(identity.user.id, payload)
        return StoredResponse(201, result(service, identity.user.id, row).model_dump(mode="json"))

    body = payload.model_dump(mode="json")
    # Etiquetas son un conjunto y timestamps se normalizan antes de firmar.
    body["tag_ids"] = sorted(str(tag) for tag in payload.tag_ids)
    stored = IdempotencyService(service.db).execute(
        identity.user.id, idempotency_key, "POST /api/v1/transactions", body, create
    )
    response.status_code = stored.status
    return Transaction.model_validate_json(json.dumps(stored.body))


@router.post("/batch", response_model=ActionResult, operation_id="batch_transactions")
def batch_transactions(
    payload: TransactionBatch, identity: Authenticated, service: Transactions, csrf: Csrf
) -> ActionResult:
    count = service.batch(identity.user.id, payload)
    return ActionResult(success=True, affected_count=count)


@router.post("/{id}/post", response_model=Transaction, operation_id="post_scheduled_transaction")
def post_transaction(
    id: UUID,
    identity: Authenticated,
    service: Transactions,
    csrf: Csrf,
    payload: TransactionUpdate | None = None,
) -> Transaction:
    return result(service, identity.user.id, service.post(identity.user.id, id, payload))


@router.get("/{id}", response_model=Transaction, operation_id="get_transaction")
def get_transaction(
    id: UUID, identity: Authenticated, service: Transactions, include_deleted: bool = False
) -> Transaction:
    return result(
        service,
        identity.user.id,
        service.get(identity.user.id, id, include_deleted=include_deleted),
    )


@router.patch("/{id}", response_model=Transaction, operation_id="update_transaction")
def update_transaction(
    id: UUID, payload: TransactionUpdate, identity: Authenticated, service: Transactions, csrf: Csrf
) -> Transaction:
    return result(service, identity.user.id, service.update(identity.user.id, id, payload))


@router.delete("/{id}", response_model=ActionResult, operation_id="delete_transaction")
def delete_transaction(
    id: UUID, identity: Authenticated, service: Transactions, csrf: Csrf
) -> ActionResult:
    service.delete(identity.user.id, id)
    return ActionResult(success=True, affected_count=1)


@router.post("/{id}/restore", response_model=Transaction, operation_id="restore_transaction")
def restore_transaction(
    id: UUID, identity: Authenticated, service: Transactions, csrf: Csrf
) -> Transaction:
    return result(service, identity.user.id, service.restore(identity.user.id, id))


@router.put("/{id}/tags", response_model=Transaction, operation_id="replace_transaction_tags")
def replace_transaction_tags(
    id: UUID, payload: TagAssignment, identity: Authenticated, service: Transactions, csrf: Csrf
) -> Transaction:
    return result(
        service, identity.user.id, service.replace_tags(identity.user.id, id, payload.tag_ids)
    )
