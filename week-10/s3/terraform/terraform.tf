terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  backend "s3" {
    bucket = "itcc-tfstate-dpm79"
    key    = "week-10-s3/terraform.tfstate"
    region = "us-east-1"
  }
}
