terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
  backend "s3" {
    bucket         = "research-agent-tfstate-manish-0903"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "research-agent-tf-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}
data "aws_availability_zones" "available" {}

locals {
  azs           = slice(data.aws_availability_zones.available.names, 0, 2)
  https_enabled = var.acm_certificate_arn != ""
}
