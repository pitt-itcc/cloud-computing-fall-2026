locals {
  queues = toset(["resize", "metadata", "archive"])
}

resource "aws_sqs_queue" "workers" {
  for_each                   = local.queues
  name                       = "itcc-image-${each.key}"
  message_retention_seconds  = 3600
  visibility_timeout_seconds = 30
}

resource "aws_sqs_queue_policy" "allow_sns" {
  for_each  = aws_sqs_queue.workers
  queue_url = each.value.url

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowSNSMessages"
        Effect    = "Allow"
        Principal = { Service = "sns.amazonaws.com" }
        Action    = "sqs:SendMessage"
        Resource  = each.value.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_sns_topic.image_events.arn
          }
        }
      }
    ]
  })
}
