from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import CurrentUserDep, get_user_service
from app.schemas.auth import UserResponse
from app.schemas.user import ChangePasswordRequest, UserUpdate
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["Users"])

UserServiceDep = Annotated[UserService, Depends(get_user_service)]


@router.get("/me", response_model=UserResponse)
async def get_profile(
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> UserResponse:
    return service.get_profile(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    payload: UserUpdate,
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> UserResponse:
    return await service.update_profile(current_user, payload)


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> None:
    await service.change_password(current_user, payload)
