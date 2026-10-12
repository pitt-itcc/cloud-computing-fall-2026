terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # @note: remote state config
  backend "s3" {
    bucket = "itcc-tfstate-dpm79"
    key    = "week-08/iam/terraform.tfstate"
    region = "us-east-1"
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

data "aws_caller_identity" "me" {}

locals {
  account_id = data.aws_caller_identity.me.account_id
}

# ---- The resource: a bucket with one public-ish file and one secret file -----------------

resource "aws_s3_bucket" "demo" {
  bucket_prefix = "cs1660-w8-"
  force_destroy = true # let terraform destroy empty it first
}

resource "aws_s3_object" "hello" {
  bucket  = aws_s3_bucket.demo.id
  key     = "public/hello.txt"
  content = "hello from cs1660\n"
}

resource "aws_s3_object" "grades" {
  bucket  = aws_s3_bucket.demo.id
  key     = "secret/grades.csv"
  content = "student,grade\nalice,A\nbob,B+\n"
}

# ---- The principal: a role you can assume from your own account ----------------------------

# TRUST policy: WHO may assume this role. "arn:aws:iam::<account>:root" means
# "this account", not the root user: any identity in the account whose own
# policies allow sts:AssumeRole on this role. Your admin identity qualifies.
resource "aws_iam_role" "reader" {
  name = "cs1660-w8-reader"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = "arn:aws:iam::${local.account_id}:root" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# PERMISSION policy: WHAT the role may do.
resource "aws_iam_role_policy" "reader" {
  name = "read-bucket"
  role = aws_iam_role.reader.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          # ListBucket is an action on the BUCKET, so the resource has no /*
          Sid      = "ListTheBucket"
          Effect   = "Allow"
          Action   = "s3:ListBucket"
          Resource = aws_s3_bucket.demo.arn
        },
        {
          # GetObject is an action on OBJECTS, so the resource needs /*
          Sid      = "ReadEveryObject"
          Effect   = "Allow"
          Action   = "s3:GetObject"
          Resource = "${aws_s3_bucket.demo.arn}/*"
        },
        {
          # Explicit deny beats the allow above, no matter what else says Allow.
          Sid      = "ButNeverTheGrades"
          Effect   = "Deny"
          Action   = "s3:GetObject"
          Resource = "${aws_s3_bucket.demo.arn}/secret/*"
        },
      ],
      # The fix students watch you apply: flip allow_uploads=true.
      var.allow_uploads ? [{
        Sid      = "UploadsOnly"
        Effect   = "Allow"
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.demo.arn}/uploads/*"
      }] : []
    )
  })
}
