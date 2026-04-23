output "bucket_name" {
  value       = aws_s3_bucket.synthesis_vault.id
  description = "Synthesis Obsidian-vault S3 bucket name"
}

output "bucket_arn" {
  value       = aws_s3_bucket.synthesis_vault.arn
  description = "S3 bucket ARN"
}

output "bucket_regional_domain_name" {
  value       = aws_s3_bucket.synthesis_vault.bucket_regional_domain_name
  description = "Regional S3 website-style domain (not public for this use case; useful for CORS/CloudFront in later epics)"
}
