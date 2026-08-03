from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import CurrentUserDep, get_comment_service
from app.schemas.comment import CommentCreate, CommentResponse
from app.services.comment import CommentService

router = APIRouter(tags=["Comments"])

CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    task_id: int,
    payload: CommentCreate,
    current_user: CurrentUserDep,
    service: CommentServiceDep,
) -> CommentResponse:
    return await service.create(task_id, payload, current_user)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment(
    comment_id: int,
    current_user: CurrentUserDep,
    service: CommentServiceDep,
) -> None:
    await service.delete(comment_id, current_user)
