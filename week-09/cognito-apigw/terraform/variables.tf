variable "region" {
  type    = string
  default = "us-east-1"
}

variable "name" {
  type    = string
  default = "cognito-demo"
}

# @note: callback for local client. This would be your frontend app in real life
variable "callback_url" {
  type    = string
  default = "http://localhost:8080/callback"
}

variable "image_tag" {
  type    = string
  default = "a716e7b"
}

variable "architecture" {
  type    = string
  default = "x86_64"
}
