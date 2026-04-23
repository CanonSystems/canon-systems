from __future__ import annotations

from fastapi.testclient import TestClient


def test_missing_page_returns_404_html(
    client: TestClient,
    vault_ids: tuple[str, str, str, str],
) -> None:
    c1, r1, _, _ = vault_ids
    path = "plans/nope/missing.md"
    r = client.get(f"/v/{c1}/{r1}/{path}")
    assert r.status_code == 404
    text = r.text
    assert c1 in text and r1 in text
    assert path in text
    assert "Return to vault home" in text
