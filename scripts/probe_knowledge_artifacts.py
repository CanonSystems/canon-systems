#!/usr/bin/env python3
"""One-shot DB probe — print artifact counts (run inside VPC)."""
from __future__ import annotations

import os

from sqlalchemy import create_engine, text


def main() -> None:
    url = os.environ["DATABASE_URL"]
    e = create_engine(url, future=True)
    with e.connect() as c:
        t = c.execute(text("SELECT count(*) FROM artifacts WHERE artifact_type = 'memory_capture'")).scalar()
        im = c.execute(
            text(
                "SELECT count(*) FROM artifacts WHERE scope_ids::text LIKE :p AND repo_ids::text LIKE :q"
            ),
            {"p": "%IMC%", "q": "%innermost%"},
        ).scalar()
        mj = c.execute(
            text(
                "SELECT count(*) FROM artifacts WHERE scope_ids::text LIKE :p AND repo_ids::text LIKE :q"
            ),
            {"p": "%MJC%", "q": "%marrow%"},
        ).scalar()
        samples = c.execute(
            text(
                "SELECT id, scope_ids, repo_ids FROM artifacts WHERE artifact_type = 'memory_capture' LIMIT 8"
            )
        ).fetchall()
    print("memory_capture_total", t)
    print("imc_innermost_match", im)
    print("mjc_marrow_match", mj)
    for row in samples:
        print("sample", row[0], row[1], row[2])


if __name__ == "__main__":
    main()
