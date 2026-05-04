"""Shared DoR (Definition of Ready) rejection telemetry validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class DorTelemetryLabels:
    """Error message phrasing for a CLI surface (qa-validate vs flow-audit)."""

    missing_json: str
    missing_status: str
    invalid_json: str
    payload_not_object: str
    handoff_mismatch: str
    stage_missing: str
    task_mismatch: str
    status_exit_marker: str
    bulk_handoffs_without_json: str

    @classmethod
    def qa_validate(cls) -> DorTelemetryLabels:
        return cls(
            missing_json="missing DoR telemetry JSON for rejection packet",
            missing_status="missing DoR telemetry status file for rejection packet",
            invalid_json="invalid JSON in DoR telemetry file",
            payload_not_object="DoR telemetry payload must be object",
            handoff_mismatch="DoR telemetry handoff_id mismatch in",
            stage_missing="DoR telemetry stage missing in",
            task_mismatch="DoR telemetry task_id mismatch in",
            status_exit_marker="DoR telemetry status missing exit_code marker",
            bulk_handoffs_without_json=(
                "HANDOFF_NOT_READY packets exist but no DoR telemetry JSON files found under"
            ),
        )

    @classmethod
    def flow_audit(cls) -> DorTelemetryLabels:
        return cls(
            missing_json="missing DoR telemetry JSON for rejection packet",
            missing_status="missing DoR telemetry status file for rejection packet",
            invalid_json="invalid JSON in telemetry file",
            payload_not_object="telemetry payload must be object",
            handoff_mismatch="telemetry handoff_id mismatch in",
            stage_missing="telemetry stage missing in",
            task_mismatch="telemetry task_id mismatch in",
            status_exit_marker="telemetry status missing exit_code marker",
            bulk_handoffs_without_json=(
                "HANDOFF_NOT_READY packets exist but no DoR telemetry JSON files found under"
            ),
        )


def collect_dor_telemetry_errors(
    *,
    rejection_packets: Sequence[Path],
    telemetry_dir: Path,
    handoff_id: str,
    task_id: str,
    labels: DorTelemetryLabels,
    require_task_identity: bool = False,
    bulk_error_if_no_json: bool = False,
) -> list[str]:
    """
    Validate DoR telemetry artifacts for persisted HANDOFF_NOT_READY packets.

    For each ``handoff-not-ready/<stem>.md``, requires ``dor-failure/<stem>.json``
    and ``dor-failure/<stem>.status``.

    Identity rules (AC3):

    - ``handoff_id`` in the JSON payload must match ``handoff_id``.
    - ``stage`` must be non-empty.
    - If ``task_id`` is present in the payload, it must match ``task_id``.
      When ``require_task_identity`` is True, the payload must carry a
      ``task_id`` equal to ``task_id`` (CLI-scoped tasks).

    Status files must contain the substring ``exit_code:`` (AC4).
    """
    errors: list[str] = []
    hi = handoff_id.strip()
    ti = task_id.strip()

    sorted_packets = sorted(rejection_packets)
    telemetry_json = sorted(telemetry_dir.glob("*.json")) if telemetry_dir.exists() else []

    if bulk_error_if_no_json and sorted_packets and not telemetry_json:
        errors.append(f"{labels.bulk_handoffs_without_json} {telemetry_dir}")

    for packet in sorted_packets:
        stem = packet.stem
        json_path = telemetry_dir / f"{stem}.json"
        status_path = telemetry_dir / f"{stem}.status"
        if not json_path.exists():
            errors.append(f"{labels.missing_json}: {packet}")
            continue
        if not status_path.exists():
            errors.append(f"{labels.missing_status}: {packet}")
            continue
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append(f"{labels.invalid_json}: {json_path}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"{labels.payload_not_object}: {json_path}")
            continue
        if str(payload.get("handoff_id", "")).strip() != hi:
            errors.append(f"{labels.handoff_mismatch}: {json_path}")
        if not str(payload.get("stage", "")).strip():
            errors.append(f"{labels.stage_missing}: {json_path}")

        payload_tid = str(payload.get("task_id", "")).strip()
        if require_task_identity:
            if payload_tid != ti:
                errors.append(f"{labels.task_mismatch}: {json_path}")
        elif "task_id" in payload and payload_tid != ti:
            errors.append(f"{labels.task_mismatch}: {json_path}")

        status_text = status_path.read_text(encoding="utf-8")
        if "exit_code:" not in status_text:
            errors.append(f"{labels.status_exit_marker}: {status_path}")

    return errors


def collect_dor_telemetry_errors_for_task(
    *,
    root: Path,
    handoff_id: str,
    task_id: str,
    labels: DorTelemetryLabels,
    require_task_identity: bool = False,
    bulk_error_if_no_json: bool = False,
) -> list[str]:
    """Discover rejection packets under the standard handoffs layout and validate telemetry."""
    base = root / ".cursor" / "handoffs" / handoff_id.strip() / task_id.strip()
    rejection_dir = base / "handoff-not-ready"
    telemetry_dir = base / "dor-failure"
    rejection_packets: Iterable[Path] = (
        sorted(rejection_dir.glob("*.md")) if rejection_dir.exists() else []
    )
    return collect_dor_telemetry_errors(
        rejection_packets=list(rejection_packets),
        telemetry_dir=telemetry_dir,
        handoff_id=handoff_id,
        task_id=task_id,
        labels=labels,
        require_task_identity=require_task_identity,
        bulk_error_if_no_json=bulk_error_if_no_json,
    )
