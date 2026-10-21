locals {
  cognito_domain = "https://${aws_cognito_user_pool_domain.this.domain}.auth.${var.region}.amazoncognito.com"
  issuer         = "https://cognito-idp.${var.region}.amazonaws.com/${aws_cognito_user_pool.this.id}"
}

output "api_url" {
  value = aws_api_gateway_stage.demo.invoke_url
}

output "user_pool_id" {
  value = aws_cognito_user_pool.this.id
}

output "client_id" {
  value = aws_cognito_user_pool_client.web.id
}

output "cognito_domain" {
  value = local.cognito_domain
}

output "callback_url" {
  value = var.callback_url
}

# Open this in a browser to create a user before the demo.
output "signup_url" {
  value = "${local.cognito_domain}/signup?client_id=${aws_cognito_user_pool_client.web.id}&response_type=code&scope=openid+email+profile&redirect_uri=${var.callback_url}"
}

# Paste these into a browser to show where verifiers find the public keys.
output "issuer" {
  value = local.issuer
}

output "discovery_url" {
  value = "${local.issuer}/.well-known/openid-configuration"
}

output "jwks_url" {
  value = "${local.issuer}/.well-known/jwks.json"
}
