provider "aws" {
  region = var.region

  default_tags {
    tags = {
      course = "cs1660"
      demo   = "week-10-s3"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  bucket_name = "cs1660-s3-demo-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket" "demo" {
  bucket        = local.bucket_name
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "demo" {
  bucket = aws_s3_bucket.demo.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "demo" {
  bucket = aws_s3_bucket.demo.id

  rule {
    id     = "expire-after-7-days"
    status = "Enabled"

    expiration {
      days = 7
    }
  }
}
