from __future__ import annotations

import re

from fastapi.testclient import TestClient

_CDN_RE = re.compile(
    r'<(?:script|link|img)\b[^>]*?\b(?:src|href)\s*=\s*["\']https?://',
    re.IGNORECASE,
)


def test_no_external_cdn_in_rendered_html(
    client: TestClient,
    vault_ids: tuple[str, str, str, str],
) -> None:
    c1, r1, _, _ = vault_ids
    paths = [
        "/",
        f"/v/{c1}/{r1}/",
        f"/v/{c1}/{r1}/plans/P1/index.md",
        f"/v/{c1}/{r1}/plans/P1/tasks/T1/index.md",
    ]
    for p in paths:
        r = client.get(p)
        assert r.status_code == 200
        assert _CDN_RE.search(r.text) is None
