from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, status

from monetae.api.routers.auth import ERROR_RESPONSES
from monetae.api.schemas.auth import ActionResult
from monetae.api.schemas.common import ArchiveRequest
from monetae.api.schemas.tags import Tag, TagCreate, TagPage, TagUpdate
from monetae.api.security import Authenticated, Database, settings_for
from monetae.db.models import Tag as TagRow
from monetae.services.catalog import CatalogService

router = APIRouter(prefix="/api/v1/tags", tags=["tags"], responses=ERROR_RESPONSES)


def catalog_service(request: Request, db: Database) -> CatalogService:
    return CatalogService(db, settings_for(request).secret_key)


Catalog = Annotated[CatalogService, Depends(catalog_service)]
Csrf = Annotated[str, Header(alias="X-CSRF-Token")]


def tag(row: TagRow) -> Tag:
    return Tag(
        name=row.name,
        color=row.color,
        icon=row.icon,
        emoji=row.emoji,
        sort_order=row.sort_order,
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
        archived_at=row.archived_at,
    )


@router.get("", response_model=TagPage, operation_id="list_tags")
def list_tags(
    identity: Authenticated,
    service: Catalog,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
    include_archived: bool = False,
) -> TagPage:
    rows, next_cursor = service.list_tags(identity.user.id, limit, cursor, include_archived)
    return TagPage(items=[tag(row) for row in rows], next_cursor=next_cursor)


@router.post("", response_model=Tag, status_code=status.HTTP_201_CREATED, operation_id="create_tag")
def create_tag(payload: TagCreate, identity: Authenticated, service: Catalog, csrf: Csrf) -> Tag:
    return tag(service.create_tag(identity.user.id, payload.model_dump()))


@router.get("/{id}", response_model=Tag, operation_id="get_tag")
def get_tag(id: UUID, identity: Authenticated, service: Catalog) -> Tag:
    return tag(service.get(TagRow, identity.user.id, id))


@router.patch("/{id}", response_model=Tag, operation_id="update_tag")
def update_tag(
    id: UUID, payload: TagUpdate, identity: Authenticated, service: Catalog, csrf: Csrf
) -> Tag:
    values = payload.model_dump(exclude_unset=True)
    return tag(service.update_tag(identity.user.id, id, values))


@router.delete("/{id}", response_model=ActionResult, operation_id="delete_tag")
def delete_tag(id: UUID, identity: Authenticated, service: Catalog, csrf: Csrf) -> ActionResult:
    service.delete(TagRow, identity.user.id, id)
    return ActionResult(success=True, affected_count=1)


@router.post("/{id}/archive", response_model=Tag, operation_id="archive_tag")
def archive_tag(
    id: UUID, payload: ArchiveRequest, identity: Authenticated, service: Catalog, csrf: Csrf
) -> Tag:
    return tag(service.archive(TagRow, identity.user.id, id))


@router.post("/{id}/reactivate", response_model=Tag, operation_id="reactivate_tag")
def reactivate_tag(id: UUID, identity: Authenticated, service: Catalog, csrf: Csrf) -> Tag:
    return tag(service.reactivate(TagRow, identity.user.id, id))
