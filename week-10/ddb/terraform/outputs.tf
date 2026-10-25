output "table_name" {
  value = aws_dynamodb_table.orders.name
}

output "table_arn" {
  value = aws_dynamodb_table.orders.arn
}

output "gsi_arn" {
  value = "${aws_dynamodb_table.orders.arn}/index/by-product"
}
