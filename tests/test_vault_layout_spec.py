from dataclasses import fields
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_vault_layout_spec_is_schema_v1_and_has_required_sections() -> None:
    spec = REPO_ROOT / "docs" / "VAULT-LAYOUT.md"
    assert spec.is_file(), f"Vault layout spec missing at {spec}"
    body = spec.read_text(encoding="utf-8")
    assert "schema_version: 1" in body
    for heading in (
        "## 1. Layout overview",
        "## 2. Scoping (per-company + per-repo)",
        "## 3. Markdown file contract",
        "## 4. .obsidian/ seed config",
        "## 5. Event-field allowlist (redaction)",
        "## 6. Per-page type catalogue",
        "## 7. Citation contract",
        "## 8. Idempotence contract",
        "## 9. Versioning policy",
    ):
        assert heading in body, f"Missing required section: {heading}"
    assert "attachments/" in body
    assert "wikilinks" in body.lower() or "[[" in body
    assert ".obsidian/" in body
    assert "schema_version" in body


def test_vault_layout_allowlist_covers_canonical_event_fields_and_backend_readme_links() -> None:
    import sys
    sys.path.insert(0, str(REPO_ROOT / "backend" / "shared"))
    from canon_backend_shared.events import CanonicalEvent  # type: ignore  # noqa: E402

    spec_body = (REPO_ROOT / "docs" / "VAULT-LAYOUT.md").read_text(encoding="utf-8")

    canonical_fields = {f.name for f in fields(CanonicalEvent)} - {"payload"}
    for field_name in canonical_fields:
        assert f"`{field_name}`" in spec_body, (
            f"CanonicalEvent field {field_name!r} missing from §5 allowlist table"
        )

    assert "DROPPED" in spec_body
    assert "`model`" in spec_body
    assert "silently drop" in spec_body.lower() or "silently dropped" in spec_body.lower()

    backend_readme = (REPO_ROOT / "backend" / "synthesis" / "README.md").read_text(encoding="utf-8")
    assert "docs/VAULT-LAYOUT.md" in backend_readme
    assert "schema_version: 1" in backend_readme
