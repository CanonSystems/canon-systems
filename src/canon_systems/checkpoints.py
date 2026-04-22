"""Per-phase checkpoint artifact validation (Wave 2 E2-T5)."""
from __future__ import annotations
import json
from pathlib import Path

REQUIRED_PHASES: tuple[str, ...] = (
    "scoper",
    "cursor-pilot",
    "implementer",
    "qa-gate",
    "release-orchestrator",
)


def _collect_checkpoint_errors(*, root: Path, handoff_id: str, task_id: str) -> list[str]:
    base = root / ".cursor" / "handoffs" / handoff_id / task_id / "checkpoints"
    errors: list[str] = []
    for phase in REQUIRED_PHASES:
        path = base / f"{phase}.json"
        if not path.exists():
            errors.append(f"missing checkpoint artifact: {path}")
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append(f"invalid JSON in checkpoint artifact: {path}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"checkpoint payload must be JSON object: {path}")
            continue
        sv = payload.get("schema_version")
        if sv != "1":
            errors.append(f"checkpoint schema_version mismatch (got {sv!r}, expected '1'): {path}")
        ph = payload.get("phase")
        if ph != phase:
            errors.append(f"checkpoint phase mismatch (got {ph!r}, expected {phase!r}): {path}")
        tid = payload.get("task_id")
        if tid != task_id:
            errors.append(f"checkpoint task_id mismatch (got {tid!r}, expected {task_id!r}): {path}")
        hid = payload.get("handoff_id")
        if hid != handoff_id:
            errors.append(f"checkpoint handoff_id mismatch (got {hid!r}, expected {handoff_id!r}): {path}")
        stv = payload.get("state_version")
        if not isinstance(stv, int) or isinstance(stv, bool) or stv < 1:
            errors.append(f"checkpoint state_version invalid (got {stv!r}, expected int >= 1): {path}")
    return errors
