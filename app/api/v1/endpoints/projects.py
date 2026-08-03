from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import CurrentUserDep, get_project_service
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project import ProjectService

router = APIRouter(tags=["Projects"])

ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]


@router.post(
    "/workspaces/{workspace_id}/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    workspace_id: int,
    payload: ProjectCreate,
    current_user: CurrentUserDep,
    service: ProjectServiceDep,
) -> ProjectResponse:
    return await service.create(workspace_id, payload, current_user)


@router.get(
    "/workspaces/{workspace_id}/projects",
    response_model=list[ProjectResponse],
)
async def list_projects(
    workspace_id: int,
    current_user: CurrentUserDep,
    service: ProjectServiceDep,
) -> list[ProjectResponse]:
    return await service.list(workspace_id, current_user)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: CurrentUserDep,
    service: ProjectServiceDep,
) -> ProjectResponse:
    return await service.get(project_id, current_user)


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    current_user: CurrentUserDep,
    service: ProjectServiceDep,
) -> ProjectResponse:
    return await service.update(project_id, payload, current_user)


@router.patch(
    "/projects/{project_id}/archive",
    response_model=ProjectResponse,
)
async def archive_project(
    project_id: int,
    current_user: CurrentUserDep,
    service: ProjectServiceDep,
) -> ProjectResponse:
    return await service.archive(project_id, current_user)


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
    project_id: int,
    current_user: CurrentUserDep,
    service: ProjectServiceDep,
) -> None:
    await service.delete(project_id, current_user)
