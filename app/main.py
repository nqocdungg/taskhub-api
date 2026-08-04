from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.exceptions import register_exception_handlers
from app.db.session import dispose_engine

API_V1_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown event của ứng dụng."""
    print("TaskHub API đang khởi động...")
    try:
        yield
    finally:
        await dispose_engine()
        print("TaskHub API đã dừng.")


app = FastAPI(
    title="TaskHub API",
    description="TaskHub - Hệ thống quản lý công việc (Task Management API)",
    version="1.0.0",
    lifespan=lifespan,
)
register_exception_handlers(app)
app.include_router(api_router, prefix=API_V1_PREFIX)
