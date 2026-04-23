from __future__ import annotations

import hashlib
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from synthesis_web.main import app, get_reader
from synthesis_web.reader import S3VaultReader

from ._fakes import DictS3Client

BUCKET = "synthesis-web-test"


def _sh(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _sh8(label: bytes) -> str:
    return hashlib.sha256(label).hexdigest()[:8]


def _put(s3: DictS3Client, rel_key: str, body: bytes) -> None:
    key = f"vault/{rel_key}"
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=body,
        ContentType="text/markdown",
        Metadata={"content-hash": _sh(body)},
    )


@pytest.fixture
def vault_ids() -> tuple[str, str, str, str]:
    c1 = _sh8(b"IMC")
    r1 = _sh8(b"innermost")
    c2 = _sh8(b"ACME")
    r2 = _sh8(b"widgets")
    return (c1, r1, c2, r2)


@pytest.fixture
def fake_s3(vault_ids: tuple[str, str, str, str]) -> DictS3Client:
    c1, r1, c2, r2 = vault_ids
    s3 = DictS3Client()
    base1 = f"{c1}/{r1}"
    _put(s3, f"{base1}/README.md", b"---\ntitle: Readme\n---\n\n# Vault one\n")
    _put(s3, f"{base1}/_index/plans.md", b"---\n---\n\n# Plan index\n")
    _put(
        s3,
        f"{base1}/plans/P1/index.md",
        b"---\nplan_id: P1\n---\n\n# Plan P1\n",
    )
    _put(
        s3,
        f"{base1}/plans/P1/tasks/T1/index.md",
        b"---\n---\n\nTask T1 links [[plan:P1]] here.\n",
    )
    _put(
        s3,
        f"{base1}/plans/P1/tasks/T2/index.md",
        b"---\n---\n\nTask T2 has [[plan:does-not-exist]] and [[plan:P1]].\n",
    )
    base2 = f"{c2}/{r2}"
    _put(s3, f"{base2}/README.md", b"---\n---\n\n# Second vault\n")
    return s3


@pytest.fixture
def reader(fake_s3: DictS3Client) -> S3VaultReader:
    return S3VaultReader(bucket=BUCKET, prefix="vault", s3_client=fake_s3)


@pytest.fixture
def client(reader: S3VaultReader) -> Iterator[TestClient]:
    app.dependency_overrides[get_reader] = lambda: reader
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
