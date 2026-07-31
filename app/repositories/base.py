from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base


class BaseRepository[ModelT: Base]:
    def __init__(self, model: type[ModelT], session: AsyncSession) -> None:
        self._model = model
        self._session = session

    async def create(self, data: dict[str, object]) -> ModelT:
        instance = self._model(**data)
        self._session.add(instance)
        await self._commit()
        await self._session.refresh(instance)
        return instance

    async def get(self, instance_id: int) -> ModelT | None:
        return await self._session.get(self._model, instance_id)

    async def list(self, *, page: int, limit: int) -> list[ModelT]:
        offset = (page - 1) * limit
        primary_key = inspect(self._model).primary_key[0]
        result = await self._session.scalars(
            select(self._model)
            .order_by(primary_key)
            .offset(offset)
            .limit(limit)
        )
        return list(result.all())

    async def update(
        self,
        instance: ModelT,
        changes: dict[str, object],
    ) -> ModelT:
        for field, value in changes.items():
            setattr(instance, field, value)
        await self._commit()
        await self._session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self._session.delete(instance)
        await self._commit()

    async def _commit(self) -> None:
        try:
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise
