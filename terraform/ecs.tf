# =============================================================================
# AWS ECS Fargate Infrastructure for Backend Deployment
# =============================================================================

# ECR Repository for Docker Images
resource "aws_ecr_repository" "backend" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "${var.ecr_repository_name}"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Project     = "bad-apples-mvp"
  }
}

# ECR Lifecycle Policy to manage old images
resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Delete untagged images older than 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# =============================================================================
# VPC and Network Configuration
# =============================================================================

# Get available availability zones
data "aws_availability_zones" "available" {
  state = "available"
}

# VPC
resource "aws_vpc" "main" {
  count = var.create_vpc ? 1 : 0

  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.ecs_cluster_name}-vpc"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  count = var.create_vpc ? 1 : 0

  vpc_id = aws_vpc.main[0].id

  tags = {
    Name        = "${var.ecs_cluster_name}-igw"
    Environment = var.environment
  }
}

# Public Subnets (for ALB and ECS tasks)
resource "aws_subnet" "public" {
  count = var.create_vpc ? 2 : 0

  vpc_id                  = aws_vpc.main[0].id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.ecs_cluster_name}-public-subnet-${count.index + 1}"
    Environment = var.environment
    Type        = "Public"
  }
}

# Route Table for Public Subnets
resource "aws_route_table" "public" {
  count = var.create_vpc ? 1 : 0

  vpc_id = aws_vpc.main[0].id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main[0].id
  }

  tags = {
    Name        = "${var.ecs_cluster_name}-public-rt"
    Environment = var.environment
  }
}

# Route Table Associations for Public Subnets
resource "aws_route_table_association" "public" {
  count = var.create_vpc ? 2 : 0

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public[0].id
}

# =============================================================================
# Security Groups
# =============================================================================

# Security Group for ALB
resource "aws_security_group" "alb" {
  count = var.create_vpc ? 1 : 0

  name        = "${var.ecs_cluster_name}-alb-sg"
  description = "Security group for Application Load Balancer"
  vpc_id      = aws_vpc.main[0].id

  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  dynamic "ingress" {
    for_each = var.enable_https ? [1] : []
    content {
      description = "HTTPS from anywhere"
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.ecs_cluster_name}-alb-sg"
    Environment = var.environment
  }
}

# Security Group for ECS Tasks
resource "aws_security_group" "ecs_tasks" {
  count = var.create_vpc ? 1 : 0

  name        = "${var.ecs_cluster_name}-ecs-tasks-sg"
  description = "Security group for ECS tasks"
  vpc_id      = aws_vpc.main[0].id

  ingress {
    description     = "Allow traffic from ALB"
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb[0].id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.ecs_cluster_name}-ecs-tasks-sg"
    Environment = var.environment
  }
}

# =============================================================================
# Application Load Balancer
# =============================================================================

# Application Load Balancer
resource "aws_lb" "main" {
  count = var.create_vpc ? 1 : 0

  name               = "${var.ecs_cluster_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb[0].id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = var.enable_deletion_protection
  idle_timeout              = var.alb_idle_timeout

  tags = {
    Name        = "${var.ecs_cluster_name}-alb"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Target Group
resource "aws_lb_target_group" "main" {
  count = var.create_vpc ? 1 : 0

  name        = "${var.ecs_cluster_name}-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main[0].id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = var.health_check_healthy_threshold
    unhealthy_threshold = var.health_check_unhealthy_threshold
    timeout             = var.health_check_timeout
    interval            = var.health_check_interval
    path                = var.health_check_path
    matcher             = "200"
  }

  deregistration_delay = var.deregistration_delay

  tags = {
    Name        = "${var.ecs_cluster_name}-tg"
    Environment = var.environment
  }
}

# HTTP Listener
resource "aws_lb_listener" "http" {
  count = var.create_vpc ? 1 : 0

  load_balancer_arn = aws_lb.main[0].arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main[0].arn
  }
}

# HTTPS Listener (optional)
resource "aws_lb_listener" "https" {
  count = var.create_vpc && var.enable_https ? 1 : 0

  load_balancer_arn = aws_lb.main[0].arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main[0].arn
  }
}

# =============================================================================
# CloudWatch Logs
# =============================================================================

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.ecs_task_family}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.ecs_task_family}-logs"
    Environment = var.environment
  }
}

# =============================================================================
# IAM Roles and Policies
# =============================================================================

# ECS Task Execution Role (used by ECS to pull images and write logs)
resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.ecs_task_family}-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.ecs_task_family}-execution-role"
    Environment = var.environment
  }
}

# Attach AWS managed policy for ECS task execution
resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Additional policy for pulling from ECR
resource "aws_iam_role_policy" "ecs_task_execution_ecr" {
  name = "${var.ecs_task_family}-ecr-policy"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      }
    ]
  })
}

# ECS Task Role (used by the application code)
resource "aws_iam_role" "ecs_task" {
  name = "${var.ecs_task_family}-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.ecs_task_family}-task-role"
    Environment = var.environment
  }
}

# Policy for S3 access (reuse existing bucket)
resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "${var.ecs_task_family}-s3-policy"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = aws_s3_bucket.video_storage.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.video_storage.arn}/*"
      }
    ]
  })
}

# Optional: ECS Exec policy for debugging
resource "aws_iam_role_policy" "ecs_exec" {
  count = var.enable_ecs_exec ? 1 : 0

  name = "${var.ecs_task_family}-exec-policy"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel"
        ]
        Resource = "*"
      }
    ]
  })
}

# =============================================================================
# ECS Cluster
# =============================================================================

resource "aws_ecs_cluster" "main" {
  name = var.ecs_cluster_name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name        = var.ecs_cluster_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# =============================================================================
# Redis Service (for job queue and pub/sub)
# =============================================================================

# CloudWatch Log Group for Redis
resource "aws_cloudwatch_log_group" "redis" {
  name              = "/ecs/${var.ecs_task_family}-redis"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.ecs_task_family}-redis-logs"
    Environment = var.environment
  }
}

# Redis Task Definition
resource "aws_ecs_task_definition" "redis" {
  family                   = "${var.ecs_task_family}-redis"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"  # 0.25 vCPU
  memory                   = "512"  # 512 MB
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  # Use Graviton (ARM64) for Redis too
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = var.use_graviton ? "ARM64" : "X86_64"
  }

  container_definitions = jsonencode([
    {
      name      = "redis"
      image     = "redis:7-alpine"
      essential = true

      portMappings = [
        {
          containerPort = 6379
          protocol      = "tcp"
        }
      ]

      command = [
        "redis-server",
        "--appendonly", "yes",
        "--appendfsync", "everysec"
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.redis.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "redis"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "redis-cli ping || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 10
      }
    }
  ])

  tags = {
    Name        = "${var.ecs_task_family}-redis"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Redis ECS Service
resource "aws_ecs_service" "redis" {
  count = var.create_vpc ? 1 : 0

  name            = "${var.ecs_service_name}-redis"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.redis.arn
  desired_count   = 1  # Redis should run as single instance
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.redis[0].id]
    assign_public_ip = true
  }

  enable_execute_command = var.enable_ecs_exec

  # Enable service discovery
  service_registries {
    registry_arn = aws_service_discovery_service.redis[0].arn
  }

  depends_on = [
    aws_iam_role_policy_attachment.ecs_task_execution
  ]

  tags = {
    Name        = "${var.ecs_service_name}-redis"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Security Group for Redis
resource "aws_security_group" "redis" {
  count = var.create_vpc ? 1 : 0

  name        = "${var.ecs_cluster_name}-redis-sg"
  description = "Security group for Redis service"
  vpc_id      = aws_vpc.main[0].id

  ingress {
    description     = "Allow Redis from ECS tasks"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks[0].id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.ecs_cluster_name}-redis-sg"
    Environment = var.environment
  }
}

# Service Discovery Namespace
resource "aws_service_discovery_private_dns_namespace" "main" {
  count = var.create_vpc ? 1 : 0

  name        = "${var.environment}.local"
  description = "Private DNS namespace for service discovery"
  vpc         = aws_vpc.main[0].id

  tags = {
    Name        = "${var.ecs_cluster_name}-namespace"
    Environment = var.environment
  }
}

# Service Discovery Service for Redis
resource "aws_service_discovery_service" "redis" {
  count = var.create_vpc ? 1 : 0

  name = "redis"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main[0].id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = {
    Name        = "${var.ecs_cluster_name}-redis-discovery"
    Environment = var.environment
  }
}

# =============================================================================
# ECS Task Definition
# =============================================================================

resource "aws_ecs_task_definition" "main" {
  family                   = var.ecs_task_family
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.ecs_task_cpu
  memory                   = var.ecs_task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  # Use Graviton (ARM64) for better performance and lower cost
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = var.use_graviton ? "ARM64" : "X86_64"
  }

  container_definitions = jsonencode([
    {
      name  = var.container_name
      image = "${aws_ecr_repository.backend.repository_url}:latest"
      
      essential = true
      
      portMappings = [
        {
          containerPort = var.container_port
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "STORAGE_BACKEND"
          value = "s3"
        },
        {
          name  = "STORAGE_BUCKET"
          value = var.bucket_name
        },
        {
          name  = "PORT"
          value = tostring(var.container_port)
        },
        {
          name  = "REDIS_URL"
          value = "redis://redis.${var.environment}.local:6379/0"
        }
      ]

      # Add sensitive environment variables here or use AWS Secrets Manager
      # secrets = [
      #   {
      #     name      = "ANTHROPIC_API_KEY"
      #     valueFrom = "arn:aws:secretsmanager:region:account:secret:name"
      #   }
      # ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:${var.container_port}/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = {
    Name        = var.ecs_task_family
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# =============================================================================
# ECS Service
# =============================================================================

resource "aws_ecs_service" "main" {
  count = var.create_vpc ? 1 : 0

  name            = var.ecs_service_name
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.main.arn
  desired_count   = var.ecs_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs_tasks[0].id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.main[0].arn
    container_name   = var.container_name
    container_port   = var.container_port
  }

  enable_execute_command = var.enable_ecs_exec

  depends_on = [
    aws_lb_listener.http,
    aws_iam_role_policy_attachment.ecs_task_execution
  ]
  
  # Deployment configuration - rolling updates
  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100

  tags = {
    Name        = var.ecs_service_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# =============================================================================
# Auto Scaling
# =============================================================================

# Auto Scaling Target
resource "aws_appautoscaling_target" "ecs" {
  count = var.create_vpc ? 1 : 0

  max_capacity       = var.ecs_max_capacity
  min_capacity       = var.ecs_min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.main[0].name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Auto Scaling Policy - CPU
resource "aws_appautoscaling_policy" "ecs_cpu" {
  count = var.create_vpc ? 1 : 0

  name               = "${var.ecs_service_name}-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs[0].resource_id
  scalable_dimension = aws_appautoscaling_target.ecs[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs[0].service_namespace

  target_tracking_scaling_policy_configuration {
    target_value       = var.autoscaling_target_cpu
    scale_in_cooldown  = 300
    scale_out_cooldown = 60

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}

# Auto Scaling Policy - Memory
resource "aws_appautoscaling_policy" "ecs_memory" {
  count = var.create_vpc ? 1 : 0

  name               = "${var.ecs_service_name}-memory-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs[0].resource_id
  scalable_dimension = aws_appautoscaling_target.ecs[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs[0].service_namespace

  target_tracking_scaling_policy_configuration {
    target_value       = var.autoscaling_target_memory
    scale_in_cooldown  = 300
    scale_out_cooldown = 60

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
  }
}

