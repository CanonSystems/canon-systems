"""SQLAlchemy models for canonical artifacts."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ArtifactORM(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    artifact_type: Mapped[str] = mapped_column(String(64), index=True)
    current_version_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(
            "artifact_versions.id",
            use_alter=True,
            name="fk_artifacts_current_version_id",
        ),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="draft")
    visibility: Mapped[str] = mapped_column(String(32), default="project")
    owners: Mapped[list[str]] = mapped_column(JSON, default=list)
    groups: Mapped[list[str]] = mapped_column(JSON, default=list)
    scope_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    repo_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    work_item_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    conversation_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_system: Mapped[str] = mapped_column(String(64))
    supersedes_artifact_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list["ArtifactVersionORM"]] = relationship(
        back_populates="artifact",
        foreign_keys="ArtifactVersionORM.artifact_id",
        cascade="all, delete-orphan",
    )
    current_version: Mapped["ArtifactVersionORM | None"] = relationship(
        foreign_keys=[current_version_id], post_update=True
    )


class ArtifactVersionORM(Base):
    __tablename__ = "artifact_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    artifact_id: Mapped[str] = mapped_column(String(64), ForeignKey("artifacts.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    body_storage_provider: Mapped[str] = mapped_column(String(64), default="s3")
    body_storage_bucket: Mapped[str] = mapped_column(String(255))
    body_storage_key: Mapped[str] = mapped_column(String(512))
    body_content_type: Mapped[str] = mapped_column(String(128), default="text/markdown")
    body_checksum: Mapped[str] = mapped_column(String(128))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(32), default="1")
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    artifact: Mapped[ArtifactORM] = relationship(
        back_populates="versions", foreign_keys=[artifact_id]
    )
