import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.cache import close_cache
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, register_request_logging
from app.db.session import dispose_engine

API_V1_PREFIX = "/api/v1"
configure_logging()
logger = logging.getLogger(__name__)

OPENAPI_TAGS = [
    {"name": "Authentication", "description": "Đăng ký, đăng nhập và quản lý token."},
    {"name": "Users", "description": "Quản lý thông tin người dùng hiện tại."},
    {"name": "Workspaces", "description": "Quản lý workspace và thành viên."},
    {"name": "Projects", "description": "Quản lý project trong workspace."},
    {"name": "Tasks", "description": "Quản lý, lọc và phân trang task."},
    {"name": "Labels", "description": "Quản lý label và gắn label cho task."},
    {"name": "Comments", "description": "Thêm và xóa comment trên task."},
]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown event của ứng dụng."""
    logger.info("TaskHub API started")
    try:
        yield
    finally:
        await close_cache()
        await dispose_engine()
        logger.info("TaskHub API stopped")


app = FastAPI(
    title="TaskHub API",
    description="TaskHub - Hệ thống quản lý công việc (Task Management API)",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
)
register_exception_handlers(app)
register_request_logging(app)
app.include_router(api_router, prefix=API_V1_PREFIX)
