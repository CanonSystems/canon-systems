output "vpc_id" {
  description = "ID of the created VPC."
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs for workloads (ECS, RDS)."
  value       = module.vpc.private_subnet_ids
}

output "public_subnet_ids" {
  description = "Public subnet IDs (NAT, optional future load balancers)."
  value       = module.vpc.public_subnet_ids
}

output "ecr_repository_urls" {
  description = "Map of repository name to URL."
  value       = module.ecr.repository_urls
}

output "artifacts_bucket_name" {
  description = "S3 bucket for build artifacts and uploads."
  value       = module.artifacts_bucket.bucket_id
}

output "artifacts_bucket_arn" {
  description = "ARN of the artifacts bucket."
  value       = module.artifacts_bucket.bucket_arn
}

output "placeholder_secret_arns" {
  description = "ARNs of Secrets Manager placeholders (add secret versions in console or CLI)."
  value       = module.placeholders.secret_arns
}

output "ecs_cluster_name" {
  description = "ECS cluster name."
  value       = module.ecs_baseline.cluster_name
}

output "ecs_service_name" {
  description = "Baseline ECS service name."
  value       = module.ecs_baseline.service_name
}

output "ecs_task_execution_role_arn" {
  description = "IAM role ARN used by the ECS agent (pull image, logs, secrets injection)."
  value       = module.ecs_baseline.task_execution_role_arn
}

output "ecs_task_role_arn" {
  description = "IAM role ARN assumed by application code in the task."
  value       = module.ecs_baseline.task_role_arn
}

output "ecs_ingress_enabled" {
  description = "Whether the baseline ECS service registers with a load balancer target group."
  value       = module.ecs_baseline.ingress_enabled
}

output "ecs_ingress_target_group_arn" {
  description = "Target group ARN when ingress is enabled; null otherwise."
  value       = module.ecs_baseline.ingress_target_group_arn
}

output "memory_plane_stable_dns_hostname" {
  description = "Stable DNS hostname for memory-plane HTTPS URLs when set by the operator."
  value       = var.memory_plane_stable_dns_hostname != "" ? var.memory_plane_stable_dns_hostname : null
}

output "rds_endpoint" {
  description = "RDS hostname (no port)."
  value       = module.rds.address
}

output "rds_port" {
  description = "RDS port."
  value       = module.rds.port
}

output "rds_database_name" {
  description = "Created database name."
  value       = module.rds.db_name
}

output "db_master_password" {
  description = "Master password when Terraform generated it (null if you passed db_password)."
  value       = var.db_password == null ? random_password.db[0].result : null
  sensitive   = true
}

output "state_table_name" {
  description = "DynamoDB canon-state table name (operational checkpoints / lease state)."
  value       = module.state_table.table_name
}

output "state_table_arn" {
  description = "ARN of the DynamoDB canon-state table."
  value       = module.state_table.table_arn
}

output "state_run_ledger_table_name" {
  description = "DynamoDB run-ledger table (durable readiness/run records; separate from checkpoint items)."
  value       = module.state_table.run_ledger_table_name
}

output "state_run_ledger_table_arn" {
  description = "ARN of the DynamoDB run-ledger table."
  value       = module.state_table.run_ledger_table_arn
}

output "state_tasks_table_name" {
  description = "DynamoDB tasks table (assignable-task event plane for `canon task`)."
  value       = module.state_table.tasks_table_name
}

output "state_tasks_table_arn" {
  description = "ARN of the DynamoDB tasks table."
  value       = module.state_table.tasks_table_arn
}

output "snapshots_bucket_name" {
  description = "S3 bucket for Axon per-commit graph snapshots (gzip JSON)."
  value       = module.axon_snapshots.snapshots_bucket_name
}

output "snapshots_bucket_arn" {
  description = "ARN of the Axon snapshots bucket."
  value       = module.axon_snapshots.snapshots_bucket_arn
}

output "meta_table_name" {
  description = "DynamoDB table for Axon snapshot metadata (pk/sk per tenant + commit)."
  value       = module.axon_snapshots.meta_table_name
}

output "meta_table_arn" {
  description = "ARN of the Axon metadata table."
  value       = module.axon_snapshots.meta_table_arn
}
