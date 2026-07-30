from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import get_task_service
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.task import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])

TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    service: TaskServiceDep,
) -> TaskResponse:
    return await service.create(payload)


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    service: TaskServiceDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[TaskResponse]:
    return await service.list(page=page, limit=limit)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, service: TaskServiceDep) -> TaskResponse:
    return await service.get(task_id)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int, payload: TaskUpdate, service: TaskServiceDep
) -> TaskResponse:
    return await service.update(task_id, payload)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, service: TaskServiceDep) -> None:
    await service.delete(task_id)
