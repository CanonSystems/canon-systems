# Axon-only Terraform (S3 + DynamoDB)

Applies **only** `modules/axon-snapshots` for `canon-systems-v2-dev` graph storage. Does not touch VPC, RDS, or ECS.

```bash
cd infra/axon-only
terraform init
terraform apply
```

State and `.terraform/` are gitignored. Run from a machine with AWS credentials; configure a remote backend for team use if needed.

The **axon HTTP service** is deployed separately (e.g. AWS App Runner + ECR image from `docker/axon-service/Dockerfile`).
