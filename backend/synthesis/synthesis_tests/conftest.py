from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from canon_backend_shared.events import CanonicalEvent

from synthesis.main import app


def _ce(
    **kwargs: object,
) -> CanonicalEvent:
    d = {
        "schema_version": 1,
        "event_id": "01JXXXX",
        "parent_event_id": "01J0000",
        "event_type": "retrieval_breakdown",
        "company_id": "MJC",
        "repository_id": "marrow",
        "plan_id": "plan-a",
        "task_id": "E5-T2",
        "handoff_id": "h1",
        "agent_name": "implementer",
        "agent_run_id": "run-1",
        "actor_id": "actor-1",
        "model": "gpt-5",
        "timestamp": "2026-04-23T10:00:00Z",
        "state_version": 1,
        "payload": {"phase": "implementer", "agent": "a", "sources": {}},
    }
    d.update(kwargs)
    return CanonicalEvent.from_dict(d)


@pytest.fixture
def event_factory() -> type:
    return _ce


@pytest.fixture
def dict_s3_client():
    from _fakes import DictS3Client

    return DictS3Client()


@pytest.fixture
def moto_s3_bucket():
    pytest.importorskip("moto")
    return "synthesis-moto-bucket"


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
