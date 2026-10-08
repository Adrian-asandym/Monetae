from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from monetae.api.routers.auth import ERROR_RESPONSES
from monetae.api.routers.transactions import Csrf
from monetae.api.schemas.auth import ActionResult
from monetae.api.schemas.transfers import Transfer, TransferCreate, TransferPage, TransferUpdate
from monetae.api.security import Authenticated, Database, settings_for
from monetae.services.transfers import TransferPair, TransferService

router = APIRouter(prefix="/api/v1/transfers", tags=["transfers"], responses=ERROR_RESPONSES)


def transfer_service(request: Request, db: Database) -> TransferService:
    return TransferService(db, settings_for(request).secret_key)


Transfers = Annotated[TransferService, Depends(transfer_service)]


def transfer(pair: TransferPair) -> Transfer:
    outgoing, incoming = pair.outgoing, pair.incoming
    return Transfer.model_validate(
        {
            **TransferService.payload(pair).model_dump(),
            "id": outgoing.transfer_group_id,
            "created_at": min(outgoing.created_at, incoming.created_at),
            "updated_at": max(outgoing.updated_at, incoming.updated_at),
            "deleted_at": outgoing.deleted_at,
            "outgoing_transaction_id": outgoing.id,
            "incoming_transaction_id": incoming.id,
            "implicit_rate": f"{pair.implicit_rate():.6f}",
        }
    )


@router.get("", response_model=TransferPage, operation_id="list_transfers")
def list_transfers(
    identity: Authenticated,
    service: Transfers,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
) -> TransferPage:
    rows, next_cursor = service.list(identity.user.id, limit, cursor)
    return TransferPage(items=[transfer(pair) for pair in rows], next_cursor=next_cursor)


@router.post("", response_model=Transfer, status_code=201, operation_id="create_transfer")
def create_transfer(
    payload: TransferCreate, identity: Authenticated, service: Transfers, csrf: Csrf
) -> Transfer:
    return transfer(service.create(identity.user.id, payload))


@router.get("/{id}", response_model=Transfer, operation_id="get_transfer")
def get_transfer(id: UUID, identity: Authenticated, service: Transfers) -> Transfer:
    return transfer(service.get(identity.user.id, id))


@router.patch("/{id}", response_model=Transfer, operation_id="update_transfer")
def update_transfer(
    id: UUID, payload: TransferUpdate, identity: Authenticated, service: Transfers, csrf: Csrf
) -> Transfer:
    return transfer(service.update(identity.user.id, id, payload))


@router.delete("/{id}", response_model=ActionResult, operation_id="delete_transfer")
def delete_transfer(
    id: UUID, identity: Authenticated, service: Transfers, csrf: Csrf
) -> ActionResult:
    service.delete(identity.user.id, id)
    return ActionResult(success=True, affected_count=2)


@router.post("/{id}/restore", response_model=Transfer, operation_id="restore_transfer")
def restore_transfer(id: UUID, identity: Authenticated, service: Transfers, csrf: Csrf) -> Transfer:
    return transfer(service.restore(identity.user.id, id))
