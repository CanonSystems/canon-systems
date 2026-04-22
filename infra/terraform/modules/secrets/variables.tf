variable "name_prefix" {
  type = string
}

variable "secret_names" {
  type        = list(string)
  description = "Logical suffixes; full name becomes name_prefix/secret_name."
}
