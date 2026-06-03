#!/usr/bin/env python3
"""Import docs/EDWARD-TASK-LIST.md items into canon task ledgers (FMO / Edward).

Run from go.showtrail.website (or any FMO repo) with canon-systems on PYTHONPATH:

  cd /path/to/go.showtrail.website
  PYTHONPATH=/path/to/canon-systems/src \\
    CANON_ACTOR_ID=usr_romiwalker \\
    CANON_ACTOR_DISPLAY_NAME=Romi \\
    python3 /path/to/canon-systems/scripts/import_fmo_edward_tasks.py

Idempotent: skips task_ref values already present in the target ledger(s).
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Allow running without pip install when PYTHONPATH points at src/
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from canon_systems import tasks as core  # noqa: E402
from canon_systems.tasks_cli import (  # noqa: E402
    _append_event,
    _company_ledger_path,
    _emit_canonical_event,
    _new_event_id,
    _now_iso,
    _read_ledger,
    _repo_ledger_path,
)

COMPANY_ID = "FMO"
AUTHOR_ID = os.environ.get("CANON_ACTOR_ID", "usr_romiwalker").strip() or "usr_romiwalker"
AUTHOR_DISPLAY = os.environ.get("CANON_ACTOR_DISPLAY_NAME", "Romi").strip() or "Romi"
ASSIGNEE = os.environ.get("CANON_EDWARD_ACTOR_ID", "usr_new.moon3461").strip() or "usr_new.moon3461"

LOCALWORK = Path(os.environ.get("CANON_LOCALWORK_ROOT", Path.home() / "localwork"))

REPO_SHOWTRAIL = "github.com/familyoneInc/go.showtrail.website"
REPO_BACKEND = "github.com/familyoneInc/familyonebackend"
REPO_ADMIN = "github.com/familyoneInc/familyone-admin-backend"

ScopeKind = Literal["repo", "multi_repo", "company"]


@dataclass(frozen=True)
class TaskSpec:
    task_ref: str
    title: str
    body: str
    scope: ScopeKind
    priority: str
    labels: tuple[str, ...]
    repo_root_name: str  # directory under localwork for repo-scoped ledger
    repository_id: str = ""
    repositories: tuple[str, ...] = ()
    source_doc: str = "docs/EDWARD-TASK-LIST.md"


def _repo_root(name: str) -> Path:
    return (LOCALWORK / name).resolve()


def _existing_refs(*ledger_paths: Path) -> set[str]:
    refs: set[str] = set()
    for path in ledger_paths:
        for ev in _read_ledger(path):
            ref = str(ev.get("task_ref", "")).strip()
            if ref:
                refs.add(ref)
    return refs


def _create_task(
    spec: TaskSpec,
    *,
    ledger_path: Path,
    repo_root: Path,
    skip_refs: set[str],
) -> str:
    if spec.task_ref in skip_refs:
        return "skip"
    event = core.make_event(
        event_type=core.EVENT_CREATED,
        event_id=_new_event_id(),
        task_ref=spec.task_ref,
        timestamp=_now_iso(),
        actor_id=AUTHOR_ID,
        actor_display=AUTHOR_DISPLAY,
        company_id=COMPANY_ID,
        scope=spec.scope,
        repository_id=spec.repository_id,
        repositories=spec.repositories,
        fields={
            "title": spec.title,
            "body": spec.body,
            "status": "open",
            "priority": spec.priority,
            "assignees": [ASSIGNEE],
            "labels": list(spec.labels),
        },
    )
    _append_event(ledger_path, event)

    class _Ctx:
        company_id = COMPANY_ID
        repository_id = spec.repository_id or REPO_SHOWTRAIL

    _emit_canonical_event(repo_root, event, _Ctx())
    return "created"


# Edward-owned items from EDWARD-TASK-LIST.md (2026-06-01). WS11/WS12 / CMS / defer omitted.
TASKS: tuple[TaskSpec, ...] = (
    TaskSpec(
        "tsk_fmo_edward_index",
        "[FMO] Edward ShowTrail task list (canonical doc)",
        "Track all handoffs in docs/EDWARD-TASK-LIST.md. Pilot show bc2a58dc-e740-4217-b2c0-f06eb3c508fe.",
        "company",
        "normal",
        ("edward-task-list", "showtrail", "index"),
        "",
        repositories=(REPO_SHOWTRAIL, REPO_BACKEND, REPO_ADMIN),
    ),
    # P0 — backend (familyonebackend)
    TaskSpec(
        "tsk_fmo_edward_p0_01",
        "[P0-1] POST /ShowTrailSync/sync-data",
        "Persist userInfo per show_id including meta_data.my_day, like_item, qr_code, seminars. "
        "Acceptance: signed-in user adds plan item → refresh → still on /plan-visit.",
        "repo",
        "urgent",
        ("p0", "auth", "sync", "edward-task-list"),
        "familyonebackend",
        repository_id=REPO_BACKEND,
    ),
    TaskSpec(
        "tsk_fmo_edward_p0_02",
        "[P0-2] POST /getUserByIdShowtrail",
        "Return full profile + meta_data on login/refresh.",
        "repo",
        "urgent",
        ("p0", "auth", "edward-task-list"),
        "familyonebackend",
        repository_id=REPO_BACKEND,
    ),
    TaskSpec(
        "tsk_fmo_edward_p0_03",
        "[P0-3] Magic link — userCreateShowtrail + checkUserShowTrail",
        "Email login stable on devgo.",
        "repo",
        "urgent",
        ("p0", "auth", "magic-link", "edward-task-list"),
        "familyonebackend",
        repository_id=REPO_BACKEND,
    ),
    TaskSpec(
        "tsk_fmo_edward_p0_03a",
        "[P0-3a] Magic link email — URL target (Cognito/SES)",
        "Link opens current PWA on devgo.showtrail.app or go.showtrail.app loading route; not legacy /Home/....",
        "multi_repo",
        "urgent",
        ("p0", "auth", "magic-link", "edward-task-list"),
        "familyonebackend",
        repositories=(REPO_BACKEND, REPO_SHOWTRAIL),
    ),
    TaskSpec(
        "tsk_fmo_edward_p0_03b",
        "[P0-3b] Magic link email — redesign + wire template",
        "Approved HTML: docs/email-templates/showtrail-magic-link-email.html. "
        "See docs/EDWARD-MAGIC-LINK-EMAIL-HANDOFF.md.",
        "multi_repo",
        "urgent",
        ("p0", "auth", "magic-link", "edward-task-list"),
        "familyonebackend",
        repositories=(REPO_BACKEND, REPO_SHOWTRAIL),
    ),
    TaskSpec(
        "tsk_fmo_edward_p0_03c",
        "[P0-3c] Magic link payload in link",
        "Encoded query: user_id, userType=first_time|second_time, code=<token> per SignIn.jsx.",
        "repo",
        "urgent",
        ("p0", "auth", "magic-link", "edward-task-list"),
        "familyonebackend",
        repository_id=REPO_BACKEND,
    ),
    TaskSpec(
        "tsk_fmo_edward_p0_04",
        "[P0-4] Profile gate — meta_data.finalData",
        "After signup review; round-trips via sync. Unblocks plan/saved/add-to-day.",
        "repo",
        "urgent",
        ("p0", "auth", "edward-task-list"),
        "familyonebackend",
        repository_id=REPO_BACKEND,
    ),
    TaskSpec(
        "tsk_fmo_edward_p0_04a",
        "[P0-4a] Deploy env — VITE_API_URL for consumer builds",
        "PWA must call https://h6wdfhaz34.execute-api.us-east-1.amazonaws.com/dev for auth/sync. "
        "Document CI / .env.production.",
        "repo",
        "urgent",
        ("p0", "deploy", "edward-task-list"),
        "go.showtrail.website",
        repository_id=REPO_SHOWTRAIL,
    ),
    TaskSpec(
        "tsk_fmo_edward_p0_05",
        "[P0-5] PH-T1 — event start_date/end_date from show_date",
        "PartnerHub publish JSON fidelity. See docs/PARTNERHUB-HANDOFF-JSON-FIDELITY.md.",
        "repo",
        "urgent",
        ("p0", "publish", "edward-task-list"),
        "familyone-admin-backend",
        repository_id=REPO_ADMIN,
    ),
    TaskSpec(
        "tsk_fmo_edward_p0_06",
        "[P0-6] PH-T3 — pre-publish validation",
        "QA titles, speaker UUIDs, dates before publish.",
        "repo",
        "urgent",
        ("p0", "publish", "edward-task-list"),
        "familyone-admin-backend",
        repository_id=REPO_ADMIN,
    ),
    # P1 Plan
    TaskSpec(
        "tsk_fmo_edward_p1_07",
        "[P1-7] Two-store API — user_saves vs my_day_items",
        "Not one blob. SHOWTRAIL-JSON-CONTRACT.md §3.5.",
        "repo",
        "high",
        ("p1", "plan", "edward-task-list"),
        "familyonebackend",
        repository_id=REPO_BACKEND,
    ),
    TaskSpec(
        "tsk_fmo_edward_p1_08",
        "[P1-8] sort_index on plan items in sync response",
        "Consumer already reads sort_index.",
        "repo",
        "high",
        ("p1", "plan", "edward-task-list"),
        "familyonebackend",
        repository_id=REPO_BACKEND,
    ),
    TaskSpec(
        "tsk_fmo_edward_p1_09",
        "[P1-9] PH-T6 — normalize seminars[*].seminar_date",
        "Session array for plan times + add saved talks.",
        "repo",
        "high",
        ("p1", "publish", "plan", "edward-task-list"),
        "familyone-admin-backend",
        repository_id=REPO_ADMIN,
    ),
    TaskSpec(
        "tsk_fmo_edward_p1_10",
        "[P1-10] Stable IDs in publish JSON",
        "seminar_id, exhibitor/booth ids match client my_day rows.",
        "repo",
        "high",
        ("p1", "publish", "plan", "edward-task-list"),
        "familyone-admin-backend",
        repository_id=REPO_ADMIN,
    ),
    # P1 Auth
    TaskSpec(
        "tsk_fmo_edward_p1_11",
        "[P1-11] Phone OTP — sendPhoneOtp / verifyPhoneOtp",
        "visitor_id + bearer for signup + onboarding.",
        "repo",
        "high",
        ("p1", "auth", "edward-task-list"),
        "familyonebackend",
        repository_id=REPO_BACKEND,
    ),
    TaskSpec(
        "tsk_fmo_edward_p1_12",
        "[P1-12] OAuth — Apple / Google / Facebook",
        "Cognito IdPs + Hosted UI callbacks for devgo + prod.",
        "repo",
        "high",
        ("p1", "auth", "oauth", "edward-task-list"),
        "familyonebackend",
        repository_id=REPO_BACKEND,
    ),
    TaskSpec(
        "tsk_fmo_edward_p1_13",
        "[P1-13] Publish show.lifecycle, opens_at, short_name, brand_mark",
        "Home + show picker (PH-T1 related).",
        "repo",
        "high",
        ("p1", "publish", "edward-task-list"),
        "familyone-admin-backend",
        repository_id=REPO_ADMIN,
    ),
    TaskSpec(
        "tsk_fmo_edward_p1_16",
        "[P1-16] Recognised family.one identity on ShowTrail signup",
        "Extend checkUserShowTrail (preferred) with has_familyone_profile + import snapshot on first_time. "
        "Consumer blocked until response stable on dev.",
        "multi_repo",
        "high",
        ("p1", "auth", "familyone", "edward-task-list"),
        "familyonebackend",
        repositories=(REPO_BACKEND, REPO_SHOWTRAIL),
    ),
    # P1 Onboarding
    TaskSpec(
        "tsk_fmo_edward_p1_14",
        "[P1-14] Persist onboarding via sync-data",
        "Interests, family stage, phone verified — not only IndexedDB.",
        "repo",
        "high",
        ("p1", "onboarding", "edward-task-list"),
        "familyonebackend",
        repository_id=REPO_BACKEND,
    ),
    TaskSpec(
        "tsk_fmo_edward_p1_15",
        "[P1-15] Document meta_data.onboarding_profile",
        "Web + native alignment for onboarding fields.",
        "repo",
        "normal",
        ("p1", "onboarding", "edward-task-list"),
        "familyonebackend",
        repository_id=REPO_BACKEND,
    ),
    # P1 Map & Discover handoffs
    TaskSpec(
        "tsk_fmo_edward_p1_map",
        "[P1] Map floor plan + booth coordinates (handoff)",
        "Complete checklist in docs/EDWARD-MAP-FLOORPLAN-HANDOFF.md. Republish pilot JSON after geometry fixes.",
        "repo",
        "high",
        ("p1", "map", "edward-task-list"),
        "familyone-admin-backend",
        repository_id=REPO_ADMIN,
    ),
    TaskSpec(
        "tsk_fmo_edward_p1_discover",
        "[P1] PH-T5 Discover — category catalog + categories[]",
        "docs/EDWARD-DISCOVER-CATEGORIES-HANDOFF.md. Pilot bc2a58dc.",
        "repo",
        "high",
        ("p1", "discover", "publish", "edward-task-list"),
        "familyone-admin-backend",
        repository_id=REPO_ADMIN,
    ),
)


def main() -> int:
    company_ledger = _company_ledger_path(COMPANY_ID)
    all_ledgers: list[Path] = [company_ledger]
    for name in ("go.showtrail.website", "familyonebackend", "familyone-admin-backend"):
        root = _repo_root(name)
        if root.exists():
            all_ledgers.append(_repo_ledger_path(root))

    skip = _existing_refs(*all_ledgers)
    created = 0
    skipped = 0

    for spec in TASKS:
        if spec.scope == "company":
            ledger = company_ledger
            root = _repo_root("go.showtrail.website")
        elif spec.scope == "multi_repo":
            ledger = company_ledger
            root = _repo_root(spec.repo_root_name or "familyonebackend")
        else:
            root = _repo_root(spec.repo_root_name)
            ledger = _repo_ledger_path(root)

        if not root.exists() and spec.scope == "repo":
            print(f"warn: missing repo root {root} for {spec.task_ref}", file=sys.stderr)
            continue

        result = _create_task(spec, ledger_path=ledger, repo_root=root, skip_refs=skip)
        if result == "created":
            created += 1
            skip.add(spec.task_ref)
            print(f"created {spec.task_ref} -> {ledger}")
        else:
            skipped += 1
            print(f"skip   {spec.task_ref}")

    print(f"\nDone: created={created} skipped={skipped} assignee={ASSIGNEE} author={AUTHOR_ID}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
