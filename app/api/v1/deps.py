from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db_session
from app.models.entities import User
from app.repositories.comment import CommentRepository
from app.repositories.label import LabelRepository
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.repositories.user import UserRepository
from app.repositories.workspace import WorkspaceRepository
from app.services.auth import AuthService
from app.services.comment import CommentService
from app.services.label import LabelService
from app.services.project import ProjectService
from app.services.task import TaskService
from app.services.user import UserService
from app.services.workspace import WorkspaceService

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
    return TaskService(
        repository=TaskRepository(session),
        project_repository=ProjectRepository(session),
        workspace_repository=WorkspaceRepository(session),
    )


def get_auth_service(session: DbSessionDep) -> AuthService:
    return AuthService(repository=UserRepository(session))


def get_user_service(session: DbSessionDep) -> UserService:
    return UserService(repository=UserRepository(session))


def get_workspace_service(session: DbSessionDep) -> WorkspaceService:
    return WorkspaceService(
        repository=WorkspaceRepository(session),
        user_repository=UserRepository(session),
    )


def get_project_service(session: DbSessionDep) -> ProjectService:
    return ProjectService(
        repository=ProjectRepository(session),
        workspace_repository=WorkspaceRepository(session),
    )


def get_label_service(session: DbSessionDep) -> LabelService:
    return LabelService(
        repository=LabelRepository(session),
        project_repository=ProjectRepository(session),
        task_repository=TaskRepository(session),
        workspace_repository=WorkspaceRepository(session),
    )


def get_comment_service(session: DbSessionDep) -> CommentService:
    return CommentService(
        repository=CommentRepository(session),
        task_repository=TaskRepository(session),
        project_repository=ProjectRepository(session),
        workspace_repository=WorkspaceRepository(session),
    )
