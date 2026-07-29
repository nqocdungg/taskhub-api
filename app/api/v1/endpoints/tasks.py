from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_task_service
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.task import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])

TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, service: TaskServiceDep) -> TaskResponse:
    return service.create(payload)


@router.get("", response_model=list[TaskResponse])
def list_tasks(service: TaskServiceDep) -> list[TaskResponse]:
    return service.list()


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, service: TaskServiceDep) -> TaskResponse:
    return service.get(task_id)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int, payload: TaskUpdate, service: TaskServiceDep
) -> TaskResponse:
    return service.update(task_id, payload)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, service: TaskServiceDep) -> None:
    service.delete(task_id)
