from fastapi import BackgroundTasks, status
from sqlalchemy.exc import IntegrityError

from app.core.cache import TaskCache
from app.core.exceptions import AppError
from app.core.rbac import EDIT_ROLES, is_admin
from app.models.entities import Project, Task, User, WorkspaceMember
from app.models.enums import TaskPriority, TaskStatus
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.repositories.user import UserRepository
from app.repositories.workspace import WorkspaceRepository
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.notification import EmailNotificationService


class TaskService:
    def __init__(
        self,
        repository: TaskRepository,
        project_repository: ProjectRepository,
        workspace_repository: WorkspaceRepository,
        user_repository: UserRepository,
        cache: TaskCache,
        notification_service: EmailNotificationService,
    ) -> None:
        self._repository = repository
        self._project_repository = project_repository
        self._workspace_repository = workspace_repository
        self._user_repository = user_repository
        self._cache = cache
        self._notification_service = notification_service

    async def create(
        self,
        project_id: int,
        payload: TaskCreate,
        current_user: User,
        background_tasks: BackgroundTasks,
    ) -> TaskResponse:
        project = await self._get_project_or_404(project_id)
        membership = await self._require_member(project, current_user)
        self._require_editor(membership, current_user)
        await self._validate_assignee(project, payload.assignee_id)

        task_data = {"project_id": project_id, **payload.model_dump()}
        task_data["created_by"] = current_user.id
        try:
            task = await self._repository.create(task_data)
        except IntegrityError as error:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Không thể tạo task với dữ liệu đã cung cấp.",
            ) from error
        await self._cache.invalidate_project(project_id)
        await self._schedule_assignment_notification(task, background_tasks)
        return TaskResponse.model_validate(task)

    async def list(
        self,
        *,
        project_id: int,
        current_user: User,
        page: int,
        limit: int,
        task_status: TaskStatus | None,
        priority: TaskPriority | None,
        assignee_id: int | None,
    ) -> list[TaskResponse]:
        project = await self._get_project_or_404(project_id)
        await self._require_member(project, current_user)
        cached_tasks = await self._cache.get(
            project_id=project_id,
            task_status=task_status,
            priority=priority,
            assignee_id=assignee_id,
            page=page,
            limit=limit,
        )
        if cached_tasks is not None:
            return cached_tasks

        tasks = await self._repository.list_by_project(
            project_id=project_id,
            task_status=task_status,
            priority=priority,
            assignee_id=assignee_id,
            page=page,
            limit=limit,
        )
        response = [TaskResponse.model_validate(task) for task in tasks]
        await self._cache.set(
            project_id=project_id,
            task_status=task_status,
            priority=priority,
            assignee_id=assignee_id,
            page=page,
            limit=limit,
            tasks=response,
        )
        return response

    async def get(self, task_id: int, current_user: User) -> TaskResponse:
        task = await self._get_task_or_404(task_id)
        project = await self._get_project_or_404(task.project_id)
        await self._require_member(project, current_user)
        return TaskResponse.model_validate(task)

    async def update(
        self,
        task_id: int,
        payload: TaskUpdate,
        current_user: User,
        background_tasks: BackgroundTasks,
    ) -> TaskResponse:
        task = await self._get_task_or_404(task_id)
        project = await self._get_project_or_404(task.project_id)
        membership = await self._require_member(project, current_user)
        self._require_editor(membership, current_user)

        previous_assignee_id = task.assignee_id
        changes = payload.model_dump(exclude_unset=True)
        required_fields = {"title", "status", "priority"}
        updated_required_fields = required_fields & changes.keys()
        if any(changes[field] is None for field in updated_required_fields):
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="title, status và priority không được để trống.",
            )
        if "assignee_id" in changes:
            await self._validate_assignee(project, changes["assignee_id"])

        try:
            updated_task = await self._repository.update(task, changes)
        except IntegrityError as error:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Không thể cập nhật task với dữ liệu đã cung cấp.",
            ) from error
        await self._cache.invalidate_project(task.project_id)
        if updated_task.assignee_id != previous_assignee_id:
            await self._schedule_assignment_notification(
                updated_task,
                background_tasks,
            )
        return TaskResponse.model_validate(updated_task)

    async def delete(self, task_id: int, current_user: User) -> None:
        task = await self._get_task_or_404(task_id)
        project = await self._get_project_or_404(task.project_id)
        membership = await self._require_member(project, current_user)
        self._require_editor(membership, current_user)
        await self._repository.delete(task)
        await self._cache.invalidate_project(task.project_id)

    async def _get_task_or_404(self, task_id: int) -> Task:
        task = await self._repository.get(task_id)
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

    async def _require_member(
        self,
        project: Project,
        user: User,
    ) -> WorkspaceMember | None:
        if is_admin(user):
            return None
        membership = await self._workspace_repository.get_membership(
            project.workspace_id,
            user.id,
        )
        if membership is None:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Bạn không phải thành viên của workspace chứa task.",
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
                message="Role VIEWER chỉ được xem task.",
            )

    async def _schedule_assignment_notification(
        self,
        task: Task,
        background_tasks: BackgroundTasks,
    ) -> None:
        if task.assignee_id is None:
            return
        assignee = await self._user_repository.get(task.assignee_id)
        if assignee is None:
            return
        background_tasks.add_task(
            self._notification_service.send_task_assignment_email,
            recipient_email=assignee.email,
            recipient_name=assignee.full_name,
            task_id=task.id,
            task_title=task.title,
        )

    async def _validate_assignee(
        self,
        project: Project,
        assignee_id: object,
    ) -> None:
        if assignee_id is None:
            return
        if not isinstance(assignee_id, int):
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="assignee_id không hợp lệ.",
            )
        membership = await self._workspace_repository.get_membership(
            project.workspace_id,
            assignee_id,
        )
        if membership is None:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Assignee phải là thành viên của workspace.",
            )
