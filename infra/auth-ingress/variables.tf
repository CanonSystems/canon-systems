variable "aws_region" {
  type        = string
  description = "AWS region for ingress and auth resources."
  default     = "us-east-1"
}

variable "domain_name" {
  type        = string
  description = "Canonical memory API domain."
  default     = "memory.canon-systems.com"
}

variable "hosted_zone_id" {
  type        = string
  description = "Route53 hosted zone id for canon-systems.com."
}

variable "vpc_id" {
  type        = string
  description = "VPC hosting ECS services."
}

variable "public_subnet_ids" {
  type        = list(string)
  description = "Public subnets for ALB."
}

variable "target_group_arn" {
  type        = string
  description = "Existing target group ARN for memory ECS service."
}

variable "acm_certificate_arn" {
  type        = string
  description = "ACM certificate ARN for TLS."
}

variable "auth_phase" {
  type        = string
  description = "Migration phase: prepare|canary|enforce|rollback."
  default     = "prepare"
}

variable "cognito_user_pool_name" {
  type        = string
  description = "Cognito User Pool name."
  default     = "canon-systems-users"
}

variable "cognito_domain_prefix" {
  type        = string
  description = "Hosted Cognito domain prefix."
  default     = "canon-systems-auth"
}
