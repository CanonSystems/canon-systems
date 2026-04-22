resource "aws_secretsmanager_secret" "placeholder" {
  for_each = toset(var.secret_names)

  name                    = "${var.name_prefix}/${each.key}"
  recovery_window_in_days = 0

  tags = {
    Purpose = "placeholder"
  }
}
