from fastapi import status

from app.core.cache import TaskCache
from app.core.exceptions import AppError
from app.core.rbac import EDIT_ROLES, is_admin
from app.models.entities import Project, User, Workspace, WorkspaceMember
from app.models.enums import ProjectStatus
from app.repositories.project import ProjectRepository
from app.repositories.workspace import WorkspaceRepository
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate


class ProjectService:
    def __init__(
        self,
        repository: ProjectRepository,
        workspace_repository: WorkspaceRepository,
        cache: TaskCache,
    ) -> None:
        self._repository = repository
        self._workspace_repository = workspace_repository
        self._cache = cache

    async def create(
        self,
        workspace_id: int,
        payload: ProjectCreate,
        current_user: User,
    ) -> ProjectResponse:
        workspace = await self._get_workspace_or_404(workspace_id)
        membership = await self._require_member(workspace, current_user)
        self._require_editor(membership, current_user)
        project = await self._repository.create(
            {"workspace_id": workspace_id, **payload.model_dump()}
        )
        return ProjectResponse.model_validate(project)

    async def list(
        self,
        workspace_id: int,
        current_user: User,
    ) -> list[ProjectResponse]:
        workspace = await self._get_workspace_or_404(workspace_id)
        await self._require_member(workspace, current_user)
        projects = await self._repository.list_by_workspace(workspace_id)
        return [ProjectResponse.model_validate(project) for project in projects]

    async def get(
        self,
        project_id: int,
        current_user: User,
    ) -> ProjectResponse:
        project = await self._get_project_or_404(project_id)
        workspace = await self._get_workspace_or_404(project.workspace_id)
        await self._require_member(workspace, current_user)
        return ProjectResponse.model_validate(project)

    async def update(
        self,
        project_id: int,
        payload: ProjectUpdate,
        current_user: User,
    ) -> ProjectResponse:
        project = await self._get_project_or_404(project_id)
        workspace = await self._get_workspace_or_404(project.workspace_id)
        membership = await self._require_member(workspace, current_user)
        self._require_editor(membership, current_user)

        changes = payload.model_dump(exclude_unset=True)
        if changes.get("name") is None and "name" in changes:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="Project name không được để trống.",
            )
        updated_project = await self._repository.update(project, changes)
        return ProjectResponse.model_validate(updated_project)

    async def archive(
        self,
        project_id: int,
        current_user: User,
    ) -> ProjectResponse:
        project = await self._get_project_or_404(project_id)
        workspace = await self._get_workspace_or_404(project.workspace_id)
        membership = await self._require_member(workspace, current_user)
        self._require_editor(membership, current_user)
        archived_project = await self._repository.update(
            project,
            {"status": ProjectStatus.ARCHIVED},
        )
        return ProjectResponse.model_validate(archived_project)

    async def delete(self, project_id: int, current_user: User) -> None:
        project = await self._get_project_or_404(project_id)
        workspace = await self._get_workspace_or_404(project.workspace_id)
        membership = await self._require_member(workspace, current_user)
        self._require_editor(membership, current_user)
        await self._repository.delete(project)
        await self._cache.invalidate_project(project_id)

    async def _get_workspace_or_404(self, workspace_id: int) -> Workspace:
        workspace = await self._workspace_repository.get(workspace_id)
        if workspace is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Workspace {workspace_id} không tồn tại.",
            )
        return workspace

    async def _get_project_or_404(self, project_id: int) -> Project:
        project = await self._repository.get(project_id)
        if project is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Project {project_id} không tồn tại.",
            )
        return project

    async def _require_member(
        self,
        workspace: Workspace,
        user: User,
    ) -> WorkspaceMember | None:
        if is_admin(user):
            return None
        membership = await self._workspace_repository.get_membership(
            workspace.id,
            user.id,
        )
        if membership is None:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Bạn không phải thành viên của workspace.",
            )
        return membership

    @staticmethod
    def _require_editor(
        membership: WorkspaceMember | None,
        user: User,
    ) -> None:
        if is_admin(user):
            return
        if membership is None or membership.role not in EDIT_ROLES:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Role VIEWER chỉ được xem project.",
            )
