output "bucket" {
  value = aws_s3_bucket.demo.id
}

output "role_arn" {
  value = aws_iam_role.reader.arn
}

output "try_it" {
  value = <<-EOT
    ./whoami.sh  # prints your admin identity, then the assumed role identity
  EOT
}
