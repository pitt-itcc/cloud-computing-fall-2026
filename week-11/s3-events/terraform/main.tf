# Week 11 EDA demo
#
#   S3 (uploads/) --> SNS topic --> thumbs-queue --> thumbnail Lambda --> S3 (thumbs/)
#                               \-> meta-queue   --> metadata Lambda  --> logs
#   each queue has its own DLQ (maxReceiveCount = 3)
#
#   S3 --> EventBridge (default bus) --> rule: uploads/ AND size > 1 MB --> log group

data "aws_caller_identity" "current" {}

resource "random_id" "suffix" {
  byte_length = 3
}

locals {
  prefix  = "${var.name}-${random_id.suffix.hex}"
  workers = toset(["thumbs", "meta"])
  handlers = {
    thumbs = "workers.thumbnail_handler"
    meta   = "workers.metadata_handler"
  }
}

resource "aws_s3_bucket" "uploads" {
  bucket        = "${local.prefix}-uploads"
  force_destroy = true # demo bucket: let terraform destroy empty it
}
