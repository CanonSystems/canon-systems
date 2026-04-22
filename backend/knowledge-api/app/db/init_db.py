"""Manual schema bootstrap for local development."""

from __future__ import annotations

from app.db.base import Base
from app.db.session import engine
from app.models import artifact_db, run_db, work_item_db  # noqa: F401


def main() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    main()
