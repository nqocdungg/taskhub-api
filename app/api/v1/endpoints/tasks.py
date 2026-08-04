from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import CurrentUserDep, get_task_service
from app.models.enums import TaskPriority, TaskStatus
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.task import TaskService

router = APIRouter(tags=["Tasks"])

TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    project_id: int,
    payload: TaskCreate,
    current_user: CurrentUserDep,
    service: TaskServiceDep,
) -> TaskResponse:
    return await service.create(project_id, payload, current_user)


@router.get(
    "/projects/{project_id}/tasks",
    response_model=list[TaskResponse],
)
async def list_tasks(
    project_id: int,
    current_user: CurrentUserDep,
    service: TaskServiceDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: TaskPriority | None = None,
    assignee_id: Annotated[int | None, Query(gt=0)] = None,
) -> list[TaskResponse]:
    return await service.list(
        project_id=project_id,
        current_user=current_user,
        page=page,
        limit=limit,
        task_status=task_status,
        priority=priority,
        assignee_id=assignee_id,
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: CurrentUserDep,
    service: TaskServiceDep,
) -> TaskResponse:
    return await service.get(task_id, current_user)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    current_user: CurrentUserDep,
    service: TaskServiceDep,
) -> TaskResponse:
    return await service.update(task_id, payload, current_user)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: CurrentUserDep,
    service: TaskServiceDep,
) -> None:
    await service.delete(task_id, current_user)
