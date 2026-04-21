import json
from pathlib import Path

from canon_systems import dor_log, shared


def _reset_repo_root_cache(monkeypatch) -> None:
    monkeypatch.setattr(shared, "_CACHED_REPO_ROOT", None)


def test_dor_log_success_does_not_queue(monkeypatch, tmp_path: Path) -> None:
    _reset_repo_root_cache(monkeypatch)
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("CANON_DOR_LOG_URL", "https://example.test/dor")
    monkeypatch.setattr(dor_log, "_post_json", lambda *_args, **_kwargs: (202, "ok"))

    code = dor_log.run(["--event-json", '{"stage":"scoper","handoff_id":"h1"}', "--quiet"])
    assert code == 0
    assert not (tmp_path / ".canon" / "memory" / "dor-failure-queue.jsonl").exists()


def test_dor_log_queues_on_send_failure(monkeypatch, tmp_path: Path) -> None:
    _reset_repo_root_cache(monkeypatch)
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("CANON_DOR_LOG_URL", "https://example.test/dor")
    monkeypatch.setattr(dor_log, "_post_json", lambda *_args, **_kwargs: (0, "timeout"))

    code = dor_log.run(["--event-json", '{"stage":"scoper","handoff_id":"h2"}', "--quiet"])
    assert code == 0

    q = tmp_path / ".canon" / "memory" / "dor-failure-queue.jsonl"
    assert q.exists()
    lines = q.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["event"]["handoff_id"] == "h2"


def test_dor_log_strict_returns_nonzero_on_failure(monkeypatch, tmp_path: Path) -> None:
    _reset_repo_root_cache(monkeypatch)
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("CANON_DOR_LOG_URL", "https://example.test/dor")
    monkeypatch.setattr(dor_log, "_post_json", lambda *_args, **_kwargs: (503, "down"))

    code = dor_log.run(["--event-json", '{"stage":"scoper","handoff_id":"h3"}', "--quiet", "--strict"])
    assert code == 1


def test_dor_log_flush_queue_retries_and_clears(monkeypatch, tmp_path: Path) -> None:
    _reset_repo_root_cache(monkeypatch)
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("CANON_DOR_LOG_URL", "https://example.test/dor")

    monkeypatch.setattr(dor_log, "_post_json", lambda *_args, **_kwargs: (0, "timeout"))
    dor_log.run(["--event-json", '{"stage":"scoper","handoff_id":"h4"}', "--quiet"])

    calls = {"count": 0}

    def _ok(*_args, **_kwargs):
        calls["count"] += 1
        return 201, "ok"

    monkeypatch.setattr(dor_log, "_post_json", _ok)
    code = dor_log.run(
        [
            "--flush-queue",
            "--event-json",
            '{"stage":"cursor-pilot-preflight","handoff_id":"h5"}',
            "--quiet",
        ]
    )
    assert code == 0
    assert calls["count"] >= 2  # queued event + current event
    assert not (tmp_path / ".canon" / "memory" / "dor-failure-queue.jsonl").exists()
