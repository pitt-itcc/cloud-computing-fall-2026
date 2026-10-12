terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      course = "cs1660"
      week   = "08"
    }
  }
}

locals {
  oidc_host = "token.actions.githubusercontent.com"

  # GitHub's sub claim for this repo and branch. Repos created after July 15, 2026
  # (including GitHub Classroom repos this term) use the immutable form, which pins
  # the owner and repo IDs so a deleted-and-recreated repo with the same name cannot
  # assume this role. ./repo-ids.sh prints the IDs.
  subject = var.use_immutable_subject ? "repo:${var.github_owner}@${var.github_owner_id}/${var.github_repo}@${var.github_repo_id}:ref:refs/heads/${var.branch}" : "repo:${var.github_owner}/${var.github_repo}:ref:refs/heads/${var.branch}"

  provider_arn = var.create_oidc_provider ? aws_iam_openid_connect_provider.github[0].arn : data.aws_iam_openid_connect_provider.github[0].arn
}

# One per account per issuer URL. If your account already has it, set create_oidc_provider = false.
# No thumbprint: AWS validates GitHub's certificate against its own trusted CA library.
resource "aws_iam_openid_connect_provider" "github" {
  count          = var.create_oidc_provider ? 1 : 0
  url            = "https://${local.oidc_host}"
  client_id_list = ["sts.amazonaws.com"]
}

data "aws_iam_openid_connect_provider" "github" {
  count = var.create_oidc_provider ? 0 : 1
  url   = "https://${local.oidc_host}"
}

# TRUST policy: only a GitHub Actions job from THIS repo, on THIS branch, may assume the role.
resource "aws_iam_role" "github" {
  name = "cs1660-w8-github"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = local.provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_host}:aud" = "sts.amazonaws.com"
          "${local.oidc_host}:sub" = local.subject
        }
      }
    }]
  })
  max_session_duration = 3600
}

# PERMISSION policy: deliberately small. Swap in ECR push permissions for assignment 2.
resource "aws_iam_role_policy" "github" {
  name = "list-buckets-only"
  role = aws_iam_role.github.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "s3:ListAllMyBuckets"
      Resource = "*"
    }]
  })
}
