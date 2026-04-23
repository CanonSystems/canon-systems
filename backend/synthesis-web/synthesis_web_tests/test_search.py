from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient

from synthesis_web.main import app, get_reader
from synthesis_web.reader import S3VaultReader

from ._fakes import DictS3Client

BUCKET = "synthesis-web-test"


def _sh(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _put(s3: DictS3Client, rel_key: str, body: bytes) -> None:
    s3.put_object(
        Bucket=BUCKET,
        Key=f"vault/{rel_key}",
        Body=body,
        Metadata={"content-hash": _sh(body)},
    )


@pytest.fixture
def search_client(vault_ids: tuple[str, str, str, str]) -> TestClient:
    c1, r1, _, _ = vault_ids
    s3 = DictS3Client()
    base = f"{c1}/{r1}"
    _put(s3, f"{base}/README.md", b"---\n---\n\n# root\n")
    for i in range(30):
        body = f"---\n---\n\npage {i} foo match\n".encode()
        _put(s3, f"{base}/searchpages/page{i}.md", body)
    reader = S3VaultReader(bucket=BUCKET, prefix="vault", s3_client=s3)
    app.dependency_overrides[get_reader] = lambda: reader
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


def test_search_honors_limit_and_truncation(
    search_client: TestClient,
    vault_ids: tuple[str, str, str, str],
) -> None:
    c1, r1, _, _ = vault_ids
    r = search_client.get(f"/v/{c1}/{r1}/_search", params={"q": "foo", "limit": 10})
    assert r.status_code == 200
    data = r.json()
    assert data["q"] == "foo"
    assert len(data["matches"]) == 10
    assert data["truncated"] is True
