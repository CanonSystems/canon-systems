variable "name_prefix" {
  type = string
}

variable "vpc_cidr" {
  type = string
}

variable "availability_zones" {
  type        = list(string)
  description = "Exactly two AZs for public/private subnet pairs."
}

variable "single_nat_gateway" {
  type = bool
}
