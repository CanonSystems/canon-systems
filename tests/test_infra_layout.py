"""Layout contracts for `infra/` (E0-T4 Terraform mirror + auth-ingress isolation)."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _infra_tracked_files() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "infra/"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in proc.stdout.splitlines() if line.strip()]
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
    tracked = _infra_tracked_files()
    bad = [p for p in tracked if p.endswith(".terraform.lock.hcl")]
    assert bad == [], f".terraform.lock.hcl must not be committed: {bad}"


def test_no_terraform_cache_committed() -> None:
    tracked = _infra_tracked_files()
    bad = [p for p in tracked if "/.terraform/" in p or p.rstrip("/").endswith("/.terraform")]
    assert bad == [], f".terraform/ contents must not be committed: {bad}"


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


DYNAMODB_CANON_STATE_MODULE = TERRAFORM_ROOT / "modules" / "dynamodb-canon-state"
DYNAMODB_MODULE_FILES = (
    "main.tf",
    "variables.tf",
    "outputs.tf",
    "README.md",
)


def test_dynamodb_canon_state_module_files_exist() -> None:
    for name in DYNAMODB_MODULE_FILES:
        path = DYNAMODB_CANON_STATE_MODULE / name
        assert path.is_file(), f"Missing module file: {path}"
        assert path.stat().st_size > 0, f"Module file is empty: {path}"


def test_dynamodb_module_has_only_name_prefix_var() -> None:
    text = (DYNAMODB_CANON_STATE_MODULE / "variables.tf").read_text(encoding="utf-8")
    assert 'variable "name_prefix"' in text
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("variable "):
            assert stripped.startswith('variable "name_prefix"'), (
                f"Unexpected variable in dynamodb-canon-state: {line!r}"
            )


def test_dynamodb_module_outputs() -> None:
    text = (DYNAMODB_CANON_STATE_MODULE / "outputs.tf").read_text(encoding="utf-8")
    assert 'output "table_name"' in text
    assert 'output "table_arn"' in text


def test_dynamodb_module_readme_mentions_keys_ttl_ppr() -> None:
    text = (DYNAMODB_CANON_STATE_MODULE / "README.md").read_text(encoding="utf-8")
    for need in ("pk", "sk", "lease_expires_at", "PAY_PER_REQUEST"):
        assert need in text, f"Module README should mention {need!r}"


def test_root_wires_state_table_module() -> None:
    main_tf = (TERRAFORM_ROOT / "main.tf").read_text(encoding="utf-8")
    assert 'module "state_table"' in main_tf
    assert "./modules/dynamodb-canon-state" in main_tf


def test_root_exposes_state_table_outputs() -> None:
    out = (TERRAFORM_ROOT / "outputs.tf").read_text(encoding="utf-8")
    assert "state_table_name" in out
    assert "state_table_arn" in out
    assert "state_run_ledger_table_name" in out
    assert "state_run_ledger_table_arn" in out


def test_root_wires_state_run_ledger_outputs_from_state_module() -> None:
    out = (TERRAFORM_ROOT / "outputs.tf").read_text(encoding="utf-8")
    assert "module.state_table.run_ledger_table_name" in out
    assert "module.state_table.run_ledger_table_arn" in out


def test_root_exposes_state_tasks_table_outputs() -> None:
    out = (TERRAFORM_ROOT / "outputs.tf").read_text(encoding="utf-8")
    assert "state_tasks_table_name" in out
    assert "state_tasks_table_arn" in out


def test_root_wires_state_tasks_outputs_from_state_module() -> None:
    out = (TERRAFORM_ROOT / "outputs.tf").read_text(encoding="utf-8")
    assert "module.state_table.tasks_table_name" in out
    assert "module.state_table.tasks_table_arn" in out


def test_dynamodb_module_declares_tasks_table() -> None:
    main_tf = (DYNAMODB_CANON_STATE_MODULE / "main.tf").read_text(encoding="utf-8")
    assert 'resource "aws_dynamodb_table" "tasks"' in main_tf
    assert "canon-tasks" in main_tf


def test_dynamodb_main_tf_key_attrs_present() -> None:
    main_tf = (DYNAMODB_CANON_STATE_MODULE / "main.tf").read_text(encoding="utf-8")
    assert 'billing_mode = "PAY_PER_REQUEST"' in main_tf
    assert 'hash_key     = "pk"' in main_tf or 'hash_key = "pk"' in main_tf
    assert 'range_key    = "sk"' in main_tf or 'range_key = "sk"' in main_tf
    assert "lease_expires_at" in main_tf
    assert "point_in_time_recovery" in main_tf
    assert "server_side_encryption" in main_tf
    assert "deletion_protection_enabled = true" in main_tf


def test_infra_terraform_readme_e2t1_section() -> None:
    text = (TERRAFORM_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## E2-T1" in text
    assert "terraform import 'module.state_table.aws_dynamodb_table.this'" in text


AXON_SNAPSHOTS_MODULE = TERRAFORM_ROOT / "modules" / "axon-snapshots"
AXON_MODULE_FILES = ("main.tf", "variables.tf", "outputs.tf", "README.md")


def test_axon_snapshots_module_files_exist() -> None:
    for name in AXON_MODULE_FILES:
        path = AXON_SNAPSHOTS_MODULE / name
        assert path.is_file(), f"Missing module file: {path}"
        assert path.stat().st_size > 0, f"Module file is empty: {path}"


def test_axon_snapshots_module_declares_s3_and_dynamodb() -> None:
    main_tf = (AXON_SNAPSHOTS_MODULE / "main.tf").read_text(encoding="utf-8")
    assert "aws_s3_bucket" in main_tf
    assert "aws_dynamodb_table" in main_tf
    assert "PAY_PER_REQUEST" in main_tf
    assert "point_in_time_recovery" in main_tf
    assert "deletion_protection_enabled" in main_tf


def test_axon_snapshots_module_exposes_expected_outputs() -> None:
    text = (AXON_SNAPSHOTS_MODULE / "outputs.tf").read_text(encoding="utf-8")
    for key in (
        "snapshots_bucket_name",
        "snapshots_bucket_arn",
        "meta_table_name",
        "meta_table_arn",
    ):
        assert f'output "{key}"' in text, f"Missing output {key}"


def test_root_wires_axon_snapshots_module() -> None:
    main_tf = (TERRAFORM_ROOT / "main.tf").read_text(encoding="utf-8")
    assert 'module "axon_snapshots"' in main_tf
    assert "./modules/axon-snapshots" in main_tf


def test_root_outputs_expose_axon_snapshots() -> None:
    out = (TERRAFORM_ROOT / "outputs.tf").read_text(encoding="utf-8")
    for key in (
        "snapshots_bucket_name",
        "snapshots_bucket_arn",
        "meta_table_name",
        "meta_table_arn",
    ):
        assert key in out, f"Missing output {key}"


def test_infra_readme_e3t1_section() -> None:
    text = (TERRAFORM_ROOT / "README.md").read_text(encoding="utf-8")
    assert "E3-T1" in text
    assert "axon-snapshots" in text


ECS_FARGATE_MODULE = TERRAFORM_ROOT / "modules" / "ecs-fargate"


def test_ecs_fargate_module_declares_optional_ingress() -> None:
    vars_tf = (ECS_FARGATE_MODULE / "variables.tf").read_text(encoding="utf-8")
    for needle in (
        'variable "ingress_enabled"',
        'variable "ingress_target_group_arn"',
        'variable "ingress_source_security_group_ids"',
    ):
        assert needle in vars_tf, f"missing {needle}"
    main_tf = (ECS_FARGATE_MODULE / "main.tf").read_text(encoding="utf-8")
    assert 'dynamic "load_balancer"' in main_tf
    assert "target_group_arn" in main_tf
    assert "ingress_target_group_arn" in main_tf
    assert 'dynamic "ingress"' in main_tf
    assert "precondition" in main_tf
    out_tf = (ECS_FARGATE_MODULE / "outputs.tf").read_text(encoding="utf-8")
    assert 'output "ingress_enabled"' in out_tf
    assert 'output "ingress_target_group_arn"' in out_tf


def test_root_wires_ecs_ingress_variables_and_outputs() -> None:
    main_tf = (TERRAFORM_ROOT / "main.tf").read_text(encoding="utf-8")
    assert "ingress_enabled" in main_tf
    assert "ingress_target_group_arn" in main_tf
    assert "ingress_source_security_group_ids" in main_tf
    root_vars = (TERRAFORM_ROOT / "variables.tf").read_text(encoding="utf-8")
    assert 'variable "ecs_ingress_enabled"' in root_vars
    assert 'variable "ecs_ingress_target_group_arn"' in root_vars
    assert 'variable "memory_plane_stable_dns_hostname"' in root_vars
    out = (TERRAFORM_ROOT / "outputs.tf").read_text(encoding="utf-8")
    assert "ecs_ingress_target_group_arn" in out
    assert "memory_plane_stable_dns_hostname" in out


def test_infra_readme_stable_ingress_section() -> None:
    text = (TERRAFORM_ROOT / "README.md").read_text(encoding="utf-8")
    assert "Optional stable ingress" in text
    assert "ecs_ingress_enabled" in text
    assert "memory-layer__csc__canon-systems" in text
    assert "canon doctor --fix-cache" in text


def test_packaged_memory_layer_defaults_tenant_context_guard() -> None:
    """Layout/docs guardrail: packaged agent rule encodes tenant vs context-latest trust boundary."""
    from importlib import resources

    body = resources.files("canon_systems.templates.rules").joinpath("memory-layer-defaults.mdc").read_text(
        encoding="utf-8",
    )
    assert "Treat `context-latest.*` as **untrusted**" in body
    assert "identity ground truth" in body or "authoritative repo" in body or "Prefer `.canon/memory-layer.local.env`" in body
    assert "`canon doctor`" in body or "canon doctor" in body
