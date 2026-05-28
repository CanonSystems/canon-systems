#!/usr/bin/env python3
"""Rewrite knowledge-api Postgres rows from IMC/innermost → MJC/marrow.

Canon capture / canon ask scope canonical artifacts by X-Company-Id (→ scope_ids)
and repo_id query param (→ repo_ids). Cloning Secrets Manager alone does not
migrate existing rows — run this against the **same** database the production
knowledge-api uses.

Dependencies (same as backend/knowledge-api): sqlalchemy, psycopg[binary].

  export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
  # or set POSTGRES_* like knowledge-api and omit --database-url

  python3 scripts/migrate_knowledge_api_tenant.py
  python3 scripts/migrate_knowledge_api_tenant.py --apply

Defaults: from_company=IMC from_repo=innermost to_company=MJC to_repo=marrow
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any


def _build_url_from_postgres_env() -> str:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "canon_systems")
    user = os.environ.get("POSTGRES_USER", "canon")
    password = os.environ.get("POSTGRES_PASSWORD", "canon")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


def _rewrite_json_list(raw: Any, replacements: dict[str, str]) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
    elif isinstance(raw, list):
        data = raw
    else:
        return None
    if not isinstance(data, list):
        return None
    return [replacements.get(str(x), str(x)) for x in data]


def _as_str_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str):
        try:
            return [str(x) for x in json.loads(raw)]
        except json.JSONDecodeError:
            return []
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", "").strip(), help="SQLAlchemy URL (postgresql+psycopg://…).")
    parser.add_argument("--from-company", default="IMC")
    parser.add_argument("--from-repo", default="innermost")
    parser.add_argument("--to-company", default="MJC")
    parser.add_argument("--to-repo", default="marrow")
    parser.add_argument("--apply", action="store_true", help="Write changes (default is dry-run).")
    args = parser.parse_args()

    database_url = args.database_url.strip() or _build_url_from_postgres_env()
    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        print("error: install sqlalchemy + psycopg (e.g. pip install 'sqlalchemy>=2' 'psycopg[binary]>=3.2')", file=sys.stderr)
        return 2

    engine = create_engine(database_url, future=True, pool_pre_ping=True)
    fc, fr, tc, tr = args.from_company, args.from_repo, args.to_company, args.to_repo

    with engine.connect() as conn:
        art_rows = conn.execute(
            text(
                "SELECT id, scope_ids, repo_ids FROM artifacts "
                "WHERE scope_ids::text LIKE :fc AND repo_ids::text LIKE :fr"
            ),
            {"fc": f"%{json.dumps(fc)}%", "fr": f"%{json.dumps(fr)}%"},
        ).fetchall()

        preview: list[tuple[str, list[str], list[str], list[str], list[str]]] = []
        for row in art_rows:
            aid, sc, rp = row[0], row[1], row[2]
            old_sc_list = _as_str_list(sc)
            old_rp_list = _as_str_list(rp)
            if fc not in old_sc_list or fr not in old_rp_list:
                continue
            new_sc = _rewrite_json_list(sc, {fc: tc})
            new_rp = _rewrite_json_list(rp, {fr: tr})
            if new_sc is None or new_rp is None:
                continue
            preview.append((aid, old_sc_list, old_rp_list, new_sc, new_rp))

        run_count = conn.execute(
            text("SELECT COUNT(*) FROM runs WHERE scope_id = :fc AND repository_id = :fr"),
            {"fc": fc, "fr": fr},
        ).scalar_one()

        wi_count = conn.execute(
            text(
                "SELECT COUNT(*) FROM work_items WHERE project_scope_id = :fc AND repository_id = :fr"
            ),
            {"fc": fc, "fr": fr},
        ).scalar_one()

        print(f"artifacts to update (contain {fc!r} in scope_ids and {fr!r} in repo_ids): {len(preview)}")
        for aid, old_sc, old_rp, nsc, nrp in preview[:15]:
            print(f"  {aid}: scope {old_sc} → {nsc}; repos {old_rp} → {nrp}")
        if len(preview) > 15:
            print(f"  … {len(preview) - 15} more")
        print(f"runs to update (scope_id={fc!r}, repository_id={fr!r}): {run_count}")
        print(f"work_items to update (project_scope_id={fc!r}, repository_id={fr!r}): {wi_count}")

        if not args.apply:
            print("\nDry run only. Re-run with --apply to write changes.")
            return 0

    with engine.begin() as conn:
        for aid, _, _, nsc, nrp in preview:
            conn.execute(
                text(
                    "UPDATE artifacts SET scope_ids = CAST(:sc AS json), "
                    "repo_ids = CAST(:rp AS json) WHERE id = :id"
                ),
                {"sc": json.dumps(nsc), "rp": json.dumps(nrp), "id": aid},
            )
        conn.execute(
            text(
                "UPDATE runs SET scope_id = :tc, repository_id = :tr "
                "WHERE scope_id = :fc AND repository_id = :fr"
            ),
            {"tc": tc, "tr": tr, "fc": fc, "fr": fr},
        )
        conn.execute(
            text(
                "UPDATE work_items SET project_scope_id = :tc, repository_id = :tr "
                "WHERE project_scope_id = :fc AND repository_id = :fr"
            ),
            {"tc": tc, "tr": tr, "fc": fc, "fr": fr},
        )

    print("Applied updates and committed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
