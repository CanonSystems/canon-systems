# synthesis-vault

Terraform module for the **Wave-5 synthesis vault** storage plane: one versioned, SSE-S3 encrypted, private S3 bucket for Obsidian-compatible markdown + JSON attachments. Object lock is **off**; versioning is **on**; public access is blocked on all four flags. A single **publisher** IAM role is allowlisted for Put/Get/Delete/List; an optional **reader** role (for future vault-web, E5-T4) may be attached. Per-tenant `s3:prefix` restrictions on the bucket policy are deferred to E5-T4 multi-tenant hardening.

## Purpose

Hosts `vault/<company_shorthash>/<repo_shorthash>/...` objects written by `backend/synthesis` (`SynthesisPublisher`). Not created by Terraform: the application layout and object keys.

## Cloud apply

`terraform apply` in the target account is **operator-run** and **out of band** for this repository’s automation (Precedent §1 — `cloud_execution_deferred`). No in-task cloud commands are performed here.

## Security posture

| Control | Setting |
| --- | --- |
| Versioning | Enabled |
| Object lock | Disabled |
| Encryption | SSE-S3 (AES256) |
| Public access block | All four `true` |
| Bucket policy | Single publisher role; optional reader role |

## Inputs

| Name | Type | Description |
| --- | --- | --- |
| `name_prefix` | string | Prefix for resource names; bucket is `${name_prefix}-synthesis-vault`. |
| `publisher_role_arn` | string | IAM role allowed to publish vault objects. |
| `vault_web_reader_role_arn` | string (nullable) | Optional read-only role for vault consumers. Default `null`. |

## Outputs

| Name | Description |
| --- | --- |
| `bucket_name` | S3 bucket name |
| `bucket_arn` | S3 bucket ARN |
| `bucket_regional_domain_name` | Regional domain name |

## Import (existing resources)

From `infra/terraform/` after configuring backend and credentials (replace with real resource id):

```bash
terraform import 'module.synthesis_vault.aws_s3_bucket.synthesis_vault' 'myproj-dev-synthesis-vault'
```
