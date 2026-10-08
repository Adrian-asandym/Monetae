from fastapi import APIRouter

from monetae.api.routers.auth import ERROR_RESPONSES, CsrfHeader
from monetae.api.schemas.auth import CurrentUser, UserUpdate
from monetae.api.security import Authenticated, Service, profile

router = APIRouter(prefix="/api/v1/users", tags=["users"], responses=ERROR_RESPONSES)


@router.get(
    "/me",
    response_model=CurrentUser,
    response_model_exclude_unset=True,
    operation_id="get_current_user",
)
def get_current_user(identity: Authenticated) -> CurrentUser:
    return profile(identity.user)


@router.patch(
    "/me",
    response_model=CurrentUser,
    response_model_exclude_unset=True,
    operation_id="update_current_user",
)
def update_current_user(
    payload: UserUpdate, identity: Authenticated, service: Service, csrf: CsrfHeader
) -> CurrentUser:
    return profile(service.update_user(identity.user, payload.model_dump(exclude_unset=True)))
