"""Add Jira/canon task linkage columns to runs."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260414_0005"
down_revision = "20260411_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("jira_issue_key", sa.String(length=64), nullable=True))
    op.add_column("runs", sa.Column("canon_task_id", sa.String(length=128), nullable=True))
    op.add_column("runs", sa.Column("task_title", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "task_title")
    op.drop_column("runs", "canon_task_id")
    op.drop_column("runs", "jira_issue_key")
