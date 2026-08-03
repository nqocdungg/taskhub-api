from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.models.entities import Label, Project, Task, User, WorkspaceMember
from app.models.enums import WorkspaceMemberRole
from app.repositories.label import LabelRepository
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.repositories.workspace import WorkspaceRepository
from app.schemas.label import (
    LabelCreate,
    LabelResponse,
    LabelUpdate,
    TaskLabelResponse,
)

EDIT_ROLES = {WorkspaceMemberRole.OWNER, WorkspaceMemberRole.EDITOR}


class LabelService:
    def __init__(
        self,
        repository: LabelRepository,
        project_repository: ProjectRepository,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
    ) -> None:
        self._repository = repository
        self._project_repository = project_repository
        self._task_repository = task_repository
        self._workspace_repository = workspace_repository

    async def create(
        self,
        project_id: int,
        payload: LabelCreate,
        current_user: User,
    ) -> LabelResponse:
        project = await self._get_project_or_404(project_id)
        membership = await self._require_member(project, current_user.id)
        self._require_editor(membership)
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
        await self._require_member(project, current_user.id)
        labels = await self._repository.list_by_project(project_id)
        return [LabelResponse.model_validate(label) for label in labels]

    async def get(self, label_id: int, current_user: User) -> LabelResponse:
        label = await self._get_label_or_404(label_id)
        project = await self._get_project_or_404(label.project_id)
        await self._require_member(project, current_user.id)
        return LabelResponse.model_validate(label)

    async def update(
        self,
        label_id: int,
        payload: LabelUpdate,
        current_user: User,
    ) -> LabelResponse:
        label = await self._get_label_or_404(label_id)
        project = await self._get_project_or_404(label.project_id)
        membership = await self._require_member(project, current_user.id)
        self._require_editor(membership)

        changes = payload.model_dump(exclude_unset=True)
        required_fields = {"name", "color"}
        updated_required_fields = required_fields & changes.keys()
        if any(changes[field] is None for field in updated_required_fields):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Label name và color không được để trống.",
            )
        updated_label = await self._repository.update(label, changes)
        return LabelResponse.model_validate(updated_label)

    async def delete(self, label_id: int, current_user: User) -> None:
        label = await self._get_label_or_404(label_id)
        project = await self._get_project_or_404(label.project_id)
        membership = await self._require_member(project, current_user.id)
        self._require_editor(membership)
        await self._repository.delete(label)

    async def attach_to_task(
        self,
        task_id: int,
        label_id: int,
        current_user: User,
    ) -> TaskLabelResponse:
        task = await self._get_task_or_404(task_id)
        project = await self._get_project_or_404(task.project_id)
        membership = await self._require_member(project, current_user.id)
        self._require_editor(membership)
        label = await self._get_label_or_404(label_id)
        self._require_same_project(task, label)

        existing_link = await self._repository.get_task_label(task_id, label_id)
        if existing_link is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Label đã được gắn vào task.",
            )
        try:
            task_label = await self._repository.attach_to_task(task_id, label_id)
        except IntegrityError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Không thể gắn label vào task.",
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
        membership = await self._require_member(project, current_user.id)
        self._require_editor(membership)
        label = await self._get_label_or_404(label_id)
        self._require_same_project(task, label)

        task_label = await self._repository.get_task_label(task_id, label_id)
        if task_label is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Label chưa được gắn vào task.",
            )
        await self._repository.remove_from_task(task_label)

    async def _get_label_or_404(self, label_id: int) -> Label:
        label = await self._repository.get(label_id)
        if label is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Label {label_id} không tồn tại.",
            )
        return label

    async def _get_task_or_404(self, task_id: int) -> Task:
        task = await self._task_repository.get(task_id)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} không tồn tại.",
            )
        return task

    async def _get_project_or_404(self, project_id: int) -> Project:
        project = await self._project_repository.get(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} không tồn tại.",
            )
        return project

    async def _require_member(
        self,
        project: Project,
        user_id: int,
    ) -> WorkspaceMember:
        membership = await self._workspace_repository.get_membership(
            project.workspace_id,
            user_id,
        )
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không phải thành viên của workspace chứa project.",
            )
        return membership

    @staticmethod
    def _require_editor(membership: WorkspaceMember) -> None:
        if membership.role not in EDIT_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Role VIEWER chỉ được xem label.",
            )

    @staticmethod
    def _require_same_project(task: Task, label: Label) -> None:
        if task.project_id != label.project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task và label phải thuộc cùng một project.",
            )
