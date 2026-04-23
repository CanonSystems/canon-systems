from __future__ import annotations

from fastapi.testclient import TestClient


def test_index_lists_multiple_vaults(client: TestClient, vault_ids: tuple[str, str, str, str]) -> None:
    c1, r1, c2, r2 = vault_ids
    r = client.get("/")
    assert r.status_code == 200
    text = r.text
    assert f"/v/{c1}/{r1}/" in text
    assert f"/v/{c2}/{r2}/" in text
