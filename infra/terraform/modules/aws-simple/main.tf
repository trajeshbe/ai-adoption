# ============================================================================
# AWS Simple Deployment -- Single EC2 Instance with Docker Compose
#
# Deploys the full AI Agent Platform on a single EC2 instance running
# docker-compose. Suitable for demos, development, and small-scale usage.
#
# Usage:
#   terraform init
#   terraform apply -var="ssh_public_key=$(cat ~/.ssh/id_rsa.pub)" \
#                   -var="repo_url=https://github.com/your-org/ai-adoption.git" \
#                   -var="domain=app.example.com"
# ============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = "agent-platform"
      ManagedBy = "terraform"
    }
  }
}

locals {
  name_prefix = "agent-platform"
}

# ----------------------------------------------------------------------------
# Networking -- VPC, Subnet, Internet Gateway, Route Table
# ----------------------------------------------------------------------------

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${local.name_prefix}-vpc"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${local.name_prefix}-igw"
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, 1)
  availability_zone       = "${var.region}a"
  map_public_ip_on_launch = true

  tags = {
    Name = "${local.name_prefix}-public-subnet"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${local.name_prefix}-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# ----------------------------------------------------------------------------
# Security Group -- Allow HTTP, HTTPS, SSH inbound; all outbound
# ----------------------------------------------------------------------------

resource "aws_security_group" "instance" {
  name        = "${local.name_prefix}-sg"
  description = "Allow HTTP, HTTPS, and SSH inbound traffic"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-sg"
  }
}

# ----------------------------------------------------------------------------
# SSH Key Pair
# ----------------------------------------------------------------------------

resource "aws_key_pair" "deployer" {
  key_name   = "${local.name_prefix}-key"
  public_key = var.ssh_public_key

  tags = {
    Name = "${local.name_prefix}-key"
  }
}

# ----------------------------------------------------------------------------
# AMI Data Source -- Ubuntu 24.04 LTS (latest)
# ----------------------------------------------------------------------------

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# ----------------------------------------------------------------------------
# EC2 Instance -- Runs Docker Compose with all platform services
# ----------------------------------------------------------------------------

resource "aws_instance" "platform" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.deployer.key_name
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.instance.id]

  root_block_device {
    volume_size           = var.disk_size
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  user_data = base64encode(templatefile("${path.module}/user_data.tftpl", {
    repo_url = var.repo_url
    domain   = var.domain
  }))

  tags = {
    Name = "${local.name_prefix}-instance"
  }

  lifecycle {
    ignore_changes = [ami]
  }
}

# ----------------------------------------------------------------------------
# Elastic IP -- Stable public address for DNS
# ----------------------------------------------------------------------------

resource "aws_eip" "platform" {
  domain = "vpc"

  tags = {
    Name = "${local.name_prefix}-eip"
  }
}

resource "aws_eip_association" "platform" {
  instance_id   = aws_instance.platform.id
  allocation_id = aws_eip.platform.id
}
