variable "name_prefix" {
  type        = string
  description = "Resource name prefix (e.g. project-env)."
}

variable "publisher_role_arn" {
  type        = string
  description = "IAM role allowed to read/write the synthesis vault bucket."
}

variable "vault_web_reader_role_arn" {
  type        = string
  default     = null
  description = "Optional read-only role for vault-web (E5-T4). Null omits the reader policy statement."
}
