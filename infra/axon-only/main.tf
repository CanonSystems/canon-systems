# Standalone apply: Axon S3 + DynamoDB only (no VPC/RDS/ECS).
# Usage: cd infra/axon-only && terraform init && terraform apply

module "axon_snapshots" {
  source      = "../terraform/modules/axon-snapshots"
  name_prefix = "canon-systems-v2-dev"
}

output "snapshots_bucket_name" {
  value = module.axon_snapshots.snapshots_bucket_name
}

output "meta_table_name" {
  value = module.axon_snapshots.meta_table_name
}
