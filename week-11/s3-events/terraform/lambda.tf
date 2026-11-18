# ------------------------------------------------------------------ IAM

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "worker" {
  for_each           = local.workers
  name               = "${local.prefix}-${each.key}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "logs" {
  for_each   = local.workers
  role       = aws_iam_role.worker[each.key].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Least privilege per worker: its own queue, and only the S3 actions it needs.
data "aws_iam_policy_document" "worker" {
  for_each = local.workers

  statement {
    sid       = "ConsumeOwnQueue"
    actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
    resources = [aws_sqs_queue.work[each.key].arn]
  }

  statement {
    sid       = "ReadUploads"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.uploads.arn}/uploads/*"]
  }

  dynamic "statement" {
    for_each = each.key == "thumbs" ? [1] : []
    content {
      sid       = "WriteThumbs"
      actions   = ["s3:PutObject"]
      resources = ["${aws_s3_bucket.uploads.arn}/thumbs/*"]
    }
  }
}

resource "aws_iam_role_policy" "worker" {
  for_each = local.workers
  name     = "worker"
  role     = aws_iam_role.worker[each.key].id
  policy   = data.aws_iam_policy_document.worker[each.key].json
}

# ------------------------------------------------------------------ functions

resource "aws_cloudwatch_log_group" "worker" {
  for_each          = local.workers
  name              = "/aws/lambda/${local.prefix}-${each.key}"
  retention_in_days = 3
}

resource "aws_lambda_function" "worker" {
  for_each      = local.workers
  function_name = "${local.prefix}-${each.key}"
  role          = aws_iam_role.worker[each.key].arn
  package_type  = "Image"
  image_uri     = var.image_uri
  timeout       = var.function_timeout

  image_config {
    command = [local.handlers[each.key]]
  }

  depends_on = [
    aws_cloudwatch_log_group.worker,
    aws_iam_role_policy_attachment.logs,
  ]
}

resource "aws_lambda_event_source_mapping" "worker" {
  for_each                = local.workers
  event_source_arn        = aws_sqs_queue.work[each.key].arn
  function_name           = aws_lambda_function.worker[each.key].arn
  batch_size              = 10
  function_response_types = ["ReportBatchItemFailures"] # partial batch failures

  scaling_config {
    maximum_concurrency = 5 # competing consumers, capped
  }

  depends_on = [aws_iam_role_policy.worker]
}
