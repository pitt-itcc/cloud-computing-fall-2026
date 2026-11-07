resource "aws_sns_topic" "image_events" {
  name = "itcc-image-events"
}

resource "aws_sns_topic_policy" "allow_eventbridge" {
  arn = aws_sns_topic.image_events.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowEventBridgePublish"
        Effect    = "Allow"
        Principal = { Service = "events.amazonaws.com" }
        Action    = "sns:Publish"
        Resource  = aws_sns_topic.image_events.arn
      }
    ]
  })
}

# --- sns -> sqs subscriptions (the fan-out) ---

resource "aws_sns_topic_subscription" "sqs" {
  for_each  = aws_sqs_queue.workers
  topic_arn = aws_sns_topic.image_events.arn
  protocol  = "sqs"
  endpoint  = each.value.arn
}
