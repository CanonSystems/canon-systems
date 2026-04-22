variable "name_prefix" {
  type        = string
  description = "Resource name prefix. The root module passes project_name and environment joined by a hyphen (see root main.tf module state_table) so the table name is <prefix>-canon-state per environment."
}
