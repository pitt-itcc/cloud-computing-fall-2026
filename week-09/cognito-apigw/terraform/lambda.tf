# lambda backend setup

data "aws_caller_identity" "current" {}

resource "aws_ecr_repository" "fn" {
  name                 = var.name
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true # lets terraform destroy remove pushed images
}

# @note: permission for api gateway to pull our image
resource "aws_ecr_repository_policy" "lambda_pull" {
  repository = aws_ecr_repository.fn.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "LambdaPull"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
      Condition = {
        StringLike = {
          "aws:sourceArn" = "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:*"
        }
      }
    }]
  })
}

locals {
  image_uri = "${aws_ecr_repository.fn.repository_url}:${var.image_tag}"
}

resource "aws_iam_role" "fn" {
  name = "${var.name}-fn"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "logs" {
  role       = aws_iam_role.fn.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "fn" {
  name              = "/aws/lambda/${var.name}"
  retention_in_days = 7
}

resource "aws_lambda_function" "fn" {
  function_name = var.name
  role          = aws_iam_role.fn.arn
  package_type  = "Image"
  image_uri     = local.image_uri
  architectures = [var.architecture]
  timeout       = 5
  # No handler or runtime here: the image's CMD (app.handler.handler) and base
  # image (python:3.14) decide those.

  depends_on = [
    aws_ecr_repository_policy.lambda_pull,
    aws_cloudwatch_log_group.fn,
    aws_iam_role_policy_attachment.logs,
  ]
}
