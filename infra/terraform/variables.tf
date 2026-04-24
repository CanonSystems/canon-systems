variable "aws_region" {
  type        = string
  description = "AWS region for all resources."
}

variable "project_name" {
  type        = string
  description = "Short name used in resource names and tags."
}

variable "environment" {
  type        = string
  description = "Deployment environment label (e.g. dev, staging, prod)."
}

variable "vpc_cidr" {
  type        = string
  description = "IPv4 CIDR for the new VPC."
  default     = "10.0.0.0/16"
}

variable "single_nat_gateway" {
  type        = bool
  description = "Use one NAT gateway (cheaper) vs one per AZ (higher availability)."
  default     = true
}

variable "ecr_repository_names" {
  type        = list(string)
  description = "ECR repository names for core services (without registry host)."
}

variable "placeholder_secret_names" {
  type        = list(string)
  description = "Secrets Manager secret names to create as empty placeholders (no secret versions)."
  default     = []
}

variable "memory_layer_secret_suffixes" {
  type        = list(string)
  description = <<-EOT
    Suffix keys for memory-layer env secrets. Full name: "<project>-<environment>/<suffix>".
    Suffixes must match slug rules in scripts/dev/lib/memory_layer/aws_secrets.py
    (memory-layer__<company>__<repository-id-slug>).
  EOT
  default = [
    "memory-layer__fmo__github-com-familyoneinc-familyonewebsite",
    "memory-layer__fmo__github-com-canonsystems-canon-systems-v2",
  ]
}

variable "db_name" {
  type        = string
  description = "Initial PostgreSQL database name."
  default     = "app"
}

variable "db_username" {
  type        = string
  description = "RDS master username."
  default     = "appadmin"
}

variable "db_password" {
  type        = string
  description = "RDS master password. If null, a random password is generated (see sensitive output)."
  sensitive   = true
  default     = null
}

variable "db_instance_class" {
  type        = string
  description = "RDS instance class."
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  type        = number
  description = "Allocated storage in GB."
  default     = 20
}

variable "db_engine_version" {
  type        = string
  description = "PostgreSQL major.minor version."
  default     = "16.4"
}

variable "rds_skip_final_snapshot" {
  type        = bool
  description = "If true, no final snapshot on destroy (typical for dev)."
  default     = true
}

variable "ecs_container_image" {
  type        = string
  description = "Container image for the baseline Fargate task (swap for your ECR image)."
  default     = "public.ecr.aws/docker/library/nginx:alpine"
}

variable "ecs_container_port" {
  type        = number
  description = "Container port exposed by the baseline task (no ALB in this baseline)."
  default     = 80
}

variable "ecs_cpu" {
  type        = number
  description = "Fargate task CPU units."
  default     = 256
}

variable "ecs_memory" {
  type        = number
  description = "Fargate task memory (MiB)."
  default     = 512
}

variable "ecs_desired_count" {
  type        = number
  description = "Desired task count for the baseline service (0 avoids running tasks until images are ready)."
  default     = 0
}

variable "ecs_ingress_enabled" {
  type        = bool
  description = "When true, attach ecs_baseline to ecs_ingress_target_group_arn (operator-provisioned ALB/NLB)."
  default     = false
}

variable "ecs_ingress_target_group_arn" {
  type        = string
  description = "Target group ARN for stable ingress. Required when ecs_ingress_enabled is true. Import/apply is operator-owned."
  default     = ""
}

variable "ecs_ingress_source_security_group_ids" {
  type        = list(string)
  description = "Security groups allowed to reach ecs_container_port on task ENIs (e.g. load balancer SG)."
  default     = []
}

variable "memory_plane_stable_dns_hostname" {
  type        = string
  description = "Optional operator bookkeeping: stable public DNS hostname for HTTPS memory URLs (echoed in outputs only; ACM/Route53 not managed here)."
  default     = ""
}
