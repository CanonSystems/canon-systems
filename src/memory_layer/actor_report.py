"""Report recent run activity by actor identity."""

from __future__ import annotations

import argparse
import json
from typing import Any

from .shared import load_identity_context, load_repo_context, request_json


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Show recent run activity and Jira keys for an actor.")
    parser.add_argument("--actor-id", default="", help="Actor id to query.")
    parser.add_argument("--limit", type=int, default=20, help="Max records to output.")
    parser.add_argument("--json", action="store_true", dest="json_out")
    args = parser.parse_args(argv)

    identity = load_identity_context()
    repo_ctx = load_repo_context(identity)
    actor_id = args.actor_id.strip() or identity.actor_id
    status, payload = request_json(
        url=f"{repo_ctx.knowledge_api_url}/api/v1/runs/summaries",
        method="GET",
        actor_id=identity.actor_id,
        company_id=repo_ctx.company_id,
        timeout_s=25,
    )

    rows: list[dict[str, Any]] = []
    if status == 200 and isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            if str(item.get("initiated_by", "")) != actor_id:
                continue
            rows.append(
                {
                    "run_id": item.get("id"),
                    "status": item.get("status"),
                    "dispatch_status": item.get("dispatch_status"),
                    "jira_issue_key": item.get("jira_issue_key"),
                    "task_title": item.get("task_title"),
                    "started_at": item.get("started_at"),
                    "ended_at": item.get("ended_at"),
                }
            )
    rows = rows[: max(1, args.limit)]
    report = {
        "actor_id": actor_id,
        "company_id": repo_ctx.company_id,
        "repository_id": repo_ctx.repository_id,
        "result_count": len(rows),
        "runs": rows,
    }
    if args.json_out:
        print(json.dumps(report, indent=2))
        return 0

    print(f"Actor activity for {actor_id} in {repo_ctx.company_id} / {repo_ctx.repository_id}")
    if not rows:
        print("No run summaries found.")
        return 0
    for item in rows:
        print(
            "- "
            f"{item['run_id']} [{item['status']}/{item['dispatch_status']}] "
            f"jira={item['jira_issue_key'] or '-'} title={item['task_title'] or '-'}"
        )
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
