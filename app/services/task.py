from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.repositories.task import TaskRepository
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate


class TaskService:
    """Business logic cho Task: orchestrate repository, kiểm tra tồn tại"""

    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    async def create(self, payload: TaskCreate) -> TaskResponse:
        try:
            task = await self._repository.create(payload.model_dump())
        except IntegrityError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="project_id, assignee_id hoặc created_by không hợp lệ.",
            ) from error
        return TaskResponse.model_validate(task)

    async def list(self, *, page: int, limit: int) -> list[TaskResponse]:
        tasks = await self._repository.list(page=page, limit=limit)
        return [TaskResponse.model_validate(task) for task in tasks]

    async def get(self, task_id: int) -> TaskResponse:
        task = await self._repository.get(task_id)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} không tồn tại.",
            )
        return TaskResponse.model_validate(task)

    async def update(self, task_id: int, payload: TaskUpdate) -> TaskResponse:
        changes = payload.model_dump(exclude_unset=True)
        required_fields = {"title", "status", "priority"}
        updated_required_fields = required_fields & changes.keys()
        if any(changes[field] is None for field in updated_required_fields):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="title, status và priority không được trống.",
            )

        task = await self._repository.get(task_id)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} không tồn tại.",
            )

        try:
            updated_task = await self._repository.update(task, changes)
        except IntegrityError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="assignee_id không hợp lệ.",
            ) from error
        return TaskResponse.model_validate(updated_task)

    async def delete(self, task_id: int) -> None:
        task = await self._repository.get(task_id)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} không tồn tại.",
            )
        await self._repository.delete(task)
