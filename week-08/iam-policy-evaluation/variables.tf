variable "region" {
  type    = string
  default = "us-east-1"
}

variable "allow_uploads" {
  description = "Grant s3:PutObject on uploads/*"
  type        = bool
  default     = false
}
