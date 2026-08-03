from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Project, session)

    async def list_by_workspace(self, workspace_id: int) -> list[Project]:
        result = await self._session.scalars(
            select(Project)
            .where(Project.workspace_id == workspace_id)
            .order_by(Project.id)
        )
        return list(result.all())
