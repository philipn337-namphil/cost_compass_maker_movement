# =====================================================================
#  B안 · 가용성 구성
#  Application Load Balancer + Auto Scaling Group (EC2 2대).
#  데이터베이스는 여전히 각 인스턴스 내부에 설치된 것으로 가정한다.
#  서버 한 대가 죽어도 서비스가 유지된다.
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
#  변수 — A안과 동일한 값을 사용한다
# ---------------------------------------------------------------------
variable "region" {
  description = "비교에 사용할 리전"
  type        = string
  default     = "ap-northeast-2"
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
  description = "상시 유지할 인스턴스 대수"
  type        = number
  default     = 2
}

# 실제 VPC를 조회하지 않도록 ID를 변수로 둔다 (자격 증명 불필요)
variable "vpc_id" {
  type    = string
  default = "vpc-00000000000000000"
}

variable "subnet_ids" {
  description = "서로 다른 가용 영역의 서브넷 2개"
  type        = list(string)
  default     = ["subnet-00000000000000001", "subnet-00000000000000002"]
}

# ---------------------------------------------------------------------
#  로드 밸런서
# ---------------------------------------------------------------------
resource "aws_lb" "app" {
  name               = "design-b-alb"
  load_balancer_type = "application"
  internal           = false
  subnets            = var.subnet_ids

  tags = {
    Name   = "design-b-alb"
    Design = "B"
  }
}

resource "aws_lb_target_group" "app" {
  name     = "design-b-tg"
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
  name_prefix   = "design-b-"
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
  name                = "design-b-asg"
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
