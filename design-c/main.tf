# =====================================================================
#  C안 · 관리형 구성
#  B안(ALB + Auto Scaling)에 더해, 데이터베이스를 RDS로 분리한다.
#  운영 부담이 가장 적지만 관리형 서비스 비용이 추가된다.
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

provider "aws" {
  region                      = var.region
  access_key                  = "mock_access_key"
  secret_key                  = "mock_secret_key"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
}

# ---------------------------------------------------------------------
#  변수 — A안·B안과 동일한 값을 사용한다
# ---------------------------------------------------------------------
variable "region" {
  type    = string
  default = "ap-northeast-2"
}

variable "ami_id" {
  type    = string
  default = "ami-0c9c942bd7bf113a2"
}

variable "instance_type" {
  type    = string
  default = "t3.small"
}

variable "root_volume_gb" {
  type    = number
  default = 30
}

variable "desired_capacity" {
  type    = number
  default = 2
}

variable "vpc_id" {
  type    = string
  default = "vpc-00000000000000000"
}

variable "subnet_ids" {
  type    = list(string)
  default = ["subnet-00000000000000001", "subnet-00000000000000002"]
}

# --- RDS 관련 ---
variable "db_instance_class" {
  description = "RDS 인스턴스 클래스"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage_gb" {
  type    = number
  default = 20
}

# 표준 지원이 끝난 엔진 버전을 쓰면 AWS가 '확장 지원(Extended Support)' 요금을
# 따로 물린다. db.t3.micro 기준 월 175.20달러로, 인스턴스 요금의 9배다.
# 코드에서는 버전 문자열 한 줄로만 보이기 때문에 배포 전에는 알아채기 어렵다.
# 보고서 [표 5-5]가 이 차이를 다룬다.
#
# 측정값 (Infracost v0.10.47 기준)
#   8.0 / 8.4 / 8.4.3  → 확장 지원 부과, C안 총액 257.46
#   9.0                → 부과 없음,      C안 총액  82.26
variable "db_engine_version" {
  description = "MySQL 엔진 버전. 표준 지원이 끝난 버전은 확장 지원 요금이 붙는다."
  type        = string
  default     = "8.0"
}

variable "db_multi_az" {
  description = "true로 바꾸면 DB 이중화 비용을 비교해 볼 수 있다"
  type        = bool
  default     = false
}

variable "db_password" {
  description = "비용 추정에는 사용되지 않는다. 실제 배포 시에만 주입한다."
  type        = string
  sensitive   = true
  default     = ""
}

# ---------------------------------------------------------------------
#  로드 밸런서
# ---------------------------------------------------------------------
resource "aws_lb" "app" {
  name               = "design-c-alb"
  load_balancer_type = "application"
  internal           = false
  subnets            = var.subnet_ids

  tags = {
    Name   = "design-c-alb"
    Design = "C"
  }
}

resource "aws_lb_target_group" "app" {
  name     = "design-c-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.vpc_id
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# ---------------------------------------------------------------------
#  오토 스케일링
# ---------------------------------------------------------------------
resource "aws_launch_template" "app" {
  name_prefix   = "design-c-"
  image_id      = var.ami_id
  instance_type = var.instance_type

  block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      volume_type = "gp3"
      volume_size = var.root_volume_gb
    }
  }
}

resource "aws_autoscaling_group" "app" {
  name                = "design-c-asg"
  vpc_zone_identifier = var.subnet_ids
  target_group_arns   = [aws_lb_target_group.app.arn]

  min_size         = 2
  max_size         = 4
  desired_capacity = var.desired_capacity

  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }
}

# ---------------------------------------------------------------------
#  관리형 데이터베이스 — C안에만 존재한다
# ---------------------------------------------------------------------
resource "aws_db_instance" "app" {
  identifier        = "design-c-db"
  engine            = "mysql"
  engine_version    = var.db_engine_version
  instance_class    = var.db_instance_class
  allocated_storage = var.db_allocated_storage_gb
  storage_type      = "gp3"
  multi_az          = var.db_multi_az

  username            = "admin"
  password            = var.db_password
  skip_final_snapshot = true

  tags = {
    Name   = "design-c-db"
    Design = "C"
  }
}
