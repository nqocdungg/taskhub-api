# ruff: noqa: E402

import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ENV_FILE", ".env.test")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://taskhub:taskhub@localhost:5434/taskhub_test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/0")
os.environ.setdefault("JWT_SECRET_KEY", "automated-test-secret-key")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("SMTP_ENABLED", "false")

import pytest
import pytest_asyncio
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text, update
from sqlalchemy.engine import make_url

from alembic import command
from app.core.cache import close_cache, redis_client
from app.db.session import async_session_factory, dispose_engine
from app.main import app
from app.models.entities import User
from app.models.enums import UserRole

API_PREFIX = "/api/v1"
DATABASE_URL = os.environ["DATABASE_URL"]
database_name = make_url(DATABASE_URL).database
if database_name is None or not database_name.endswith("_test"):
    raise RuntimeError("Automated tests require a database ending in '_test'.")


def pytest_sessionstart(session: pytest.Session) -> None:
    del session
    command.upgrade(Config("alembic.ini"), "head")


@pytest_asyncio.fixture(scope="session", autouse=True, loop_scope="session")
async def application_resources() -> AsyncIterator[None]:
    yield
    await close_cache()
    await dispose_engine()


async def _clear_test_state() -> None:
    async with async_session_factory() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE comments, task_labels, labels, tasks, "
                "projects, workspace_members, workspaces, users "
                "RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()
    await redis_client.flushdb()


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def clean_test_state() -> AsyncIterator[None]:
    await _clear_test_state()
    yield
    await _clear_test_state()


@pytest_asyncio.fixture(loop_scope="session")
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client


@dataclass(slots=True)
class ApiUser:
    id: int
    email: str
    password: str
    access_token: str
    refresh_token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}


class ApiFactory:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        self._sequence = 0

    async def create_user(
        self,
        *,
        email: str | None = None,
        password: str = "Password123!",
        full_name: str = "Test User",
    ) -> ApiUser:
        self._sequence += 1
        resolved_email = email or f"user{self._sequence}@example.com"
        register_response = await self.client.post(
            f"{API_PREFIX}/auth/register",
            json={
                "email": resolved_email,
                "full_name": full_name,
                "password": password,
            },
        )
        assert register_response.status_code == 201, register_response.text
        user_data = register_response.json()

        login_response = await self.client.post(
            f"{API_PREFIX}/auth/login",
            json={"email": resolved_email, "password": password},
        )
        assert login_response.status_code == 200, login_response.text
        token_data = login_response.json()
        return ApiUser(
            id=user_data["id"],
            email=resolved_email,
            password=password,
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
        )

    async def promote_admin(self, user: ApiUser) -> None:
        async with async_session_factory() as session:
            await session.execute(
                update(User)
                .where(User.id == user.id)
                .values(role=UserRole.ADMIN)
            )
            await session.commit()

    async def create_workspace(
        self,
        owner: ApiUser,
        *,
        name: str = "Test Workspace",
    ) -> dict[str, Any]:
        response = await self.client.post(
            f"{API_PREFIX}/workspaces",
            headers=owner.headers,
            json={"name": name},
        )
        assert response.status_code == 201, response.text
        return response.json()

    async def invite_member(
        self,
        owner: ApiUser,
        workspace_id: int,
        member: ApiUser,
        role: str,
    ) -> dict[str, Any]:
        response = await self.client.post(
            f"{API_PREFIX}/workspaces/{workspace_id}/members",
            headers=owner.headers,
            json={"user_id": member.id, "role": role},
        )
        assert response.status_code == 201, response.text
        return response.json()

    async def create_project(
        self,
        user: ApiUser,
        workspace_id: int,
        *,
        name: str = "Test Project",
    ) -> dict[str, Any]:
        response = await self.client.post(
            f"{API_PREFIX}/workspaces/{workspace_id}/projects",
            headers=user.headers,
            json={"name": name, "description": "Integration test"},
        )
        assert response.status_code == 201, response.text
        return response.json()

    async def create_task(
        self,
        user: ApiUser,
        project_id: int,
        *,
        title: str = "Test Task",
        assignee_id: int | None = None,
        status: str = "TODO",
        priority: str = "MEDIUM",
    ) -> dict[str, Any]:
        response = await self.client.post(
            f"{API_PREFIX}/projects/{project_id}/tasks",
            headers=user.headers,
            json={
                "title": title,
                "assignee_id": assignee_id,
                "status": status,
                "priority": priority,
            },
        )
        assert response.status_code == 201, response.text
        return response.json()


@pytest.fixture
def factory(client: AsyncClient) -> ApiFactory:
    return ApiFactory(client)
