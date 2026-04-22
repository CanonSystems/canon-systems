"""Initial artifact tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260410_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_items",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("external_type", sa.String(length=64), nullable=False),
        sa.Column("external_key", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("project_scope_id", sa.String(length=64), nullable=True),
        sa.Column("repository_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_work_items_external_key", "work_items", ["external_key"], unique=True)

    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("current_version_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("visibility", sa.String(length=32), nullable=False, server_default="project"),
        sa.Column("owners", sa.JSON(), nullable=False),
        sa.Column("groups", sa.JSON(), nullable=False),
        sa.Column("scope_ids", sa.JSON(), nullable=False),
        sa.Column("repo_ids", sa.JSON(), nullable=False),
        sa.Column("work_item_ids", sa.JSON(), nullable=False),
        sa.Column("conversation_ids", sa.JSON(), nullable=False),
        sa.Column("source_system", sa.String(length=64), nullable=False),
        sa.Column("supersedes_artifact_id", sa.String(length=64), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_artifacts_artifact_type", "artifacts", ["artifact_type"])

    op.create_table(
        "artifact_versions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("artifact_id", sa.String(length=64), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("body_storage_provider", sa.String(length=64), nullable=False),
        sa.Column("body_storage_bucket", sa.String(length=255), nullable=False),
        sa.Column("body_storage_key", sa.String(length=512), nullable=False),
        sa.Column("body_content_type", sa.String(length=128), nullable=False),
        sa.Column("body_checksum", sa.String(length=128), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifacts.id"]),
    )
    op.create_index("ix_artifact_versions_artifact_id", "artifact_versions", ["artifact_id"])

    op.create_foreign_key(
        "fk_artifacts_current_version_id",
        "artifacts",
        "artifact_versions",
        ["current_version_id"],
        ["id"],
    )

    op.create_table(
        "runs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("initiated_by", sa.String(length=64), nullable=False),
        sa.Column("work_item_id", sa.String(length=64), nullable=True),
        sa.Column("repository_id", sa.String(length=64), nullable=True),
        sa.Column("scope_id", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"]),
    )

    op.create_table(
        "run_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
    )
    op.create_index("ix_run_events_run_id", "run_events", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_run_events_run_id", table_name="run_events")
    op.drop_table("run_events")
    op.drop_table("runs")
    op.drop_constraint("fk_artifacts_current_version_id", "artifacts", type_="foreignkey")
    op.drop_index("ix_artifact_versions_artifact_id", table_name="artifact_versions")
    op.drop_table("artifact_versions")
    op.drop_index("ix_artifacts_artifact_type", table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_index("ix_work_items_external_key", table_name="work_items")
    op.drop_table("work_items")
