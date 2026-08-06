from fastapi import status
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError
from app.models.entities import Label, Project, Task, User
from app.repositories.label import LabelRepository
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.schemas.label import (
    LabelCreate,
    LabelResponse,
    LabelUpdate,
    TaskLabelResponse,
)
from app.services.access import AccessService


class LabelService:
    def __init__(
        self,
        repository: LabelRepository,
        project_repository: ProjectRepository,
        task_repository: TaskRepository,
        access_service: AccessService,
    ) -> None:
        self._repository = repository
        self._project_repository = project_repository
        self._task_repository = task_repository
        self._access_service = access_service

    async def create(
        self,
        project_id: int,
        payload: LabelCreate,
        current_user: User,
    ) -> LabelResponse:
        project = await self._get_project_or_404(project_id)
        membership = await self._access_service.require_member(
            project.workspace_id,
            current_user,
            message="Bạn không phải thành viên của workspace chứa project.",
        )
        self._access_service.require_editor(
            membership, current_user, resource_name="label"
        )
        label = await self._repository.create(
            {"project_id": project_id, **payload.model_dump()}
        )
        return LabelResponse.model_validate(label)

    async def list(
        self,
        project_id: int,
        current_user: User,
    ) -> list[LabelResponse]:
        project = await self._get_project_or_404(project_id)
        await self._access_service.require_member(
            project.workspace_id,
            current_user,
            message="Bạn không phải thành viên của workspace chứa project.",
        )
        labels = await self._repository.list_by_project(project_id)
        return [LabelResponse.model_validate(label) for label in labels]

    async def get(self, label_id: int, current_user: User) -> LabelResponse:
        label = await self._get_label_or_404(label_id)
        project = await self._get_project_or_404(label.project_id)
        await self._access_service.require_member(
            project.workspace_id,
            current_user,
            message="Bạn không phải thành viên của workspace chứa project.",
        )
        return LabelResponse.model_validate(label)

    async def update(
        self,
        label_id: int,
        payload: LabelUpdate,
        current_user: User,
    ) -> LabelResponse:
        label = await self._get_label_or_404(label_id)
        project = await self._get_project_or_404(label.project_id)
        membership = await self._access_service.require_member(
            project.workspace_id,
            current_user,
            message="Bạn không phải thành viên của workspace chứa project.",
        )
        self._access_service.require_editor(
            membership, current_user, resource_name="label"
        )

        changes = payload.model_dump(exclude_unset=True)
        required_fields = {"name", "color"}
        updated_required_fields = required_fields & changes.keys()
        if any(changes[field] is None for field in updated_required_fields):
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="Label name và color không được để trống.",
            )
        updated_label = await self._repository.update(label, changes)
        return LabelResponse.model_validate(updated_label)

    async def delete(self, label_id: int, current_user: User) -> None:
        label = await self._get_label_or_404(label_id)
        project = await self._get_project_or_404(label.project_id)
        membership = await self._access_service.require_member(
            project.workspace_id,
            current_user,
            message="Bạn không phải thành viên của workspace chứa project.",
        )
        self._access_service.require_editor(
            membership, current_user, resource_name="label"
        )
        await self._repository.delete(label)

    async def attach_to_task(
        self,
        task_id: int,
        label_id: int,
        current_user: User,
    ) -> TaskLabelResponse:
        task = await self._get_task_or_404(task_id)
        project = await self._get_project_or_404(task.project_id)
        membership = await self._access_service.require_member(
            project.workspace_id,
            current_user,
            message="Bạn không phải thành viên của workspace chứa project.",
        )
        self._access_service.require_editor(
            membership, current_user, resource_name="label"
        )
        label = await self._get_label_or_404(label_id)
        self._require_same_project(task, label)

        existing_link = await self._repository.get_task_label(task_id, label_id)
        if existing_link is not None:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                message="Label đã được gắn vào task.",
            )
        try:
            task_label = await self._repository.attach_to_task(task_id, label_id)
        except IntegrityError as error:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                message="Không thể gắn label vào task.",
            ) from error
        return TaskLabelResponse.model_validate(task_label)

    async def remove_from_task(
        self,
        task_id: int,
        label_id: int,
        current_user: User,
    ) -> None:
        task = await self._get_task_or_404(task_id)
        project = await self._get_project_or_404(task.project_id)
        membership = await self._access_service.require_member(
            project.workspace_id,
            current_user,
            message="Bạn không phải thành viên của workspace chứa project.",
        )
        self._access_service.require_editor(
            membership, current_user, resource_name="label"
        )
        label = await self._get_label_or_404(label_id)
        self._require_same_project(task, label)

        task_label = await self._repository.get_task_label(task_id, label_id)
        if task_label is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Label chưa được gắn vào task.",
            )
        await self._repository.remove_from_task(task_label)

    async def _get_label_or_404(self, label_id: int) -> Label:
        label = await self._repository.get(label_id)
        if label is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Label {label_id} không tồn tại.",
            )
        return label

    async def _get_task_or_404(self, task_id: int) -> Task:
        task = await self._task_repository.get(task_id)
        if task is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Task {task_id} không tồn tại.",
            )
        return task

    async def _get_project_or_404(self, project_id: int) -> Project:
        project = await self._project_repository.get(project_id)
        if project is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Project {project_id} không tồn tại.",
            )
        return project

    @staticmethod
    def _require_same_project(task: Task, label: Label) -> None:
        if task.project_id != label.project_id:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Task và label phải thuộc cùng một project.",
            )
