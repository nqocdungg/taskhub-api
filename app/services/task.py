from fastapi import HTTPException, status

from app.repositories.task import TaskRepository
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate


class TaskService:
    """Business logic cho Task: orchestrate repository, kiểm tra tồn tại"""

    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def create(self, payload: TaskCreate) -> TaskResponse:
        return self._repository.create(payload)

    def list(self) -> list[TaskResponse]:
        return self._repository.list()

    def get(self, task_id: int) -> TaskResponse:
        task = self._repository.get(task_id)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} không tồn tại.",
            )
        return task

    def update(self, task_id: int, payload: TaskUpdate) -> TaskResponse:
        changes = payload.model_dump(exclude_unset=True)
        required_fields = {"title", "status", "priority"}
        updated_required_fields = required_fields & changes.keys()
        if any(changes[field] is None for field in updated_required_fields):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="title, status và priority không được trống.",
            )

        task = self._repository.update(task_id, changes)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} không tồn tại.",
            )
        return task

    def delete(self, task_id: int) -> None:
        deleted = self._repository.delete(task_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} không tồn tại.",
            )
