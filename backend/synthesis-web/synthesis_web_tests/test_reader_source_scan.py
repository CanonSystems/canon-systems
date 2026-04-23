from __future__ import annotations

import re
from pathlib import Path

_FORBIDDEN_METHODS = (
    "put_object",
    "put_object_acl",
    "put_object_tagging",
    "put_object_retention",
    "put_object_legal_hold",
    "put_bucket_policy",
    "put_bucket_acl",
    "delete_object",
    "delete_objects",
    "delete_object_tagging",
    "copy_object",
    "copy",
    "upload_file",
    "upload_fileobj",
    "upload_part",
    "upload_part_copy",
    "create_multipart_upload",
    "complete_multipart_upload",
    "abort_multipart_upload",
    "restore_object",
    "write_get_object_response",
)


def test_reader_source_has_no_write_calls() -> None:
    root = Path(__file__).resolve().parents[1]
    src = (root / "synthesis_web" / "reader.py").read_text(encoding="utf-8")
    pattern = r"\b(" + "|".join(re.escape(m) for m in _FORBIDDEN_METHODS) + r")\s*\("
    forbidden = re.compile(pattern)
    match = forbidden.search(src)
    assert match is None, f"reader.py must not contain S3 write call sites; found: {match.group(0) if match else ''}"


def test_reader_source_scan_regex_detects_sample_writes() -> None:
    """Self-check: prove the forbidden regex would catch a write-call site."""
    pattern = r"\b(" + "|".join(re.escape(m) for m in _FORBIDDEN_METHODS) + r")\s*\("
    forbidden = re.compile(pattern)
    for name in _FORBIDDEN_METHODS:
        sample = f"self._s3.{name}(Bucket='b', Key='k')"
        assert forbidden.search(sample) is not None, f"regex failed to detect {name}"
