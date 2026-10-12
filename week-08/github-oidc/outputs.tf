output "role_arn" {
  description = "Put this in the repo as the Actions variable AWS_ROLE_ARN"
  value       = aws_iam_role.github.arn
}

output "trusted_subject" {
  description = "The only sub claim this role accepts"
  value       = local.subject
}
