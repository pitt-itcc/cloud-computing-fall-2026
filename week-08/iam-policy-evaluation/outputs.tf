output "bucket" {
  value = aws_s3_bucket.demo.id
}

output "role_arn" {
  value = aws_iam_role.reader.arn
}

output "try_it" {
  value = <<-EOT
    ./reader.sh whoami                       # you, then the role
    ./reader.sh get public/hello.txt         # allowed by ReadEveryObject
    ./reader.sh get secret/grades.csv        # explicit deny: ButNeverTheGrades
    ./reader.sh put uploads/hw.txt           # implicit deny: nothing allows PutObject
    ./reader.sh simulate                     # same answers, no request sent
    terraform apply -var allow_uploads=true  # then put again
  EOT
}
