from __future__ import annotations

import pytest
from moto import mock_aws
import boto3

pytest.importorskip("moto")

from canon_backend_shared.events import CanonicalEvent
from synthesis.generator import generate_vault
from synthesis.redaction import shorthash
from synthesis.publisher import SynthesisPublisher


def _ev() -> CanonicalEvent:
    return CanonicalEvent.from_dict(
        {
            "schema_version": 1,
            "event_id": "01JS3PUB",
            "parent_event_id": "01J0000",
            "event_type": "retrieval_breakdown",
            "company_id": "MJC",
            "repository_id": "marrow",
            "plan_id": "p1",
            "task_id": "t1",
            "handoff_id": "h1",
            "agent_name": "a",
            "agent_run_id": "r1",
            "actor_id": "a1",
            "model": "m",
            "timestamp": "2026-01-01T00:00:00Z",
            "state_version": 1,
            "payload": {"phase": "scoper", "agent": "x", "sources": {}},
        }
    )


@mock_aws
def test_publish_is_idempotent_no_duplicate_writes() -> None:
    bucket = "moto-synth-idem"
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=bucket)
    ev = _ev()
    bundle = generate_vault(
        [ev],
        company_id="MJC",
        repository_id="marrow",
        cutoff_timestamp="2026-12-31T00:00:00Z",
    )
    pfx = f"vault/{shorthash('MJC')}/{shorthash('marrow')}"
    pub = SynthesisPublisher(
        bucket=bucket,
        s3_client=s3,
        prefix=pfx,
    )
    a = pub.publish(bundle)
    n = len(bundle.pages)
    assert a.written == n
    b = pub.publish(bundle)
    assert b.written == 0
    assert b.skipped == n
    head = s3.head_object(
        Bucket=bucket,
        Key=f"{pfx}/README.md",
    )
    h = (head.get("Metadata", {}) or {}).get("content-hash", "")
    assert len(h) == 64
    for ch in h:
        assert ch in "0123456789abcdef"
