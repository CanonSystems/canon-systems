from __future__ import annotations

from pathlib import Path

from canon_systems import secrets_submit


class _MissingSecretError(Exception):
    def __init__(self) -> None:
        super().__init__("not found")
        self.response = {"Error": {"Code": "ResourceNotFoundException"}}


class _FakeSecretsClient:
    def __init__(self, *, exists: bool) -> None:
        self.exists = exists
        self.put_calls: list[dict[str, str]] = []
        self.create_calls: list[dict[str, str]] = []

    def describe_secret(self, SecretId: str) -> dict[str, str]:
        if not self.exists:
            raise _MissingSecretError()
        return {"Name": SecretId}

    def put_secret_value(self, SecretId: str, SecretString: str) -> dict[str, str]:
        self.put_calls.append({"SecretId": SecretId, "SecretString": SecretString})
        return {"VersionId": "ver_put"}

    def create_secret(self, Name: str, SecretString: str) -> dict[str, str]:
        self.create_calls.append({"Name": Name, "SecretString": SecretString})
        return {"VersionId": "ver_create"}

    def get_secret_value(self, SecretId: str) -> dict[str, str]:
        raise _MissingSecretError()


def _write_repo_scope(tmp_path: Path) -> None:
    env_path = tmp_path / ".canon" / "memory-layer.local.env"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(
        "\n".join(
            [
                "COMPANY_ID=IMC",
                "REPOSITORY_ID=innermost",
                "MEMORY_LAYER_AWS_SECRET_NAME_PREFIX=canon-memory-dev",
                "AWS_REGION=us-east-1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_template_outputs_structured_payload(capsys) -> None:
    code = secrets_submit.run(["template", "--company-id", "IMC", "--repository-id", "innermost"])
    assert code == 0
    out = capsys.readouterr().out
    assert '"COMPANY_ID": "IMC"' in out
    assert '"REPOSITORY_ID": "innermost"' in out
    assert '"CANON_STATE_API_URL": "https://memory.canon-systems.com"' in out
    assert '"CANON_HTTP_BEARER_TOKEN": "<token>"' in out


def test_submit_validates_and_writes_existing_secret(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _write_repo_scope(tmp_path)
    monkeypatch.setattr("canon_systems.shared._CACHED_REPO_ROOT", None)
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))

    client = _FakeSecretsClient(exists=True)
    monkeypatch.setattr(secrets_submit, "_secrets_client", lambda profile, region: client)

    code = secrets_submit.run(
        [
            "submit",
            "--company-id",
            "IMC",
            "--repository-id",
            "innermost",
            "--prefix",
            "canon-memory-dev",
            "--aws-region",
            "us-east-1",
            "--set",
            "KNOWLEDGE_API_URL=https://memory.canon-systems.com",
            "--set",
            "KNOWLEDGE_WORKER_URL=https://memory.canon-systems.com",
            "--set",
            "MEMORY_ADAPTER_URL=https://memory.canon-systems.com",
            "--set",
            "SCOPE_ARTIFACT_BUCKET=canon-systems-v2-dev-artifacts",
            "--set",
            "CANON_HTTP_BEARER_TOKEN=tok",
        ]
    )
    assert code == 0
    assert len(client.put_calls) == 1
    assert not client.create_calls
    import json

    stored = json.loads(client.put_calls[0]["SecretString"])
    assert stored.get("CANON_STATE_API_URL") == "https://memory.canon-systems.com"
    out = capsys.readouterr().out
    assert "canon secrets submit: success via put_secret_value" in out


def test_submit_requires_missing_keys_without_allow_partial(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _write_repo_scope(tmp_path)
    monkeypatch.setattr("canon_systems.shared._CACHED_REPO_ROOT", None)
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))

    code = secrets_submit.run(
        [
            "submit",
            "--company-id",
            "IMC",
            "--repository-id",
            "innermost",
            "--prefix",
            "canon-memory-dev",
            "--aws-region",
            "us-east-1",
            "--dry-run",
        ]
    )
    assert code == 2
    out = capsys.readouterr().out
    assert "missing required keys" in out


def test_wizard_collects_prompts_and_runs_dry_run(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _write_repo_scope(tmp_path)
    monkeypatch.setattr("canon_systems.shared._CACHED_REPO_ROOT", None)
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    monkeypatch.setattr(secrets_submit, "_secrets_client", lambda profile, region: _FakeSecretsClient(exists=False))

    answers = iter(
        [
            "IMC",
            "innermost",
            "canon-memory-dev",
            "us-east-1",
            "canon-systems",
            "",
            "n",
            "https://memory.canon-systems.com",
            "https://memory.canon-systems.com",
            "https://memory.canon-systems.com",
            "canon-systems-v2-dev-artifacts",
            "y",
            "y",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(secrets_submit.getpass, "getpass", lambda _: "tok")

    code = secrets_submit.run(["wizard", "--dry-run"])
    assert code == 0
    out = capsys.readouterr().out
    assert "Canon secrets wizard" in out
    assert "canon secrets submit plan:" in out
