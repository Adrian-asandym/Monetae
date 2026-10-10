from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request

from monetae.api.routers.auth import ERROR_RESPONSES
from monetae.api.schemas.auth import ActionResult
from monetae.api.schemas.goals import (
    Goal,
    GoalCreate,
    GoalPage,
    GoalUpdate,
    TransactionAssignment,
)
from monetae.api.security import Authenticated, Database, clock_for, settings_for
from monetae.services.goals import GoalService

router = APIRouter(prefix="/api/v1/goals", tags=["goals"], responses=ERROR_RESPONSES)
Csrf = Annotated[str, Header(alias="X-CSRF-Token")]


def goal_service(request: Request, db: Database) -> GoalService:
    return GoalService(db, settings_for(request).secret_key, clock_for(request))


Goals = Annotated[GoalService, Depends(goal_service)]


@router.get("", response_model=GoalPage, operation_id="list_goals")
def list_goals(
    identity: Authenticated,
    service: Goals,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
) -> GoalPage:
    return service.list(identity.user, limit, cursor)


@router.post("", response_model=Goal, status_code=201, operation_id="create_goal")
def create_goal(payload: GoalCreate, identity: Authenticated, service: Goals, csrf: Csrf) -> Goal:
    return service.representation(identity.user, service.create(identity.user, payload))


@router.get("/{id}", response_model=Goal, operation_id="get_goal")
def get_goal(id: UUID, identity: Authenticated, service: Goals) -> Goal:
    return service.representation(identity.user, service.get(identity.user, id))


@router.patch("/{id}", response_model=Goal, operation_id="update_goal")
def update_goal(
    id: UUID, payload: GoalUpdate, identity: Authenticated, service: Goals, csrf: Csrf
) -> Goal:
    return service.representation(identity.user, service.update(identity.user, id, payload))


@router.delete("/{id}", response_model=ActionResult, operation_id="delete_goal")
def delete_goal(id: UUID, identity: Authenticated, service: Goals, csrf: Csrf) -> ActionResult:
    service.delete(identity.user, id)
    return ActionResult(success=True, affected_count=1)


@router.put("/{id}/transactions", response_model=Goal, operation_id="assign_goals_transactions")
def assign_goals_transactions(
    id: UUID, payload: TransactionAssignment, identity: Authenticated, service: Goals, csrf: Csrf
) -> Goal:
    return service.representation(
        identity.user, service.assign(identity.user, id, payload.transaction_ids)
    )
