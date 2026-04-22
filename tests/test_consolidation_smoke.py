"""Structural checks for Wave 0 consolidation smoke harness (hermetic; no shell-outs)."""

from __future__ import annotations

import ast
import importlib.util
import stat
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "smoke-test.sh"
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"
GITIGNORE = REPO_ROOT / ".gitignore"
WAVE0_CLOSEOUT = REPO_ROOT / "docs" / "WAVE-0-CLOSEOUT.md"


def _require_yaml():
    if importlib.util.find_spec("yaml") is None:
        pytest.skip("pyyaml required (pip install -r requirements-dev.txt)")


def test_smoke_script_exists_executable_and_content():
    assert SMOKE_SCRIPT.is_file(), f"missing {SMOKE_SCRIPT}"
    mode = SMOKE_SCRIPT.stat().st_mode
    assert mode & stat.S_IXUSR, f"{SMOKE_SCRIPT} not owner-executable"
    text = SMOKE_SCRIPT.read_text(encoding="utf-8")
    assert "set -euo pipefail" in text
    assert "scripts/backend/build-services.sh" in text
    assert "pytest" in text
    assert "terraform validate" in text


def test_ci_yml_parses_and_smoke_job_contract():
    _require_yaml()
    import yaml  # type: ignore[import-untyped]

    data = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))
    assert data.get("name") == "Canon Smoke Test"
    jobs = data.get("jobs") or {}
    job = jobs.get("smoke-test")
    assert job is not None, "jobs.smoke-test missing"
    assert job.get("runs-on") == "ubuntu-latest"
    assert job.get("timeout-minutes") == 20

    steps = job.get("steps") or []
    run_lines: list[str] = []
    found_py_311 = False
    for step in steps:
        if not isinstance(step, dict):
            continue
        r = step.get("run")
        if isinstance(r, str):
            run_lines.append(r)
        u = step.get("uses", "")
        if isinstance(u, str) and "actions/setup-python" in u:
            w = step.get("with") or {}
            pv = w.get("python-version")
            if isinstance(pv, (int, float)):
                pv = str(pv)
            if isinstance(pv, str) and pv.strip().startswith("3.11"):
                found_py_311 = True

    assert found_py_311, "setup-python@3.11 required"

    # bash scripts/smoke-test.sh in a run step
    run_blob = "\n".join(run_lines)
    assert "bash scripts/smoke-test.sh" in run_blob, run_blob

    # setup-terraform
    uses_steps = [s.get("uses") for s in steps if isinstance(s, dict)]
    assert any(
        isinstance(u, str) and "hashicorp/setup-terraform" in u for u in uses_steps
    )


def test_venv_smoke_gitignored():
    lines = GITIGNORE.read_text(encoding="utf-8").splitlines()
    assert any(line.strip() == ".venv-smoke/" for line in lines)


def test_wave0_closeout_doc_and_oq_refs():
    assert WAVE0_CLOSEOUT.is_file()
    text = WAVE0_CLOSEOUT.read_text(encoding="utf-8")
    assert "OQ-E0-T4-01" in text
    assert "OQ-E0-T5-01" in text


def test_hermetic_guard_no_subprocess_module():
    """Guardrail: this module must not import or load the stdlib subprocess module."""
    p = Path(__file__).resolve()
    tree = ast.parse(p.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "subprocess" or (
                    isinstance(alias.name, str) and alias.name.startswith("subprocess.")
                ):
                    raise AssertionError("subprocess import is forbidden in consolidation smoke test")
        if isinstance(node, ast.ImportFrom) and node.module in ("subprocess",):
            raise AssertionError("subprocess import is forbidden in consolidation smoke test")
