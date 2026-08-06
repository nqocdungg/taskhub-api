from fastapi import status

from app.core.exceptions import AppError
from app.models.entities import Comment, Project, Task, User
from app.repositories.comment import CommentRepository
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.schemas.comment import CommentCreate, CommentResponse
from app.services.access import AccessService


class CommentService:
    def __init__(
        self,
        repository: CommentRepository,
        task_repository: TaskRepository,
        project_repository: ProjectRepository,
        access_service: AccessService,
    ) -> None:
        self._repository = repository
        self._task_repository = task_repository
        self._project_repository = project_repository
        self._access_service = access_service

    async def create(
        self,
        task_id: int,
        payload: CommentCreate,
        current_user: User,
    ) -> CommentResponse:
        task = await self._get_task_or_404(task_id)
        project = await self._get_project_or_404(task.project_id)
        membership = await self._access_service.require_member(
            project.workspace_id,
            current_user,
            message="Bạn không phải thành viên của workspace chứa task.",
        )
        self._access_service.require_editor(
            membership, current_user, resource_name="comment"
        )
        comment = await self._repository.create(
            {
                "task_id": task_id,
                "author_id": current_user.id,
                "content": payload.content,
            }
        )
        return CommentResponse.model_validate(comment)

    async def delete(self, comment_id: int, current_user: User) -> None:
        comment = await self._get_comment_or_404(comment_id)
        task = await self._get_task_or_404(comment.task_id)
        project = await self._get_project_or_404(task.project_id)
        membership = await self._access_service.require_member(
            project.workspace_id,
            current_user,
            message="Bạn không phải thành viên của workspace chứa task.",
        )
        self._access_service.require_editor(
            membership, current_user, resource_name="comment"
        )
        self._access_service.require_comment_author(
            comment.author_id,
            current_user,
        )
        await self._repository.delete(comment)

    async def _get_comment_or_404(self, comment_id: int) -> Comment:
        comment = await self._repository.get(comment_id)
        if comment is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Comment {comment_id} không tồn tại.",
            )
        return comment

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
