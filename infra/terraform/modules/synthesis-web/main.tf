# NOT wired into infra/terraform/main.tf (Precedent §1 cloud_execution_deferred waiver).

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0, < 6.0"
    }
  }
}

resource "aws_iam_role" "synthesis_web_lambda" {
  name = "${var.name_prefix}-synthesis-web-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "synthesis_web_s3_read" {
  name = "${var.name_prefix}-synthesis-web-s3-read"
  role = aws_iam_role.synthesis_web_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListVaultPrefix"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = var.vault_bucket_arn
        Condition = {
          StringLike = {
            "s3:prefix" = [
              "${var.vault_prefix}/${var.company_shorthash}/${var.repo_shorthash}/*",
              "${var.vault_prefix}/*",
            ]
          }
        }
      },
      {
        Sid      = "GetObjects"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${var.vault_bucket_arn}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "synthesis_web_basic" {
  role       = aws_iam_role.synthesis_web_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "synthesis_web" {
  function_name = "${var.name_prefix}-synthesis-web"
  role          = aws_iam_role.synthesis_web_lambda.arn
  handler       = "synthesis_web.main.handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 512

  filename         = var.lambda_package_path
  source_code_hash = var.lambda_package_hash

  environment {
    variables = {
      SYNTHESIS_WEB_BUCKET = var.vault_bucket_name
      SYNTHESIS_WEB_PREFIX = var.vault_prefix
    }
  }
}

resource "aws_apigatewayv2_api" "synthesis_web" {
  name          = "${var.name_prefix}-synthesis-web"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "synthesis_web" {
  api_id                 = aws_apigatewayv2_api.synthesis_web.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.synthesis_web.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "synthesis_web_proxy" {
  api_id    = aws_apigatewayv2_api.synthesis_web.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.synthesis_web.id}"
}

resource "aws_apigatewayv2_stage" "synthesis_web" {
  api_id      = aws_apigatewayv2_api.synthesis_web.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "synthesis_web_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.synthesis_web.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.synthesis_web.execution_arn}/*/*"
}

resource "aws_cloudfront_distribution" "synthesis_web" {
  enabled = true
  comment = "${var.name_prefix} synthesis-web (deferred stub)"

  origin {
    domain_name = replace(replace(aws_apigatewayv2_api.synthesis_web.api_endpoint, "https://", ""), "/", "")
    origin_id   = "apigw"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "apigw"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "If-None-Match"]

      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}
