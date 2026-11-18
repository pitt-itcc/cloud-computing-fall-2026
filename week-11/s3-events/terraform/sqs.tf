resource "aws_sqs_queue" "dlq" {
  for_each                  = local.workers
  name                      = "${local.prefix}-${each.key}-dlq"
  message_retention_seconds = 1209600 # 14 days: time to investigate
}

resource "aws_sqs_queue" "work" {
  for_each                   = local.workers
  name                       = "${local.prefix}-${each.key}-queue"
  visibility_timeout_seconds = var.function_timeout * 6 # AWS guidance for Lambda consumers
  receive_wait_time_seconds  = 20                       # long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq[each.key].arn
    maxReceiveCount     = var.max_receive_count
  })
}

# The DLQ only accepts messages from its own source queue.
resource "aws_sqs_queue_redrive_allow_policy" "dlq" {
  for_each  = local.workers
  queue_url = aws_sqs_queue.dlq[each.key].id
  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.work[each.key].arn]
  })
}

# Let the topic, and only this topic, send to each work queue.
resource "aws_sqs_queue_policy" "allow_sns" {
  for_each  = local.workers
  queue_url = aws_sqs_queue.work[each.key].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowSNSSend"
      Effect    = "Allow"
      Principal = { Service = "sns.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.work[each.key].arn
      Condition = { ArnEquals = { "aws:SourceArn" = aws_sns_topic.uploads.arn } }
    }]
  })
}
