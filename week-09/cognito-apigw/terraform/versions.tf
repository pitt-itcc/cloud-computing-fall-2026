terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # @note: remote state config
  backend "s3" {
    bucket = "itcc-tfstate-dpm79"
    key    = "week-07/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.region
}
