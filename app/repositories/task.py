from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Task
from app.models.enums import TaskPriority, TaskStatus
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Task, session)

    async def list_by_project(
        self,
        *,
        project_id: int,
        task_status: TaskStatus | None,
        priority: TaskPriority | None,
        assignee_id: int | None,
        page: int,
        limit: int,
    ) -> list[Task]:
        offset = (page - 1) * limit
        statement = select(Task).where(Task.project_id == project_id)
        if task_status is not None:
            statement = statement.where(Task.status == task_status)
        if priority is not None:
            statement = statement.where(Task.priority == priority)
        if assignee_id is not None:
            statement = statement.where(Task.assignee_id == assignee_id)
        result = await self._session.scalars(
            statement.order_by(Task.id).offset(offset).limit(limit)
        )
        return list(result.all())
