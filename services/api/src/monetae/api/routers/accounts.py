from decimal import Decimal
from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, status

from monetae.api.routers.auth import ERROR_RESPONSES
from monetae.api.schemas.accounts import Account, AccountCreate, AccountPage, AccountUpdate
from monetae.api.schemas.auth import ActionResult
from monetae.api.schemas.common import ArchiveRequest
from monetae.api.security import Authenticated, Database, settings_for
from monetae.db.models import Account as AccountRow
from monetae.services.catalog import CatalogService

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"], responses=ERROR_RESPONSES)


def catalog_service(request: Request, db: Database) -> CatalogService:
    return CatalogService(db, settings_for(request).secret_key)


Catalog = Annotated[CatalogService, Depends(catalog_service)]
Csrf = Annotated[str, Header(alias="X-CSRF-Token")]


def account(row: AccountRow, balance: Decimal, transaction_count: int) -> Account:
    return Account(
        name=row.name,
        type=cast(Literal["cash", "bank", "wallet", "card", "other"], row.type),
        currency=row.currency,
        initial_balance=f"{row.initial_balance:.2f}",
        balance=f"{balance:.2f}",
        transaction_count=transaction_count,
        color=row.color,
        icon=row.icon,
        sort_order=row.sort_order,
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
        archived_at=row.archived_at,
    )


@router.get("", response_model=AccountPage, operation_id="list_accounts")
def list_accounts(
    identity: Authenticated,
    service: Catalog,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
    include_archived: bool = False,
) -> AccountPage:
    rows, next_cursor = service.list_accounts(identity.user.id, limit, cursor, include_archived)
    balances = service.account_statistics(identity.user.id, rows)
    return AccountPage(
        items=[account(row, *balances[row.id]) for row in rows], next_cursor=next_cursor
    )


@router.post(
    "", response_model=Account, status_code=status.HTTP_201_CREATED, operation_id="create_account"
)
def create_account(
    payload: AccountCreate, identity: Authenticated, service: Catalog, csrf: Csrf
) -> Account:
    row = service.create_account(identity.user.id, payload.model_dump())
    return account(row, *service.account_statistics(identity.user.id, [row])[row.id])


@router.get("/{id}", response_model=Account, operation_id="get_account")
def get_account(id: UUID, identity: Authenticated, service: Catalog) -> Account:
    row = service.get(AccountRow, identity.user.id, id)
    return account(row, *service.account_statistics(identity.user.id, [row])[row.id])


@router.patch("/{id}", response_model=Account, operation_id="update_account")
def update_account(
    id: UUID, payload: AccountUpdate, identity: Authenticated, service: Catalog, csrf: Csrf
) -> Account:
    values = payload.model_dump(exclude_unset=True)
    if "initial_balance" in values and values["initial_balance"] is not None:
        values["initial_balance"] = Decimal(values["initial_balance"])
    row = service.update_account(identity.user.id, id, values)
    return account(row, *service.account_statistics(identity.user.id, [row])[row.id])


@router.delete("/{id}", response_model=ActionResult, operation_id="delete_account")
def delete_account(id: UUID, identity: Authenticated, service: Catalog, csrf: Csrf) -> ActionResult:
    service.delete(AccountRow, identity.user.id, id)
    return ActionResult(success=True, affected_count=1)


@router.post("/{id}/archive", response_model=Account, operation_id="archive_account")
def archive_account(
    id: UUID, payload: ArchiveRequest, identity: Authenticated, service: Catalog, csrf: Csrf
) -> Account:
    row = service.archive(AccountRow, identity.user.id, id)
    return account(row, *service.account_statistics(identity.user.id, [row])[row.id])


@router.post("/{id}/reactivate", response_model=Account, operation_id="reactivate_account")
def reactivate_account(id: UUID, identity: Authenticated, service: Catalog, csrf: Csrf) -> Account:
    row = service.reactivate(AccountRow, identity.user.id, id)
    return account(row, *service.account_statistics(identity.user.id, [row])[row.id])
