from fastapi import HTTPException, status

from app.models.entities import Comment, Project, Task, User
from app.repositories.comment import CommentRepository
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.repositories.workspace import WorkspaceRepository
from app.schemas.comment import CommentCreate, CommentResponse


class CommentService:
    def __init__(
        self,
        repository: CommentRepository,
        task_repository: TaskRepository,
        project_repository: ProjectRepository,
        workspace_repository: WorkspaceRepository,
    ) -> None:
        self._repository = repository
        self._task_repository = task_repository
        self._project_repository = project_repository
        self._workspace_repository = workspace_repository

    async def create(
        self,
        task_id: int,
        payload: CommentCreate,
        current_user: User,
    ) -> CommentResponse:
        task = await self._get_task_or_404(task_id)
        project = await self._get_project_or_404(task.project_id)
        await self._require_member(project, current_user.id)
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
        await self._require_member(project, current_user.id)
        if comment.author_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn chỉ được xóa comment của chính mình.",
            )
        await self._repository.delete(comment)

    async def _get_comment_or_404(self, comment_id: int) -> Comment:
        comment = await self._repository.get(comment_id)
        if comment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comment {comment_id} không tồn tại.",
            )
        return comment

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

    async def _require_member(self, project: Project, user_id: int) -> None:
        membership = await self._workspace_repository.get_membership(
            project.workspace_id,
            user_id,
        )
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không phải thành viên của workspace chứa task.",
            )
