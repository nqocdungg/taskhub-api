from fastapi import status
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError
from app.models.entities import User, Workspace
from app.repositories.user import UserRepository
from app.repositories.workspace import WorkspaceRepository
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberCreate,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
)


class WorkspaceService:
    def __init__(
        self,
        repository: WorkspaceRepository,
        user_repository: UserRepository,
    ) -> None:
        self._repository = repository
        self._user_repository = user_repository

    async def create(
        self,
        payload: WorkspaceCreate,
        current_user: User,
    ) -> WorkspaceResponse:
        workspace = await self._repository.create_with_owner(
            name=payload.name,
            owner_id=current_user.id,
        )
        return WorkspaceResponse.model_validate(workspace)

    async def get(
        self,
        workspace_id: int,
        current_user: User,
    ) -> WorkspaceResponse:
        workspace = await self._get_or_404(workspace_id)
        await self._require_member(workspace, current_user.id)
        return WorkspaceResponse.model_validate(workspace)

    async def list(self, current_user: User) -> list[WorkspaceResponse]:
        workspaces = await self._repository.list_for_user(current_user.id)
        return [
            WorkspaceResponse.model_validate(workspace)
            for workspace in workspaces
        ]

    async def update(
        self,
        workspace_id: int,
        payload: WorkspaceUpdate,
        current_user: User,
    ) -> WorkspaceResponse:
        workspace = await self._get_or_404(workspace_id)
        self._require_owner(workspace, current_user.id)
        changes = payload.model_dump(exclude_unset=True)
        if changes.get("name") is None and "name" in changes:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="Workspace name không được để trống.",
            )
        updated_workspace = await self._repository.update(workspace, changes)
        return WorkspaceResponse.model_validate(updated_workspace)

    async def delete(self, workspace_id: int, current_user: User) -> None:
        workspace = await self._get_or_404(workspace_id)
        self._require_owner(workspace, current_user.id)
        await self._repository.delete(workspace)

    async def invite_member(
        self,
        workspace_id: int,
        payload: WorkspaceMemberCreate,
        current_user: User,
    ) -> WorkspaceMemberResponse:
        workspace = await self._get_or_404(workspace_id)
        self._require_owner(workspace, current_user.id)

        user = await self._user_repository.get(payload.user_id)
        if user is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"User {payload.user_id} không tồn tại.",
            )
        existing_member = await self._repository.get_membership(
            workspace_id,
            payload.user_id,
        )
        if existing_member is not None:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                message="User đã là thành viên của workspace.",
            )

        try:
            member = await self._repository.add_member(
                workspace_id=workspace_id,
                user_id=payload.user_id,
                role=payload.role,
            )
        except IntegrityError as error:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                message="Không thể thêm thành viên vào workspace.",
            ) from error
        return WorkspaceMemberResponse.model_validate(member)

    async def remove_member(
        self,
        workspace_id: int,
        user_id: int,
        current_user: User,
    ) -> None:
        workspace = await self._get_or_404(workspace_id)
        self._require_owner(workspace, current_user.id)
        if user_id == workspace.owner_id:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Không thể xóa owner khỏi workspace.",
            )

        member = await self._repository.get_membership(workspace_id, user_id)
        if member is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Thành viên không tồn tại trong workspace.",
            )
        await self._repository.remove_member(member)

    async def _get_or_404(self, workspace_id: int) -> Workspace:
        workspace = await self._repository.get(workspace_id)
        if workspace is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Workspace {workspace_id} không tồn tại.",
            )
        return workspace

    async def _require_member(self, workspace: Workspace, user_id: int) -> None:
        member = await self._repository.get_membership(workspace.id, user_id)
        if member is None:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Bạn không phải thành viên của workspace.",
            )

    @staticmethod
    def _require_owner(workspace: Workspace, user_id: int) -> None:
        if workspace.owner_id != user_id:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Chỉ owner mới có quyền thực hiện thao tác này.",
            )
