from __future__ import annotations

from fastapi.testclient import TestClient


def test_vault_home_lists_pages_and_links(
    client: TestClient,
    vault_ids: tuple[str, str, str, str],
) -> None:
    c1, r1, _, _ = vault_ids
    r = client.get(f"/v/{c1}/{r1}/")
    assert r.status_code == 200
    text = r.text
    assert "plans/P1/index.md" in text or "Plan P1" in text
    assert "_index/plans.md" in text or "Index pages" in text
    assert f"/v/{c1}/{r1}/_graph" in text
    assert f"/v/{c1}/{r1}/_search" in text
