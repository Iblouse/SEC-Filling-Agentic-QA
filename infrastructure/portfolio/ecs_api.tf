resource "aws_ecs_cluster" "api" {
  name = "${var.project_name}-api"

  setting {
    name  = "containerInsights"
    value = var.api_enable_container_insights ? "enabled" : "disabled"
  }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project_name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.api_cpu)
  memory                   = tostring(var.api_memory)
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.api_task.arn

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = "${aws_ecr_repository.application.repository_url}:${var.api_image_tag}"
      essential = true

      portMappings = [
        {
          containerPort = var.api_container_port
          hostPort      = var.api_container_port
          protocol      = "tcp"
          appProtocol   = "http"
        }
      ]

      environment = [
        { name = "AWS_REGION", value = var.aws_region },
        { name = "PORT", value = tostring(var.api_container_port) },
        { name = "QA_ARTIFACT_BUCKET", value = aws_s3_bucket.curated.bucket },
        {
          name  = "QA_ARTIFACT_MANIFEST_KEY"
          value = "${var.api_artifact_prefix}/manifest.json"
        },
        { name = "QA_ARTIFACT_DIRECTORY", value = "/tmp/edgar-qa" },
        { name = "QA_CANDIDATE_K", value = tostring(var.api_candidate_k) },
        {
          name  = "QA_RERANK_CANDIDATES"
          value = tostring(var.api_rerank_candidates)
        },
        { name = "QA_EVIDENCE_K", value = tostring(var.api_evidence_k) },
        { name = "QA_FEEDBACK_TABLE_NAME", value = aws_dynamodb_table.api_feedback.name },
        {
          name  = "QA_FEEDBACK_TTL_DAYS"
          value = tostring(var.api_feedback_ttl_days)
        },
        { name = "QA_METRICS_NAMESPACE", value = var.api_metrics_namespace },
        { name = "QA_SERVICE_NAME", value = var.project_name },
        { name = "QA_ENVIRONMENT", value = var.api_environment }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.application.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "api"
        }
      }

      linuxParameters = {
        initProcessEnabled = true
      }

      healthCheck = {
        command = [
          "CMD-SHELL",
          "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:${var.api_container_port}/healthz', timeout=3)\" || exit 1"
        ]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 120
      }
    }
  ])
}

resource "aws_ecs_service" "api" {
  name            = "${var.project_name}-api"
  cluster         = aws_ecs_cluster.api.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  health_check_grace_period_seconds = 300
  wait_for_steady_state             = true

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    assign_public_ip = true
    security_groups  = [aws_security_group.api_task.id]
    subnets          = aws_subnet.api_public[*].id
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = var.api_container_port
  }

  depends_on = [aws_lb_listener.api_http]
}
