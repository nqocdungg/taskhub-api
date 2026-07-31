from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.scalar(
            select(User).where(User.email == email)
        )
        return result

    async def set_refresh_token_hash(
        self,
        user: User,
        token_hash: str | None,
    ) -> User:
        return await self.update(user, {"refresh_token_hash": token_hash})
