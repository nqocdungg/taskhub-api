from fastapi import status

from app.core.cache import TaskCache
from app.core.exceptions import AppError
from app.models.entities import Project, User, Workspace
from app.models.enums import ProjectStatus
from app.repositories.project import ProjectRepository
from app.repositories.workspace import WorkspaceRepository
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.access import AccessService


class ProjectService:
    def __init__(
        self,
        repository: ProjectRepository,
        workspace_repository: WorkspaceRepository,
        access_service: AccessService,
        cache: TaskCache,
    ) -> None:
        self._repository = repository
        self._workspace_repository = workspace_repository
        self._access_service = access_service
        self._cache = cache

    async def create(
        self,
        workspace_id: int,
        payload: ProjectCreate,
        current_user: User,
    ) -> ProjectResponse:
        workspace = await self._get_workspace_or_404(workspace_id)
        membership = await self._access_service.require_member(
            workspace.id,
            current_user,
            message="Bạn không phải thành viên của workspace.",
        )
        self._access_service.require_editor(
            membership, current_user, resource_name="project"
        )
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
        await self._access_service.require_member(
            workspace.id,
            current_user,
            message="Bạn không phải thành viên của workspace.",
        )
        projects = await self._repository.list_by_workspace(workspace_id)
        return [ProjectResponse.model_validate(project) for project in projects]

    async def get(
        self,
        project_id: int,
        current_user: User,
    ) -> ProjectResponse:
        project = await self._get_project_or_404(project_id)
        workspace = await self._get_workspace_or_404(project.workspace_id)
        await self._access_service.require_member(
            workspace.id,
            current_user,
            message="Bạn không phải thành viên của workspace.",
        )
        return ProjectResponse.model_validate(project)

    async def update(
        self,
        project_id: int,
        payload: ProjectUpdate,
        current_user: User,
    ) -> ProjectResponse:
        project = await self._get_project_or_404(project_id)
        workspace = await self._get_workspace_or_404(project.workspace_id)
        membership = await self._access_service.require_member(
            workspace.id,
            current_user,
            message="Bạn không phải thành viên của workspace.",
        )
        self._access_service.require_editor(
            membership, current_user, resource_name="project"
        )

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
        membership = await self._access_service.require_member(
            workspace.id,
            current_user,
            message="Bạn không phải thành viên của workspace.",
        )
        self._access_service.require_editor(
            membership, current_user, resource_name="project"
        )
        archived_project = await self._repository.update(
            project,
            {"status": ProjectStatus.ARCHIVED},
        )
        return ProjectResponse.model_validate(archived_project)

    async def delete(self, project_id: int, current_user: User) -> None:
        project = await self._get_project_or_404(project_id)
        workspace = await self._get_workspace_or_404(project.workspace_id)
        membership = await self._access_service.require_member(
            workspace.id,
            current_user,
            message="Bạn không phải thành viên của workspace.",
        )
        self._access_service.require_editor(
            membership, current_user, resource_name="project"
        )
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
