from pathlib import Path

from memory_layer import __version__
from memory_layer.version_check import _version_tuple, check


def test_version_tuple_parses_digits_and_falls_back():
    assert _version_tuple("1.2.3") == (1, 2, 3)
    assert _version_tuple("0.2.0") == (0, 2, 0)
    assert _version_tuple("garbage") == (0,)


def test_check_ok_when_no_pin(tmp_path: Path):
    ok, _msg = check(tmp_path)
    assert ok is True


def test_check_ok_when_pin_equal(tmp_path: Path):
    env = tmp_path / ".canon" / "memory-layer.local.env"
    env.parent.mkdir(parents=True)
    env.write_text(f"CANON_MEMORY_LAYER_VERSION={__version__}\n", encoding="utf-8")
    ok, _ = check(tmp_path)
    assert ok is True


def test_check_fails_when_installed_older_than_pin(tmp_path: Path):
    env = tmp_path / ".canon" / "memory-layer.local.env"
    env.parent.mkdir(parents=True)
    # Pin something guaranteed to be newer than installed.
    env.write_text("CANON_MEMORY_LAYER_VERSION=999.0.0\n", encoding="utf-8")
    ok, msg = check(tmp_path)
    assert ok is False
    assert "pipx upgrade canon-memory-layer" in msg


def test_check_ok_when_installed_newer_than_pin(tmp_path: Path):
    env = tmp_path / ".canon" / "memory-layer.local.env"
    env.parent.mkdir(parents=True)
    env.write_text("CANON_MEMORY_LAYER_VERSION=0.0.1\n", encoding="utf-8")
    ok, _ = check(tmp_path)
    assert ok is True
