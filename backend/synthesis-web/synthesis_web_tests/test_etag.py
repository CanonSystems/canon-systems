from __future__ import annotations

import hashlib
import re

from fastapi.testclient import TestClient

from ._fakes import DictS3Client


def test_content_hash_etag_honors_if_none_match(
    client: TestClient,
    vault_ids: tuple[str, str, str, str],
) -> None:
    c1, r1, _, _ = vault_ids
    url = f"/v/{c1}/{r1}/plans/P1/tasks/T1/index.md"
    first = client.get(url)
    assert first.status_code == 200
    etag = first.headers.get("etag")
    assert etag
    assert re.match(r'^"[0-9a-f]{64}"$', etag)
    second = client.get(url, headers={"If-None-Match": etag})
    assert second.status_code == 304
    assert second.content == b""


def test_changing_content_busts_etag(
    client: TestClient,
    fake_s3: DictS3Client,
    vault_ids: tuple[str, str, str, str],
) -> None:
    """Mutating the underlying S3 object's content-hash metadata MUST bust the ETag
    and force a fresh 200 (not 304), proving the cache key tracks content."""
    c1, r1, _, _ = vault_ids
    url = f"/v/{c1}/{r1}/plans/P1/tasks/T1/index.md"
    first = client.get(url)
    assert first.status_code == 200
    first_etag = first.headers["etag"]

    key = f"vault/{c1}/{r1}/plans/P1/tasks/T1/index.md"
    new_body = b"---\n---\n\nTask T1 links [[plan:P1]] here.\n\n## NEW SECTION\n"
    fake_s3.objects[key]["Body"] = new_body
    fake_s3.objects[key]["Metadata"] = {"content-hash": hashlib.sha256(new_body).hexdigest()}

    second = client.get(url, headers={"If-None-Match": first_etag})
    assert second.status_code == 200, "stale If-None-Match must not return 304 after content change"
    assert second.headers["etag"] != first_etag
    assert "NEW SECTION" in second.text

    third = client.get(url, headers={"If-None-Match": second.headers["etag"]})
    assert third.status_code == 304
    assert third.content == b""
