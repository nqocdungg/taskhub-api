from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Label, TaskLabel
from app.repositories.base import BaseRepository


class LabelRepository(BaseRepository[Label]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Label, session)

    async def list_by_project(self, project_id: int) -> list[Label]:
        result = await self._session.scalars(
            select(Label)
            .where(Label.project_id == project_id)
            .order_by(Label.id)
        )
        return list(result.all())

    async def get_task_label(
        self,
        task_id: int,
        label_id: int,
    ) -> TaskLabel | None:
        return await self._session.get(TaskLabel, (task_id, label_id))

    async def attach_to_task(
        self,
        task_id: int,
        label_id: int,
    ) -> TaskLabel:
        task_label = TaskLabel(task_id=task_id, label_id=label_id)
        self._session.add(task_label)
        await self._commit()
        return task_label

    async def remove_from_task(self, task_label: TaskLabel) -> None:
        await self._session.delete(task_label)
        await self._commit()
