import hmac

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.security import (
    create_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.entities import User
from app.models.enums import UserRole
from app.repositories.user import UserRepository
from app.schemas.auth import (
    LoginRequest,
    TokenPair,
    UserRegister,
    UserResponse,
)


class AuthService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def register(self, payload: UserRegister) -> UserResponse:
        email = str(payload.email)
        if await self._repository.get_by_email(email) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email đã được sử dụng.",
            )

        try:
            user = await self._repository.create(
                {
                    "email": email,
                    "full_name": payload.full_name,
                    "hashed_password": hash_password(payload.password),
                    "role": UserRole.MEMBER,
                    "is_active": True,
                }
            )
        except IntegrityError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email đã được sử dụng.",
            ) from error

        return UserResponse.model_validate(user)

    async def login(self, payload: LoginRequest) -> TokenPair:
        user = await self._repository.get_by_email(str(payload.email))
        if user is None or not verify_password(
            payload.password,
            user.hashed_password,
        ):
            raise self._unauthorized("Email hoặc mật khẩu không chính xác.")
        self._ensure_active(user)
        return await self._issue_token_pair(user)

    async def refresh(self, refresh_token: str) -> TokenPair:
        user = await self._get_refresh_token_owner(refresh_token)
        return await self._issue_token_pair(user)

    async def logout(self, refresh_token: str) -> None:
        user = await self._get_refresh_token_owner(refresh_token)
        await self._repository.set_refresh_token_hash(user, None)

    async def _issue_token_pair(self, user: User) -> TokenPair:
        access_token = create_token(user.id, "access")
        refresh_token = create_token(user.id, "refresh")
        await self._repository.set_refresh_token_hash(
            user,
            hash_refresh_token(refresh_token),
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def _get_refresh_token_owner(self, refresh_token: str) -> User:
        try:
            user_id = decode_token(refresh_token, "refresh")
        except ValueError as error:
            raise self._unauthorized(str(error)) from error

        user = await self._repository.get(user_id)
        if user is None:
            raise self._unauthorized("Refresh token không hợp lệ.")
        self._ensure_active(user)

        token_hash = hash_refresh_token(refresh_token)
        if user.refresh_token_hash is None or not hmac.compare_digest(
            user.refresh_token_hash,
            token_hash,
        ):
            raise self._unauthorized(
                "Refresh token đã bị thu hồi hoặc đã được sử dụng."
            )
        return user

    @staticmethod
    def _ensure_active(user: User) -> None:
        if not user.is_active:
            raise AuthService._unauthorized(
                "Tài khoản đã bị vô hiệu hóa."
            )

    @staticmethod
    def _unauthorized(detail: str) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )
