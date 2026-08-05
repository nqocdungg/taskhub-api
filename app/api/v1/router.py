from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    comments,
    labels,
    projects,
    tasks,
    users,
    workspaces,
)
from app.api.v1.responses import ERROR_RESPONSES

api_router = APIRouter(responses=ERROR_RESPONSES)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(workspaces.router)
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
api_router.include_router(labels.router)
api_router.include_router(comments.router)
