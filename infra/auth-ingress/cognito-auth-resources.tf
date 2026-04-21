resource "aws_cognito_user_pool" "canon_users" {
  name = var.cognito_user_pool_name
}

resource "aws_cognito_user_pool_client" "canon_cli" {
  name                                 = "canon-cli"
  user_pool_id                         = aws_cognito_user_pool.canon_users.id
  generate_secret                      = false
  explicit_auth_flows                  = ["ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
  prevent_user_existence_errors        = "ENABLED"
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = ["http://localhost:8787/callback"]
  logout_urls                          = ["http://localhost:8787/logout"]
}

resource "aws_cognito_user_pool_domain" "canon_cli" {
  domain       = var.cognito_domain_prefix
  user_pool_id = aws_cognito_user_pool.canon_users.id
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.canon_users.id
}

output "cognito_client_id" {
  value = aws_cognito_user_pool_client.canon_cli.id
}
