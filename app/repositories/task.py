from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Task
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Task, session)

    async def list_by_project(
        self,
        *,
        project_id: int,
        page: int,
        limit: int,
    ) -> list[Task]:
        offset = (page - 1) * limit
        result = await self._session.scalars(
            select(Task)
            .where(Task.project_id == project_id)
            .order_by(Task.id)
            .offset(offset)
            .limit(limit)
        )
        return list(result.all())
