"""Layout and shared-lib contracts for `backend/` (E0-T2)."""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND = REPO_ROOT / "backend"
SHARED_ON_PATH = REPO_ROOT / "backend" / "shared"

SERVICE_SLUGS = (
    "knowledge-api",
    "knowledge-worker",
    "memory-adapter",
    "state-api",
    "axon-service",
    "synthesis",
    "synthesis-web",
)

PYTHON_SERVICES: dict[str, str] = {
    "knowledge-api": "app",
    "knowledge-worker": "knowledge_worker",
    "memory-adapter": "memory_adapter",
    "state-api": "state_api",
    "axon-service": "axon_service",
    "synthesis": "synthesis",
}


def _ensure_shared_importable() -> None:
    s = str(SHARED_ON_PATH)
    if s not in sys.path:
        sys.path.insert(0, s)


@pytest.mark.parametrize("slug", SERVICE_SLUGS)
def test_seven_service_dirs_exist(slug: str) -> None:
    d = BACKEND / slug
    assert d.is_dir()
    readme = d / "README.md"
    assert readme.is_file()
    assert readme.read_text(encoding="utf-8").strip() != ""


@pytest.mark.parametrize("slug,pkg", PYTHON_SERVICES.items())
def test_python_services_have_entrypoints(slug: str, pkg: str) -> None:
    base = BACKEND / slug
    assert (base / "pyproject.toml").is_file()
    main_py = base / pkg / "main.py"
    assert main_py.is_file()
    tree = ast.parse(main_py.read_text(encoding="utf-8"))
    has_app = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "app":
                    has_app = True
    assert has_app, f"{main_py} must assign module-level `app`"


def test_synthesis_web_is_readme_only() -> None:
    sw = BACKEND / "synthesis-web"
    assert (sw / "README.md").is_file()
    assert (sw / ".gitkeep").is_file()
    assert not (sw / "pyproject.toml").exists()
    pys = list(sw.rglob("*.py"))
    assert pys == []


def test_shared_modules_importable() -> None:
    for name in ("auth.py", "ids.py", "events.py"):
        p = BACKEND / "shared" / "canon_backend_shared" / name
        assert p.is_file()
    _ensure_shared_importable()
    import canon_backend_shared.auth as auth
    import canon_backend_shared.events as events
    import canon_backend_shared.ids as ids

    assert hasattr(auth, "verify_caller")
    assert hasattr(ids, "deterministic_id")
    assert hasattr(events, "CanonicalEvent")


def test_deterministic_id_is_stable_and_supports_prefix() -> None:
    _ensure_shared_importable()
    from canon_backend_shared import ids

    a = ids.deterministic_id("a", "b")
    b = ids.deterministic_id("a", "b")
    assert a == b
    assert len(a) == 64
    p = ids.deterministic_id("a", "b", prefix="evt")
    assert p.startswith("evt_")
    assert p.split("_", 1)[1] == a


def test_canonical_event_roundtrip() -> None:
    _ensure_shared_importable()
    from canon_backend_shared.events import CanonicalEvent

    minimal = CanonicalEvent(
        schema_version=1,
        event_id="e1",
        parent_event_id="p0",
        event_type="qa_result",
        company_id="IMC",
        repository_id="innermost",
        plan_id="canon_memory_platform_build_d21073e1",
        task_id="E0-T2",
        handoff_id="canon-memory-v1",
        agent_name="implementer",
        agent_run_id="run-1",
        actor_id="actor-1",
        model="composer-2-fast",
        timestamp="2026-04-22T00:00:00Z",
        state_version=1,
        payload={"k": "v"},
    )
    back = CanonicalEvent.from_dict(minimal.to_dict())
    assert back == minimal


def test_verify_caller_docstring_and_notimplemented() -> None:
    _ensure_shared_importable()
    from canon_backend_shared.auth import verify_caller

    assert verify_caller.__doc__ is not None
    assert "E2-T2" in verify_caller.__doc__
    assert "E1-T2" in verify_caller.__doc__
    with pytest.raises(NotImplementedError, match="real auth"):
        verify_caller({})


def test_workspace_declaration_or_script_present() -> None:
    root = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    ws = root.get("tool", {}).get("uv", {}).get("workspace", {})
    members = ws.get("members", [])
    script = REPO_ROOT / "scripts" / "backend" / "install-workspace.sh"
    assert ("backend/*" in members) or (script.is_file() and script.read_text(encoding="utf-8").strip() != "")