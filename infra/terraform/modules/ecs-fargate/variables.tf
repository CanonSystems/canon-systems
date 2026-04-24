variable "name_prefix" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "container_name" {
  type = string
}

variable "container_image" {
  type = string
}

variable "container_port" {
  type = number
}

variable "cpu" {
  type = number
}

variable "memory" {
  type = number
}

variable "desired_count" {
  type = number
}

variable "s3_bucket_arn" {
  type = string
}

variable "secret_arns" {
  type        = list(string)
  description = "Secrets Manager ARNs the task role may read (GetSecretValue)."
  default     = []
}

variable "ingress_enabled" {
  type        = bool
  description = "When true, register the baseline ECS service with ingress_target_group_arn."
  default     = false
}

variable "ingress_target_group_arn" {
  type        = string
  description = "Existing ALB/NLB target group ARN. Required when ingress_enabled is true."
  default     = ""
}

variable "ingress_source_security_group_ids" {
  type        = list(string)
  description = "Security groups allowed to reach container_port on the task ENIs (typically the load balancer SG). Ignored when empty."
  default     = []
}
