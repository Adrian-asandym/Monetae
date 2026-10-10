from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request

from monetae.api.routers.auth import ERROR_RESPONSES
from monetae.api.schemas.auth import ActionResult
from monetae.api.schemas.budgets import (
    Budget,
    BudgetCreate,
    BudgetPage,
    BudgetUpdate,
    TransactionAssignment,
)
from monetae.api.security import Authenticated, Database, clock_for, settings_for
from monetae.services.budgets import BudgetService

router = APIRouter(prefix="/api/v1/budgets", tags=["budgets"], responses=ERROR_RESPONSES)
Csrf = Annotated[str, Header(alias="X-CSRF-Token")]


def budget_service(request: Request, db: Database) -> BudgetService:
    return BudgetService(db, settings_for(request).secret_key, clock_for(request))


Budgets = Annotated[BudgetService, Depends(budget_service)]


@router.get("", response_model=BudgetPage, operation_id="list_budgets")
def list_budgets(
    identity: Authenticated,
    service: Budgets,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
) -> BudgetPage:
    return service.list(identity.user, limit, cursor)


@router.post("", response_model=Budget, status_code=201, operation_id="create_budget")
def create_budget(
    payload: BudgetCreate, identity: Authenticated, service: Budgets, csrf: Csrf
) -> Budget:
    return service.representation(identity.user, service.create(identity.user, payload))


@router.get("/{id}", response_model=Budget, operation_id="get_budget")
def get_budget(id: UUID, identity: Authenticated, service: Budgets) -> Budget:
    return service.representation(identity.user, service.get(identity.user, id))


@router.patch("/{id}", response_model=Budget, operation_id="update_budget")
def update_budget(
    id: UUID, payload: BudgetUpdate, identity: Authenticated, service: Budgets, csrf: Csrf
) -> Budget:
    return service.representation(identity.user, service.update(identity.user, id, payload))


@router.delete("/{id}", response_model=ActionResult, operation_id="delete_budget")
def delete_budget(id: UUID, identity: Authenticated, service: Budgets, csrf: Csrf) -> ActionResult:
    service.delete(identity.user, id)
    return ActionResult(success=True, affected_count=1)


@router.put("/{id}/transactions", response_model=Budget, operation_id="assign_budgets_transactions")
def assign_budgets_transactions(
    id: UUID, payload: TransactionAssignment, identity: Authenticated, service: Budgets, csrf: Csrf
) -> Budget:
    return service.representation(
        identity.user, service.assign(identity.user, id, payload.transaction_ids)
    )
