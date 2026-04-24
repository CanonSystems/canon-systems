"""Tests for `canon doctor`."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

import canon_systems.doctor_cli as dr


def test_doctor_json_ok_when_wired_no_hits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".canon").mkdir(parents=True)
    (tmp_path / ".canon" / "memory-layer.local.env").write_text(
        "COMPANY_ID=ACME\nREPOSITORY_ID=demo\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dr, "repo_root", lambda: tmp_path)
    buf = io.StringIO()
    monkeypatch.setattr(dr.sys, "stdout", buf)
    assert dr.run(["--json"]) == 0
    o = json.loads(buf.getvalue())
    assert o["company_id_file"] == "ACME"
    assert o["tenant_context_mismatch"] is False
    assert o["canonical_memory_https_url_keys"] == [
        "KNOWLEDGE_API_URL",
        "KNOWLEDGE_WORKER_URL",
        "MEMORY_ADAPTER_URL",
        "CANON_STATE_API_URL",
    ]


def test_doctor_warns_literal_ip_in_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".canon").mkdir(parents=True)
    (tmp_path / ".canon" / "memory-layer.local.env").write_text(
        "COMPANY_ID=ACME\n"
        "REPOSITORY_ID=demo\n"
        "KNOWLEDGE_API_URL=http://10.0.0.1:8080\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dr, "repo_root", lambda: tmp_path)
    assert dr.run(["--json"]) == 1


def test_doctor_tenant_mismatch_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".canon").mkdir(parents=True)
    (tmp_path / ".canon" / "memory-layer.local.env").write_text(
        "COMPANY_ID=ACME\nREPOSITORY_ID=demo\n",
        encoding="utf-8",
    )
    (tmp_path / ".canon" / "memory").mkdir(parents=True)
    (tmp_path / ".canon" / "memory" / "context-latest.md").write_text(
        "# Session Memory Context\n\n- company_id: `OTHER`\n- repository_id: `demo`\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dr, "repo_root", lambda: tmp_path)
    buf = io.StringIO()
    monkeypatch.setattr(dr.sys, "stdout", buf)
    assert dr.run(["--json"]) == 1
    o = json.loads(buf.getvalue())
    assert o["tenant_context_mismatch"] is True
