"""Add dispatch metadata to orchestration runs."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260411_0002"
down_revision = "20260410_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column("dispatch_status", sa.String(length=64), nullable=False, server_default="pending"),
    )
    op.add_column("runs", sa.Column("orchestration_runtime", sa.String(length=64), nullable=True))
    op.add_column("runs", sa.Column("workflow_type", sa.String(length=128), nullable=True))
    op.add_column("runs", sa.Column("task_queue", sa.String(length=128), nullable=True))
    op.add_column("runs", sa.Column("capability_class", sa.String(length=64), nullable=True))
    op.add_column("runs", sa.Column("provider_lane", sa.String(length=64), nullable=True))
    op.add_column("runs", sa.Column("fallback_lane", sa.String(length=64), nullable=True))
    op.add_column("runs", sa.Column("parent_run_id", sa.String(length=64), nullable=True))
    op.add_column("runs", sa.Column("dispatch_payload_json", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_runs_parent_run_id",
        "runs",
        "runs",
        ["parent_run_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_runs_parent_run_id", "runs", type_="foreignkey")
    op.drop_column("runs", "dispatch_payload_json")
    op.drop_column("runs", "parent_run_id")
    op.drop_column("runs", "fallback_lane")
    op.drop_column("runs", "provider_lane")
    op.drop_column("runs", "capability_class")
    op.drop_column("runs", "task_queue")
    op.drop_column("runs", "workflow_type")
    op.drop_column("runs", "orchestration_runtime")
    op.drop_column("runs", "dispatch_status")
