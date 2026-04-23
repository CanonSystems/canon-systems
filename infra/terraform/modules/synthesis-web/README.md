<!-- NOT wired into infra/terraform/main.tf (Precedent §1 cloud_execution_deferred waiver). -->

# synthesis-web (Terraform stub)

Operator-applied module sketch: **Lambda** (Python 3.11, Mangum handler `synthesis_web.main.handler`) + **API Gateway HTTP API** (`ANY /{proxy+}`) + **CloudFront** (default cert, HTTPS to viewer). **Not** referenced from the repo root `infra/terraform/main.tf` until cloud execution is approved.

## Variables

| Name | Default | Notes |
|------|---------|--------|
| `name_prefix` | `""` | Resource name prefix |
| `vault_bucket_arn` | `""` | Read policy scope |
| `vault_bucket_name` | `""` | `SYNTHESIS_WEB_BUCKET` |
| `vault_prefix` | `vault` | `SYNTHESIS_WEB_PREFIX` |
| `company_shorthash` | `""` | Optional ListBucket condition |
| `repo_shorthash` | `""` | Optional ListBucket condition |
| `domain` | `""` | Reserved for future custom domain |
| `lambda_package_path` | `""` | Zip path for `aws_lambda_function` |
| `lambda_package_hash` | `""` | `source_code_hash` |

## Outputs

- `service_url` — `https://` + CloudFront domain name
- `api_endpoint` — API Gateway URL
- `lambda_role_arn` — Lambda execution role

## Deferred apply

```bash
cd infra/terraform/modules/synthesis-web
terraform init
# Provide a workspace/root that wires variables; do not merge unwired root references until policy allows.
terraform plan -var="name_prefix=example" -var="vault_bucket_arn=arn:aws:s3:::..." 
```

IAM is **read-only** on the vault bucket (`s3:GetObject`, `s3:ListBucket` with prefix conditions). Adjust `ListBucket` conditions when `company_shorthash` / `repo_shorthash` are empty.
