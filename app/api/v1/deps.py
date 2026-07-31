from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db_session
from app.models.entities import User
from app.repositories.task import TaskRepository
from app.repositories.user import UserRepository
from app.services.auth import AuthService
from app.services.task import TaskService
from app.services.user import UserService

DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
bearer_scheme = HTTPBearer(auto_error=False)
BearerCredentialsDep = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]


async def get_current_user(
    credentials: BearerCredentialsDep,
    session: DbSessionDep,
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Access token không hợp lệ hoặc đã hết hạn.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise credentials_error

    try:
        user_id = decode_token(credentials.credentials, "access")
    except ValueError as error:
        raise credentials_error from error

    user = await UserRepository(session).get(user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def get_task_service(session: DbSessionDep) -> TaskService:
    return TaskService(repository=TaskRepository(session))


def get_auth_service(session: DbSessionDep) -> AuthService:
    return AuthService(repository=UserRepository(session))


def get_user_service(session: DbSessionDep) -> UserService:
    return UserService(repository=UserRepository(session))
