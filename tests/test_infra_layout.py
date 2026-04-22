"""Layout contracts for `infra/` (E0-T4 Terraform mirror + auth-ingress isolation)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INFRA = REPO_ROOT / "infra"
TERRAFORM_ROOT = INFRA / "terraform"
AUTH_INGRESS = INFRA / "auth-ingress"

ROOT_TERRAFORM_FILES = frozenset(
    {
        "main.tf",
        "variables.tf",
        "outputs.tf",
        "providers.tf",
        "versions.tf",
        "terraform.tfvars",
    }
)

MODULE_NAMES = (
    "vpc",
    "ecr",
    "ecs-fargate",
    "rds-postgres",
    "s3-artifacts",
    "secrets",
)

MODULE_TRIO = frozenset({"main.tf", "variables.tf", "outputs.tf"})


def test_terraform_root_files_present() -> None:
    present = {p.name for p in TERRAFORM_ROOT.iterdir() if p.is_file()}
    missing = ROOT_TERRAFORM_FILES - present
    assert not missing, f"Missing root Terraform files: {sorted(missing)}"


def test_terraform_modules_present() -> None:
    for mod in MODULE_NAMES:
        mod_dir = TERRAFORM_ROOT / "modules" / mod
        assert mod_dir.is_dir(), f"Missing module directory: {mod_dir}"
        files = {p.name for p in mod_dir.iterdir() if p.is_file()}
        missing = MODULE_TRIO - files
        assert not missing, f"Module {mod} missing files: {sorted(missing)}"


def test_no_tfstate_committed() -> None:
    matches = list(INFRA.glob("**/terraform.tfstate*"))
    assert matches == [], f"terraform.tfstate* must not be committed: {matches}"


def test_no_terraform_lock_committed() -> None:
    matches = list(INFRA.glob("**/.terraform.lock.hcl"))
    assert matches == [], f".terraform.lock.hcl must not be committed: {matches}"


def test_no_terraform_cache_committed() -> None:
    terraform_dirs = [p for p in INFRA.rglob(".terraform") if p.is_dir()]
    assert terraform_dirs == [], f".terraform/ must not exist under infra/: {terraform_dirs}"


def test_auth_ingress_untouched() -> None:
    assert AUTH_INGRESS.is_dir()
    basenames = {p.name for p in AUTH_INGRESS.iterdir() if p.is_file()}
    expected = {
        "canon-systems-com-ingress.tf",
        "cognito-auth-resources.tf",
        "variables.tf",
    }
    assert basenames == expected, (
        f"auth-ingress must expose exactly {expected}, got {basenames}"
    )


def test_migration_note_exists() -> None:
    note = REPO_ROOT / "docs" / "E0-T4-INFRA-IMPORT.md"
    text = note.read_text(encoding="utf-8")
    assert note.is_file()
    assert "ebecb91" in text
    assert "no cloud commands" in text


def test_import_manifest_exists() -> None:
    readme = TERRAFORM_ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    ecr_keys = (
        "canon/jira-bridge",
        "canon/knowledge-api",
        "canon/knowledge-worker",
        "canon/temporal-runtime",
    )
    for key in ecr_keys:
        fragment = f'terraform import \'module.ecr.aws_ecr_repository.this["{key}"]\''
        assert fragment in text, f"Missing terraform import line for ECR repo {key}"
    assert text.count("terraform import") >= len(ecr_keys)
