"""Add indexes for current resource queries.

Revision ID: 20260806_0003
Revises: 20260731_0002
Create Date: 2026-08-06
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260806_0003"
down_revision: str | None = "20260731_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_workspace_members_user_id",
        "workspace_members",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_projects_workspace_id_id",
        "projects",
        ["workspace_id", "id"],
        unique=False,
    )
    op.create_index(
        "ix_tasks_project_id_id",
        "tasks",
        ["project_id", "id"],
        unique=False,
    )
    op.create_index(
        "ix_tasks_project_status_id",
        "tasks",
        ["project_id", "status", "id"],
        unique=False,
    )
    op.create_index(
        "ix_tasks_project_priority_id",
        "tasks",
        ["project_id", "priority", "id"],
        unique=False,
    )
    op.create_index(
        "ix_tasks_project_assignee_id",
        "tasks",
        ["project_id", "assignee_id", "id"],
        unique=False,
    )
    op.create_index(
        "ix_labels_project_id_id",
        "labels",
        ["project_id", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_labels_project_id_id", table_name="labels")
    op.drop_index("ix_tasks_project_assignee_id", table_name="tasks")
    op.drop_index("ix_tasks_project_priority_id", table_name="tasks")
    op.drop_index("ix_tasks_project_status_id", table_name="tasks")
    op.drop_index("ix_tasks_project_id_id", table_name="tasks")
    op.drop_index("ix_projects_workspace_id_id", table_name="projects")
    op.drop_index(
        "ix_workspace_members_user_id",
        table_name="workspace_members",
    )
