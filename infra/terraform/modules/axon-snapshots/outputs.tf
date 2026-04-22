output "snapshots_bucket_name" {
  value = aws_s3_bucket.snapshots.id
}

output "snapshots_bucket_arn" {
  value = aws_s3_bucket.snapshots.arn
}

output "meta_table_name" {
  value = aws_dynamodb_table.meta.name
}

output "meta_table_arn" {
  value = aws_dynamodb_table.meta.arn
}
