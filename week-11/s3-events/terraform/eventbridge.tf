resource "aws_cloudwatch_event_rule" "large_uploads" {
  name        = "${local.prefix}-large-uploads"
  description = "uploads/ objects larger than ${var.large_upload_bytes} bytes"
  event_pattern = jsonencode({
    source        = ["aws.s3"]
    "detail-type" = ["Object Created"]
    detail = {
      bucket = { name = [aws_s3_bucket.uploads.id] }
      object = {
        key  = [{ prefix = "uploads/" }]
        size = [{ numeric = [">", var.large_upload_bytes] }]
      }
    }
  })
}

# EventBridge log targets must live under /aws/events/
resource "aws_cloudwatch_log_group" "large_uploads" {
  name              = "/aws/events/${local.prefix}-large-uploads"
  retention_in_days = 3
}

data "aws_iam_policy_document" "events_to_logs" {
  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.large_uploads.arn}:*"]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com", "delivery.logs.amazonaws.com"]
    }
  }
}

resource "aws_cloudwatch_log_resource_policy" "events_to_logs" {
  policy_name     = "${local.prefix}-events-to-logs"
  policy_document = data.aws_iam_policy_document.events_to_logs.json
}

resource "aws_cloudwatch_event_target" "large_uploads" {
  rule = aws_cloudwatch_event_rule.large_uploads.name
  arn  = aws_cloudwatch_log_group.large_uploads.arn

  depends_on = [aws_cloudwatch_log_resource_policy.events_to_logs]
}
