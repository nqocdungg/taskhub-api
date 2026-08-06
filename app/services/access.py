from fastapi import status

from app.core.exceptions import AppError
from app.core.rbac import EDIT_ROLES, is_admin
from app.models.entities import User, Workspace, WorkspaceMember
from app.repositories.workspace import WorkspaceRepository


class AccessService:
    def __init__(self, repository: WorkspaceRepository) -> None:
        self._repository = repository

    async def get_membership(
        self,
        workspace_id: int,
        user_id: int,
    ) -> WorkspaceMember | None:
        return await self._repository.get_membership(workspace_id, user_id)

    async def require_member(
        self,
        workspace_id: int,
        user: User,
        *,
        message: str,
    ) -> WorkspaceMember | None:
        if is_admin(user):
            return None
        membership = await self.get_membership(workspace_id, user.id)
        if membership is None:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                message=message,
            )
        return membership

    @staticmethod
    def require_editor(
        membership: WorkspaceMember | None,
        user: User,
        *,
        resource_name: str,
    ) -> None:
        if is_admin(user):
            return
        if membership is None or membership.role not in EDIT_ROLES:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                message=f"Role VIEWER chỉ được xem {resource_name}.",
            )

    @staticmethod
    def require_owner(workspace: Workspace, user: User) -> None:
        if not is_admin(user) and workspace.owner_id != user.id:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Chỉ owner mới có quyền thực hiện thao tác này.",
            )

    @staticmethod
    def require_comment_author(author_id: int, user: User) -> None:
        if not is_admin(user) and author_id != user.id:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Bạn chỉ được xóa comment của chính mình.",
            )
