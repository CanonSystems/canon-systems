"""SQLAlchemy models for orchestration runs."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RunORM(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    stage: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(64))
    dispatch_status: Mapped[str] = mapped_column(String(64), default="pending")
    launch_mode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    initiated_by: Mapped[str] = mapped_column(String(64))
    orchestration_runtime: Mapped[str | None] = mapped_column(String(64), nullable=True)
    workflow_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    task_queue: Mapped[str | None] = mapped_column(String(128), nullable=True)
    capability_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_lane: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fallback_lane: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parent_run_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("runs.id"), nullable=True
    )
    dispatch_payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    claimed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scope_artifact_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("artifacts.id"), nullable=True
    )
    plan_packet_artifact_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("artifacts.id"), nullable=True
    )
    scaffold_blueprint_artifact_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("artifacts.id"), nullable=True
    )
    execution_packet_artifact_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("artifacts.id"), nullable=True
    )
    work_item_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("work_items.id"), nullable=True
    )
    jira_issue_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    canon_task_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    task_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    repository_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scope_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RunEventORM(Base):
    __tablename__ = "run_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("runs.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(128))
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
