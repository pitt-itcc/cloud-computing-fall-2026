resource "aws_sns_topic" "uploads" {
  name = "${local.prefix}-photo-uploaded"
}

# Let S3, and only this bucket in this account, publish to the topic.
resource "aws_sns_topic_policy" "allow_s3" {
  arn = aws_sns_topic.uploads.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowS3Publish"
      Effect    = "Allow"
      Principal = { Service = "s3.amazonaws.com" }
      Action    = "sns:Publish"
      Resource  = aws_sns_topic.uploads.arn
      Condition = {
        ArnLike      = { "aws:SourceArn" = aws_s3_bucket.uploads.arn }
        StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id }
      }
    }]
  })
}

resource "aws_s3_bucket_notification" "uploads" {
  bucket      = aws_s3_bucket.uploads.id
  eventbridge = true # also send every event to the default EventBridge bus

  topic {
    topic_arn     = aws_sns_topic.uploads.arn
    events        = ["s3:ObjectCreated:*"]
    filter_prefix = "uploads/" # thumbs/ writes must NOT re-trigger us
  }

  depends_on = [aws_sns_topic_policy.allow_s3]
}

resource "aws_sns_topic_subscription" "work" {
  for_each             = local.workers
  topic_arn            = aws_sns_topic.uploads.arn
  protocol             = "sqs"
  endpoint             = aws_sqs_queue.work[each.key].arn
  raw_message_delivery = true # SQS body = the S3 event, no SNS envelope

  depends_on = [aws_sqs_queue_policy.allow_sns]
}
