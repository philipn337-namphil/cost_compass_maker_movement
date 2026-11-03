# =====================================================================
#  A안 · 최소 구성
#  EC2 1대에 애플리케이션과 데이터베이스를 함께 올린다.
#  가장 저렴하지만 단일 장애점(SPOF)이 존재한다.
#
#  ※ 이 템플릿은 Infracost 비용 추정 전용이며 실제로 apply 하지 않는다.
# =====================================================================

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# 비용 추정만 수행하므로 실제 자격 증명 없이 파싱되도록 설정한다.
provider "aws" {
  region                      = var.region
  access_key                  = "mock_access_key"
  secret_key                  = "mock_secret_key"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
}

# ---------------------------------------------------------------------
#  변수 — 세 설계안이 동일한 값을 사용해야 비교가 공정하다
# ---------------------------------------------------------------------
variable "region" {
  description = "비교에 사용할 리전"
  type        = string
  default     = "ap-northeast-2" # 서울
}

variable "ami_id" {
  description = "Amazon Linux 2023 AMI (리전마다 다르므로 실제 값으로 교체 가능)"
  type        = string
  default     = "ami-0c9c942bd7bf113a2"
}

variable "instance_type" {
  description = "애플리케이션 서버 인스턴스 타입"
  type        = string
  default     = "t3.small"
}

variable "root_volume_gb" {
  description = "루트 EBS 볼륨 크기(GB)"
  type        = number
  default     = 30
}

# ---------------------------------------------------------------------
#  애플리케이션 서버 (DB 포함)
# ---------------------------------------------------------------------
resource "aws_instance" "app" {
  ami           = var.ami_id
  instance_type = var.instance_type

  root_block_device {
    volume_type = "gp3"
    volume_size = var.root_volume_gb
  }

  tags = {
    Name   = "design-a-app"
    Design = "A"
  }
}

# 고정 공인 IP
resource "aws_eip" "app" {
  domain   = "vpc"
  instance = aws_instance.app.id

  tags = {
    Name   = "design-a-eip"
    Design = "A"
  }
}
