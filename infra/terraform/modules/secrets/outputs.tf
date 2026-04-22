output "secret_arns" {
  value = { for k, s in aws_secretsmanager_secret.placeholder : k => s.arn }
}
