resource "aws_s3_bucket" "images" {
  bucket_prefix = "itcc-image-pipeline-"
  force_destroy = true
}

resource "aws_s3_bucket_notification" "images" {
  bucket      = aws_s3_bucket.images.id
  eventbridge = true
}
