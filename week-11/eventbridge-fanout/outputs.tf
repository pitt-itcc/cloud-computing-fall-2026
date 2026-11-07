output "bucket_name" {
  value = aws_s3_bucket.images.id
}

output "resize_queue_url" {
  value = aws_sqs_queue.workers["resize"].url
}

output "metadata_queue_url" {
  value = aws_sqs_queue.workers["metadata"].url
}

output "archive_queue_url" {
  value = aws_sqs_queue.workers["archive"].url
}
