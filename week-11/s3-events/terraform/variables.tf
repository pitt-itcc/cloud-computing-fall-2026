variable "region" {
  type    = string
  default = "us-east-1"
}

variable "name" {
  description = "Prefix for every resource"
  type        = string
  default     = "eda-demo"
}

variable "image_uri" {
  description = "ECR image URI for the worker Lambda (account.dkr.ecr.region.amazonaws.com/repo:tag)"
  type        = string
}

variable "function_timeout" {
  description = "Lambda timeout in seconds. Queue visibility timeout is set to 6x this."
  type        = number
  default     = 5
}

variable "max_receive_count" {
  description = "Failed receives before SQS moves a message to the DLQ"
  type        = number
  default     = 3
}

variable "large_upload_bytes" {
  description = "EventBridge rule matches uploads bigger than this"
  type        = number
  default     = 1000000
}
