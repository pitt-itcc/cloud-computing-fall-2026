terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # @note: remote state config
  backend "s3" {
    bucket = "itcc-tfstate-dpm79"
    key    = "week-10/terraform.tfstate"
    region = "us-east-1"
  }
}
