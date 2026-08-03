from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import CurrentUserDep, get_label_service
from app.schemas.label import (
    LabelCreate,
    LabelResponse,
    LabelUpdate,
    TaskLabelResponse,
)
from app.services.label import LabelService

router = APIRouter(tags=["Labels"])

LabelServiceDep = Annotated[LabelService, Depends(get_label_service)]


@router.post(
    "/projects/{project_id}/labels",
    response_model=LabelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_label(
    project_id: int,
    payload: LabelCreate,
    current_user: CurrentUserDep,
    service: LabelServiceDep,
) -> LabelResponse:
    return await service.create(project_id, payload, current_user)


@router.get(
    "/projects/{project_id}/labels",
    response_model=list[LabelResponse],
)
async def list_labels(
    project_id: int,
    current_user: CurrentUserDep,
    service: LabelServiceDep,
) -> list[LabelResponse]:
    return await service.list(project_id, current_user)


@router.get("/labels/{label_id}", response_model=LabelResponse)
async def get_label(
    label_id: int,
    current_user: CurrentUserDep,
    service: LabelServiceDep,
) -> LabelResponse:
    return await service.get(label_id, current_user)


@router.patch("/labels/{label_id}", response_model=LabelResponse)
async def update_label(
    label_id: int,
    payload: LabelUpdate,
    current_user: CurrentUserDep,
    service: LabelServiceDep,
) -> LabelResponse:
    return await service.update(label_id, payload, current_user)


@router.delete("/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_label(
    label_id: int,
    current_user: CurrentUserDep,
    service: LabelServiceDep,
) -> None:
    await service.delete(label_id, current_user)


@router.post(
    "/tasks/{task_id}/labels/{label_id}",
    response_model=TaskLabelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def attach_label_to_task(
    task_id: int,
    label_id: int,
    current_user: CurrentUserDep,
    service: LabelServiceDep,
) -> TaskLabelResponse:
    return await service.attach_to_task(task_id, label_id, current_user)


@router.delete(
    "/tasks/{task_id}/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_label_from_task(
    task_id: int,
    label_id: int,
    current_user: CurrentUserDep,
    service: LabelServiceDep,
) -> None:
    await service.remove_from_task(task_id, label_id, current_user)
