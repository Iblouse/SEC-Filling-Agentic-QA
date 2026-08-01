data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "api" {
  cidr_block           = var.api_vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-api"
  }
}

resource "aws_internet_gateway" "api" {
  vpc_id = aws_vpc.api.id

  tags = {
    Name = "${var.project_name}-api"
  }
}

resource "aws_subnet" "api_public" {
  count = 2

  vpc_id                  = aws_vpc.api.id
  cidr_block              = cidrsubnet(var.api_vpc_cidr, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-api-public-${count.index + 1}"
  }
}

resource "aws_route_table" "api_public" {
  vpc_id = aws_vpc.api.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.api.id
  }

  tags = {
    Name = "${var.project_name}-api-public"
  }
}

resource "aws_route_table_association" "api_public" {
  count = length(aws_subnet.api_public)

  subnet_id      = aws_subnet.api_public[count.index].id
  route_table_id = aws_route_table.api_public.id
}

resource "aws_security_group" "api_alb" {
  name        = "${var.project_name}-api-alb"
  description = "Internet traffic to the SEC QA load balancer."
  vpc_id      = aws_vpc.api.id

  ingress {
    description = "Public HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.api_ingress_cidrs
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-api-alb"
  }
}

resource "aws_security_group" "api_task" {
  name        = "${var.project_name}-api-task"
  description = "Only the ALB can reach the FastAPI container."
  vpc_id      = aws_vpc.api.id

  ingress {
    description     = "FastAPI from ALB"
    from_port       = var.api_container_port
    to_port         = var.api_container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.api_alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-api-task"
  }
}
