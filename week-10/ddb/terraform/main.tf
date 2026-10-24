provider "aws" {
  region = var.region

  default_tags {
    tags = {
      course = "cs1660"
      demo   = "week-10-dynamodb"
    }
  }
}

# access patterns are on the slides, this table covers all four
resource "aws_dynamodb_table" "orders" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "customerId"
  range_key = "orderId" # @note: "<ISO date>#<id>" so it sorts chronologically

  # only key attributes go here, everything else is schemaless
  attribute {
    name = "customerId"
    type = "S"
  }

  attribute {
    name = "orderId"
    type = "S"
  }

  attribute {
    name = "productId"
    type = "S"
  }

  # who cares this is a demo
  deletion_protection_enabled = false
}

resource "aws_dynamodb_table_global_secondary_index" "by_product" {
  table_name = aws_dynamodb_table.orders.name

  name            = "by-product"
  hash_key        = "productId"
  range_key       = "orderId"
  projection_type = "ALL"
}
