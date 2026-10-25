output "bucket_name" {
  value = aws_s3_bucket.demo.id
}

output "bucket_arn" {
  value = aws_s3_bucket.demo.arn
}
