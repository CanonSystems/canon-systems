terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_lb" "memory_api" {
  name               = "canon-memory-api"
  internal           = false
  load_balancer_type = "application"
  subnets            = var.public_subnet_ids
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.memory_api.arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = var.acm_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = var.target_group_arn
  }
}

resource "aws_route53_record" "memory_api_alias" {
  zone_id = var.hosted_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_lb.memory_api.dns_name
    zone_id                = aws_lb.memory_api.zone_id
    evaluate_target_health = true
  }
}

output "ingress_domain" {
  value = var.domain_name
}

output "auth_phase" {
  value = var.auth_phase
}
