from __future__ import annotations

from fastapi.testclient import TestClient


def test_backlinks_section_lists_linking_pages(
    client: TestClient,
    vault_ids: tuple[str, str, str, str],
) -> None:
    c1, r1, _, _ = vault_ids
    r = client.get(f"/v/{c1}/{r1}/plans/P1/index.md")
    assert r.status_code == 200
    assert "Backlinks" in r.text
    assert f"/v/{c1}/{r1}/plans/P1/tasks/T1/index.md" in r.text
    assert f"/v/{c1}/{r1}/plans/P1/tasks/T2/index.md" in r.text
