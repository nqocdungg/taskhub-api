import pytest
from sqlalchemy import text

from app.db.session import async_session_factory

pytestmark = pytest.mark.asyncio(loop_scope="session")

EXPECTED_INDEXES = {
    "ix_workspace_members_user_id",
    "ix_projects_workspace_id_id",
    "ix_tasks_project_id_id",
    "ix_tasks_project_status_id",
    "ix_tasks_project_priority_id",
    "ix_tasks_project_assignee_id",
    "ix_labels_project_id_id",
}


async def test_query_indexes_exist_in_postgresql() -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE schemaname = 'public'"
            )
        )
    actual_indexes = set(result.scalars())

    assert EXPECTED_INDEXES <= actual_indexes
