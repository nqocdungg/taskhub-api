from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Workspace, WorkspaceMember
from app.models.enums import WorkspaceMemberRole
from app.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Workspace, session)

    async def create_with_owner(
        self,
        *,
        name: str,
        owner_id: int,
    ) -> Workspace:
        workspace = Workspace(name=name, owner_id=owner_id)
        self._session.add(workspace)
        try:
            await self._session.flush()
            self._session.add(
                WorkspaceMember(
                    workspace_id=workspace.id,
                    user_id=owner_id,
                    role=WorkspaceMemberRole.OWNER,
                )
            )
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise
        await self._session.refresh(workspace)
        return workspace

    async def get_membership(
        self,
        workspace_id: int,
        user_id: int,
    ) -> WorkspaceMember | None:
        member: WorkspaceMember | None = await self._session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        return member

    async def list_for_user(self, user_id: int) -> list[Workspace]:
        result = await self._session.scalars(
            select(Workspace)
            .join(WorkspaceMember)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.id)
        )
        return list(result.all())

    async def add_member(
        self,
        *,
        workspace_id: int,
        user_id: int,
        role: WorkspaceMemberRole,
    ) -> WorkspaceMember:
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
        )
        self._session.add(member)
        await self._commit()
        await self._session.refresh(member)
        return member

    async def remove_member(self, member: WorkspaceMember) -> None:
        await self._session.delete(member)
        await self._commit()
