from pydantic import TypeAdapter, ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.models.enums import TaskPriority, TaskStatus
from app.schemas.task import TaskResponse

TASK_CACHE_TTL_SECONDS = 60
TASK_LIST_ADAPTER = TypeAdapter(list[TaskResponse])


class TaskCache:
    def __init__(self, client: Redis) -> None:
        self._client = client

    async def get(
        self,
        *,
        project_id: int,
        task_status: TaskStatus | None,
        priority: TaskPriority | None,
        assignee_id: int | None,
        page: int,
        limit: int,
    ) -> list[TaskResponse] | None:
        key = self._build_key(
            project_id=project_id,
            task_status=task_status,
            priority=priority,
            assignee_id=assignee_id,
            page=page,
            limit=limit,
        )
        try:
            cached = await self._client.get(key)
        except RedisError:
            return None

        if cached is None:
            return None

        try:
            return TASK_LIST_ADAPTER.validate_json(cached)
        except ValidationError:
            await self._delete(key)
            return None

    async def set(
        self,
        *,
        project_id: int,
        task_status: TaskStatus | None,
        priority: TaskPriority | None,
        assignee_id: int | None,
        page: int,
        limit: int,
        tasks: list[TaskResponse],
    ) -> None:
        key = self._build_key(
            project_id=project_id,
            task_status=task_status,
            priority=priority,
            assignee_id=assignee_id,
            page=page,
            limit=limit,
        )
        try:
            await self._client.set(
                key,
                TASK_LIST_ADAPTER.dump_json(tasks),
                ex=TASK_CACHE_TTL_SECONDS,
            )
        except RedisError:
            return

    async def invalidate_project(self, project_id: int) -> None:
        pattern = f"taskhub:projects:{project_id}:tasks:*"
        try:
            keys = [key async for key in self._client.scan_iter(match=pattern)]
            if keys:
                await self._client.delete(*keys)
        except RedisError:
            return

    async def _delete(self, key: str) -> None:
        try:
            await self._client.delete(key)
        except RedisError:
            return

    @staticmethod
    def _build_key(
        *,
        project_id: int,
        task_status: TaskStatus | None,
        priority: TaskPriority | None,
        assignee_id: int | None,
        page: int,
        limit: int,
    ) -> str:
        status_value = task_status.value if task_status is not None else "all"
        priority_value = priority.value if priority is not None else "all"
        assignee_value = assignee_id if assignee_id is not None else "all"
        return (
            f"taskhub:projects:{project_id}:tasks:"
            f"status={status_value}:priority={priority_value}:"
            f"assignee={assignee_value}:page={page}:limit={limit}"
        )


redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
task_cache = TaskCache(redis_client)


async def close_cache() -> None:
    await redis_client.aclose()
