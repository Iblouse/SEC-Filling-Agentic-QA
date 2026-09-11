
resource "aws_iam_role" "api_task" {
  name               = "${var.project_name}-api-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
}

data "aws_iam_policy_document" "api_task" {
  statement {
    sid     = "ReadRuntimeArtifacts"
    effect  = "Allow"
    actions = ["s3:GetObject"]
    resources = [
      "${aws_s3_bucket.curated.arn}/${var.api_artifact_prefix}/*"
    ]
  }

  statement {
    sid    = "InvokeEmbeddingRerankAndAnswerModels"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel"
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v2:0",
      "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}::foundation-model/cohere.rerank-v3-5:0",
      "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}:${local.account_id}:inference-profile/us.amazon.nova-2-lite-v1:0",
      "arn:${data.aws_partition.current.partition}:bedrock:us-east-1::foundation-model/amazon.nova-2-lite-v1:0",
      "arn:${data.aws_partition.current.partition}:bedrock:us-east-2::foundation-model/amazon.nova-2-lite-v1:0",
      "arn:${data.aws_partition.current.partition}:bedrock:us-west-2::foundation-model/amazon.nova-2-lite-v1:0"
    ]
  }

  statement {
    sid       = "UseRerankAPI"
    effect    = "Allow"
    actions   = ["bedrock:Rerank"]
    resources = ["*"]
  }

  statement {
    sid     = "ReadNovaInferenceProfile"
    effect  = "Allow"
    actions = ["bedrock:GetInferenceProfile"]
    resources = [
      "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}:${local.account_id}:inference-profile/us.amazon.nova-2-lite-v1:0"
    ]
  }
}

resource "aws_iam_role_policy" "api_task" {
  name   = "${var.project_name}-api-runtime-access"
  role   = aws_iam_role.api_task.id
  policy = data.aws_iam_policy_document.api_task.json
}
