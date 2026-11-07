# @note only matches objects under the uploads/ prefix so that
# worker output (resized/, archive/) doesn't re-trigger the pipeline

resource "aws_cloudwatch_event_rule" "s3_object_created" {
  name        = "itcc-image-upload"
  description = "fires when an object is created under uploads/ in the images bucket"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = {
        name = [aws_s3_bucket.images.id]
      }
      object = {
        key = [{ prefix = "uploads/" }]
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "sns" {
  rule      = aws_cloudwatch_event_rule.s3_object_created.name
  target_id = "image-events-topic"
  arn       = aws_sns_topic.image_events.arn
}
