output "bucket" {
  value = aws_s3_bucket.uploads.id
}

output "topic_arn" {
  value = aws_sns_topic.uploads.arn
}

output "queue_urls" {
  value = { for k, q in aws_sqs_queue.work : k => q.id }
}

output "dlq_urls" {
  value = { for k, q in aws_sqs_queue.dlq : k => q.id }
}

output "dlq_arns" {
  value = { for k, q in aws_sqs_queue.dlq : k => q.arn }
}

output "log_groups" {
  value = merge(
    { for k, g in aws_cloudwatch_log_group.worker : k => g.name },
    { large_uploads = aws_cloudwatch_log_group.large_uploads.name },
  )
}
