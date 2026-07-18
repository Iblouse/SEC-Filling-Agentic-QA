data "aws_iam_policy_document" "ecs_task_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "ecs_task_execution" {
  name               = "${var.project_name}-ecs-task-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ingestion_task" {
  name               = "${var.project_name}-ingestion-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
}

data "aws_iam_policy_document" "ingestion_task" {
  statement {
    sid    = "ListProjectBuckets"
    effect = "Allow"
    actions = [
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.raw.arn,
      aws_s3_bucket.curated.arn
    ]
  }

  statement {
    sid    = "ReadWriteProjectObjects"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:AbortMultipartUpload"
    ]
    resources = [
      "${aws_s3_bucket.raw.arn}/*",
      "${aws_s3_bucket.curated.arn}/*"
    ]
  }

  statement {
    sid    = "ProcessIngestionQueue"
    effect = "Allow"
    actions = [
      "sqs:ChangeMessageVisibility",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "sqs:ReceiveMessage",
      "sqs:SendMessage"
    ]
    resources = [
      aws_sqs_queue.ingestion.arn,
      aws_sqs_queue.ingestion_dlq.arn
    ]
  }
}

resource "aws_iam_role_policy" "ingestion_task" {
  name   = "${var.project_name}-ingestion-access"
  role   = aws_iam_role.ingestion_task.id
  policy = data.aws_iam_policy_document.ingestion_task.json
}
