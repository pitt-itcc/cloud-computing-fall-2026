# @note: cognito user pool, its login domain, and app client. This is our "Identity Provier"

resource "aws_cognito_user_pool" "this" {
  name = var.name

  # users sign in with their email address, and Cognito emails them a confirmation code when they sign up.
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length                   = 8
    require_lowercase                = true
    require_numbers                  = true
    require_uppercase                = false
    require_symbols                  = false
    temporary_password_validity_days = 7
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # So terraform destroy works without a manual step.
  deletion_protection = "INACTIVE"
}

# login pages live at https://<prefix>.auth.<region>.amazoncognito.com
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "aws_cognito_user_pool_domain" "this" {
  domain       = "cs1660-w9-${random_string.suffix.result}"
  user_pool_id = aws_cognito_user_pool.this.id

  # 1 = classic Hosted UI (works with no extra setup).
  # 2 = newer "managed login", which also needs a branding resource.
  managed_login_version = 1
}

# @note: on the whiteboard this is a PUBLIC client
resource "aws_cognito_user_pool_client" "web" {
  name         = "${var.name}-web"
  user_pool_id = aws_cognito_user_pool.this.id

  generate_secret = false

  # Authorization code flow only. No implicit flow.
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = [var.callback_url]

  # USER_PASSWORD_AUTH is only here for the CLI fallback in the README.
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_PASSWORD_AUTH",
  ]

  prevent_user_existence_errors = "ENABLED"
}
