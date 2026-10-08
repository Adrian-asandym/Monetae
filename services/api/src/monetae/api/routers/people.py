from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, status

from monetae.api.routers.auth import ERROR_RESPONSES
from monetae.api.schemas.auth import ActionResult
from monetae.api.schemas.people import Person, PersonCreate, PersonPage, PersonUpdate
from monetae.api.security import Authenticated, Database, settings_for
from monetae.db.models import Person as PersonRow
from monetae.services.catalog import CatalogService

router = APIRouter(prefix="/api/v1/people", tags=["people"], responses=ERROR_RESPONSES)


def catalog_service(request: Request, db: Database) -> CatalogService:
    return CatalogService(db, settings_for(request).secret_key)


Catalog = Annotated[CatalogService, Depends(catalog_service)]
Csrf = Annotated[str, Header(alias="X-CSRF-Token")]


def person(row: PersonRow) -> Person:
    return Person(
        name=row.name,
        aliases=row.aliases,
        note=row.note,
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


@router.get("", response_model=PersonPage, operation_id="list_people")
def list_people(
    identity: Authenticated,
    service: Catalog,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
    q: str | None = None,
) -> PersonPage:
    rows, next_cursor = service.list_people(identity.user.id, limit, cursor, q)
    return PersonPage(items=[person(row) for row in rows], next_cursor=next_cursor)


@router.post(
    "", response_model=Person, status_code=status.HTTP_201_CREATED, operation_id="create_person"
)
def create_person(
    payload: PersonCreate, identity: Authenticated, service: Catalog, csrf: Csrf
) -> Person:
    return person(service.create_person(identity.user.id, payload.model_dump()))


@router.get("/{id}", response_model=Person, operation_id="get_person")
def get_person(id: UUID, identity: Authenticated, service: Catalog) -> Person:
    return person(service.get(PersonRow, identity.user.id, id))


@router.patch("/{id}", response_model=Person, operation_id="update_person")
def update_person(
    id: UUID, payload: PersonUpdate, identity: Authenticated, service: Catalog, csrf: Csrf
) -> Person:
    values = payload.model_dump(exclude_unset=True)
    return person(service.update_person(identity.user.id, id, values))


@router.delete("/{id}", response_model=ActionResult, operation_id="delete_person")
def delete_person(id: UUID, identity: Authenticated, service: Catalog, csrf: Csrf) -> ActionResult:
    service.delete(PersonRow, identity.user.id, id)
    return ActionResult(success=True, affected_count=1)
