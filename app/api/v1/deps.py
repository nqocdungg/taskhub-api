from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.repositories.task import TaskRepository
from app.services.task import TaskService

DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_task_service(session: DbSessionDep) -> TaskService:
    return TaskService(repository=TaskRepository(session))
