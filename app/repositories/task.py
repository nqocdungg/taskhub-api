from datetime import UTC, datetime

from app.schemas.task import TaskCreate, TaskResponse


class TaskRepository:
    """Lưu trữ Task tạm thời trong bộ nhớ."""

    def __init__(self) -> None:
        self._items: dict[int, TaskResponse] = {}
        self._next_id = 1

    def create(self, payload: TaskCreate) -> TaskResponse:
        task = TaskResponse(
            id=self._next_id,
            created_at=datetime.now(UTC),
            **payload.model_dump(),
        )
        self._items[task.id] = task
        self._next_id += 1
        return task

    def list(self) -> list[TaskResponse]:
        return list(self._items.values())

    def get(self, task_id: int) -> TaskResponse | None:
        return self._items.get(task_id)

    def update(
        self, task_id: int, changes: dict[str, object]
    ) -> TaskResponse | None:
        task = self._items.get(task_id)
        if task is None:
            return None
        updated_task = task.model_copy(update=changes)
        self._items[task_id] = updated_task
        return updated_task

    def delete(self, task_id: int) -> bool:
        return self._items.pop(task_id, None) is not None
