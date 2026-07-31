from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_auth_service
from app.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    TokenPair,
    UserRegister,
    UserResponse,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: UserRegister,
    service: AuthServiceDep,
) -> UserResponse:
    return await service.register(payload)


@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginRequest,
    service: AuthServiceDep,
) -> TokenPair:
    return await service.login(payload)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshTokenRequest,
    service: AuthServiceDep,
) -> TokenPair:
    return await service.refresh(payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshTokenRequest,
    service: AuthServiceDep,
) -> None:
    await service.logout(payload.refresh_token)
