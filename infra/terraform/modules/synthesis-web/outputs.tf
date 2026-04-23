# NOT wired into infra/terraform/main.tf (Precedent §1 cloud_execution_deferred waiver).

output "service_url" {
  description = "HTTPS URL on CloudFront (default certificate)."
  value       = "https://${aws_cloudfront_distribution.synthesis_web.domain_name}"
}

output "api_endpoint" {
  description = "HTTP API invoke URL (API Gateway v2)."
  value       = aws_apigatewayv2_api.synthesis_web.api_endpoint
}

output "lambda_role_arn" {
  description = "IAM role ARN for the Lambda function."
  value       = aws_iam_role.synthesis_web_lambda.arn
}
