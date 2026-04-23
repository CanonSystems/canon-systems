from __future__ import annotations

from fastapi.testclient import TestClient


def test_page_resolves_wikilinks_to_internal_urls(
    client: TestClient,
    vault_ids: tuple[str, str, str, str],
) -> None:
    c1, r1, _, _ = vault_ids
    r = client.get(f"/v/{c1}/{r1}/plans/P1/tasks/T1/index.md")
    assert r.status_code == 200
    assert f'href="/v/{c1}/{r1}/plans/P1/index.md"' in r.text
    assert 'class="wikilink"' in r.text


def test_unknown_wikilink_renders_as_inactive_span(
    client: TestClient,
    vault_ids: tuple[str, str, str, str],
) -> None:
    c1, r1, _, _ = vault_ids
    r = client.get(f"/v/{c1}/{r1}/plans/P1/tasks/T2/index.md")
    assert r.status_code == 200
    assert 'class="wikilink-unresolved"' in r.text
    assert "does-not-exist" in r.text
    idx = r.text.index("does-not-exist")
    open_idx = r.text.rfind("<span", 0, idx)
    close_idx = r.text.find("</span>", idx)
    assert open_idx != -1 and close_idx != -1
    span_fragment = r.text[open_idx : close_idx + len("</span>")]
    assert 'class="wikilink-unresolved"' in span_fragment
    assert "<a " not in span_fragment
    assert "href=" not in span_fragment
