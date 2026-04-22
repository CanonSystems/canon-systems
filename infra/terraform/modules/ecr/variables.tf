variable "name_prefix" {
  type = string
}

variable "repository_names" {
  type = list(string)
}

variable "image_tag_mutability" {
  type    = string
  default = "MUTABLE"
}
