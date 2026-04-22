"""Add claim metadata to orchestration runs."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260411_0003"
down_revision = "20260411_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("claimed_by", sa.String(length=64), nullable=True))
    op.add_column("runs", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "claimed_at")
    op.drop_column("runs", "claimed_by")
