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
