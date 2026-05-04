output "table_name" {
  description = "Name of the DynamoDB canon-state table."
  value       = aws_dynamodb_table.this.name
}

output "table_arn" {
  description = "ARN of the DynamoDB canon-state table."
  value       = aws_dynamodb_table.this.arn
}

output "run_ledger_table_name" {
  description = "DynamoDB run-ledger table name (readiness run records; no lease/TTL overlap with canon-state)."
  value       = aws_dynamodb_table.run_ledger.name
}

output "run_ledger_table_arn" {
  description = "ARN of the DynamoDB run-ledger table."
  value       = aws_dynamodb_table.run_ledger.arn
}
