"""Add refresh token hash to users.

Revision ID: 20260731_0002
Revises: 20260730_0001
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260731_0002"
down_revision: str | None = "20260730_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "refresh_token_hash")
