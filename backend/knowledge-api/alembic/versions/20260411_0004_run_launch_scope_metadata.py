"""Add launch mode and source artifact metadata to runs."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260411_0004"
down_revision = "20260411_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("launch_mode", sa.String(length=64), nullable=True))
    op.add_column("runs", sa.Column("source_conversation_id", sa.String(length=64), nullable=True))
    op.add_column("runs", sa.Column("scope_artifact_id", sa.String(length=64), nullable=True))
    op.add_column("runs", sa.Column("plan_packet_artifact_id", sa.String(length=64), nullable=True))
    op.add_column("runs", sa.Column("scaffold_blueprint_artifact_id", sa.String(length=64), nullable=True))
    op.add_column("runs", sa.Column("execution_packet_artifact_id", sa.String(length=64), nullable=True))

    op.create_foreign_key(
        "fk_runs_scope_artifact_id",
        "runs",
        "artifacts",
        ["scope_artifact_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_runs_plan_packet_artifact_id",
        "runs",
        "artifacts",
        ["plan_packet_artifact_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_runs_scaffold_blueprint_artifact_id",
        "runs",
        "artifacts",
        ["scaffold_blueprint_artifact_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_runs_execution_packet_artifact_id",
        "runs",
        "artifacts",
        ["execution_packet_artifact_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_runs_execution_packet_artifact_id", "runs", type_="foreignkey")
    op.drop_constraint("fk_runs_scaffold_blueprint_artifact_id", "runs", type_="foreignkey")
    op.drop_constraint("fk_runs_plan_packet_artifact_id", "runs", type_="foreignkey")
    op.drop_constraint("fk_runs_scope_artifact_id", "runs", type_="foreignkey")

    op.drop_column("runs", "execution_packet_artifact_id")
    op.drop_column("runs", "scaffold_blueprint_artifact_id")
    op.drop_column("runs", "plan_packet_artifact_id")
    op.drop_column("runs", "scope_artifact_id")
    op.drop_column("runs", "source_conversation_id")
    op.drop_column("runs", "launch_mode")
