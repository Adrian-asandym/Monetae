from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request

from monetae.api.routers.auth import ERROR_RESPONSES
from monetae.api.schemas.auth import ActionResult, Currency
from monetae.api.schemas.subscriptions import (
    ArchiveRequest,
    Subscription,
    SubscriptionCreate,
    SubscriptionPage,
    SubscriptionStatus,
    SubscriptionTotalPage,
    SubscriptionUpdate,
)
from monetae.api.security import Authenticated, Database, clock_for, settings_for
from monetae.services.subscriptions import SubscriptionService

router = APIRouter(
    prefix="/api/v1/subscriptions", tags=["subscriptions"], responses=ERROR_RESPONSES
)
Csrf = Annotated[str, Header(alias="X-CSRF-Token")]


def subscription_service(request: Request, db: Database) -> SubscriptionService:
    return SubscriptionService(db, settings_for(request).secret_key, clock_for(request))


Subscriptions = Annotated[SubscriptionService, Depends(subscription_service)]


@router.get("", response_model=SubscriptionPage, operation_id="list_subscriptions")
def list_subscriptions(
    identity: Authenticated,
    service: Subscriptions,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
    status: SubscriptionStatus = "active",
) -> SubscriptionPage:
    return service.list(identity.user.id, status, limit, cursor)


@router.post("", response_model=Subscription, status_code=201, operation_id="create_subscription")
def create_subscription(
    payload: SubscriptionCreate, identity: Authenticated, service: Subscriptions, csrf: Csrf
) -> Subscription:
    return service.representation(service.create(identity.user.id, payload))


@router.get(
    "/totals", response_model=SubscriptionTotalPage, operation_id="get_subscriptions_totals"
)
def subscription_totals(
    identity: Authenticated,
    service: Subscriptions,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
    report_currency: Currency | None = None,
) -> SubscriptionTotalPage:
    return service.totals(identity.user.id, report_currency, limit, cursor)


@router.get("/{id}", response_model=Subscription, operation_id="get_subscription")
def get_subscription(id: UUID, identity: Authenticated, service: Subscriptions) -> Subscription:
    return service.representation(service.get(identity.user.id, id))


@router.patch("/{id}", response_model=Subscription, operation_id="update_subscription")
def update_subscription(
    id: UUID,
    payload: SubscriptionUpdate,
    identity: Authenticated,
    service: Subscriptions,
    csrf: Csrf,
) -> Subscription:
    return service.representation(service.update(identity.user.id, id, payload))


@router.delete("/{id}", response_model=ActionResult, operation_id="delete_subscription")
def delete_subscription(
    id: UUID, identity: Authenticated, service: Subscriptions, csrf: Csrf
) -> ActionResult:
    service.delete(identity.user.id, id)
    return ActionResult(success=True, affected_count=1)


@router.post("/{id}/archive", response_model=Subscription, operation_id="archive_subscription")
def archive_subscription(
    id: UUID, payload: ArchiveRequest, identity: Authenticated, service: Subscriptions, csrf: Csrf
) -> Subscription:
    return service.representation(service.archive(identity.user.id, id, payload.reason))


@router.post(
    "/{id}/reactivate", response_model=Subscription, operation_id="reactivate_subscription"
)
def reactivate_subscription(
    id: UUID, identity: Authenticated, service: Subscriptions, csrf: Csrf
) -> Subscription:
    return service.representation(service.reactivate(identity.user.id, id))
