from fastapi import status
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError
from app.core.security import hash_password, verify_password
from app.models.entities import User
from app.repositories.user import UserRepository
from app.schemas.auth import UserResponse
from app.schemas.user import ChangePasswordRequest, UserUpdate


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    @staticmethod
    def get_profile(user: User) -> UserResponse:
        return UserResponse.model_validate(user)

    async def update_profile(
        self,
        user: User,
        payload: UserUpdate,
    ) -> UserResponse:
        changes = payload.model_dump(exclude_unset=True)
        email = changes.get("email")
        if email is not None:
            normalized_email = str(email)
            existing_user = await self._repository.get_by_email(normalized_email)
            if existing_user is not None and existing_user.id != user.id:
                raise AppError(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Email đã được sử dụng.",
                )
            changes["email"] = normalized_email

        try:
            updated_user = await self._repository.update(user, changes)
        except IntegrityError as error:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                message="Email đã được sử dụng.",
            ) from error
        return UserResponse.model_validate(updated_user)

    async def change_password(
        self,
        user: User,
        payload: ChangePasswordRequest,
    ) -> None:
        if not verify_password(
            payload.current_password,
            user.hashed_password,
        ):
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Mật khẩu hiện tại không chính xác.",
            )

        await self._repository.update(
            user,
            {
                "hashed_password": hash_password(payload.new_password),
                "refresh_token_hash": None,
            },
        )
