from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, status

from monetae.api.routers.auth import ERROR_RESPONSES
from monetae.api.schemas.auth import ActionResult
from monetae.api.schemas.categories import Category, CategoryCreate, CategoryPage, CategoryUpdate
from monetae.api.security import Authenticated, Database, settings_for
from monetae.db.models import Category as CategoryRow
from monetae.services.catalog import CatalogService

router = APIRouter(prefix="/api/v1/categories", tags=["categories"], responses=ERROR_RESPONSES)


def catalog_service(request: Request, db: Database) -> CatalogService:
    return CatalogService(db, settings_for(request).secret_key)


Catalog = Annotated[CatalogService, Depends(catalog_service)]
Csrf = Annotated[str, Header(alias="X-CSRF-Token")]


def category(row: CategoryRow) -> Category:
    return Category(
        name=row.name,
        kind=cast(Literal["income", "expense"], row.kind),
        parent_id=row.parent_id,
        icon=row.icon,
        color=row.color,
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
        is_system=row.is_system,
        system_key=cast(Literal["interest_income", "interest_expense"] | None, row.system_key),
    )


@router.get("", response_model=CategoryPage, operation_id="list_categories")
def list_categories(
    identity: Authenticated,
    service: Catalog,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
) -> CategoryPage:
    rows, next_cursor = service.list_categories(identity.user.id, limit, cursor)
    return CategoryPage(items=[category(row) for row in rows], next_cursor=next_cursor)


@router.post(
    "", response_model=Category, status_code=status.HTTP_201_CREATED, operation_id="create_category"
)
def create_category(
    payload: CategoryCreate, identity: Authenticated, service: Catalog, csrf: Csrf
) -> Category:
    return category(service.create_category(identity.user.id, payload.model_dump()))


@router.get("/{id}", response_model=Category, operation_id="get_category")
def get_category(id: UUID, identity: Authenticated, service: Catalog) -> Category:
    return category(service.get(CategoryRow, identity.user.id, id))


@router.patch("/{id}", response_model=Category, operation_id="update_category")
def update_category(
    id: UUID, payload: CategoryUpdate, identity: Authenticated, service: Catalog, csrf: Csrf
) -> Category:
    values = payload.model_dump(exclude_unset=True)
    return category(service.update_category(identity.user.id, id, values))


@router.delete("/{id}", response_model=ActionResult, operation_id="delete_category")
def delete_category(
    id: UUID, identity: Authenticated, service: Catalog, csrf: Csrf
) -> ActionResult:
    service.delete_category(identity.user.id, id)
    return ActionResult(success=True, affected_count=1)
