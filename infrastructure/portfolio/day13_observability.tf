locals {
  api_alarm_actions = var.api_alarm_sns_topic_arn == "" ? [] : [var.api_alarm_sns_topic_arn]
  api_metric_dimensions = {
    Service     = var.project_name
    Environment = var.api_environment
  }
}

resource "aws_cloudwatch_metric_alarm" "api_server_errors" {
  alarm_name          = "${var.project_name}-api-server-errors"
  alarm_description   = "The SEC QA API emitted one or more server errors in five minutes."
  namespace           = var.api_metrics_namespace
  metric_name         = "ServerErrorCount"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  dimensions          = local.api_metric_dimensions
  alarm_actions       = local.api_alarm_actions
  ok_actions          = local.api_alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "api_high_latency" {
  alarm_name          = "${var.project_name}-api-high-latency"
  alarm_description   = "The maximum API request latency exceeded 15 seconds."
  namespace           = var.api_metrics_namespace
  metric_name         = "RequestLatency"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanThreshold"
  threshold           = 15000
  treat_missing_data  = "notBreaching"
  dimensions          = local.api_metric_dimensions
  alarm_actions       = local.api_alarm_actions
  ok_actions          = local.api_alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "api_abstention_spike" {
  alarm_name          = "${var.project_name}-api-abstention-spike"
  alarm_description   = "The API produced at least five abstentions in fifteen minutes."
  namespace           = var.api_metrics_namespace
  metric_name         = "AbstentionCount"
  statistic           = "Sum"
  period              = 900
  evaluation_periods  = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 5
  treat_missing_data  = "notBreaching"
  dimensions          = local.api_metric_dimensions
  alarm_actions       = local.api_alarm_actions
  ok_actions          = local.api_alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "api_unhealthy_targets" {
  alarm_name          = "${var.project_name}-api-unhealthy-targets"
  alarm_description   = "The Application Load Balancer has an unhealthy API target."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "UnHealthyHostCount"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  dimensions = {
    LoadBalancer = aws_lb.api.arn_suffix
    TargetGroup  = aws_lb_target_group.api.arn_suffix
  }
  alarm_actions = local.api_alarm_actions
  ok_actions    = local.api_alarm_actions
}

resource "aws_cloudwatch_dashboard" "api" {
  dashboard_name = "${var.project_name}-api"
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "API traffic and server errors"
          region = var.aws_region
          view   = "timeSeries"
          metrics = [
            [var.api_metrics_namespace, "RequestCount", "Service", var.project_name, "Environment", var.api_environment, { stat = "Sum" }],
            [".", "ServerErrorCount", ".", ".", ".", ".", { stat = "Sum" }]
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Latency"
          region = var.aws_region
          view   = "timeSeries"
          metrics = [
            [var.api_metrics_namespace, "RequestLatency", "Service", var.project_name, "Environment", var.api_environment, { stat = "Average" }],
            [".", "AnswerLatency", ".", ".", ".", ".", { stat = "Average" }]
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "Answer quality signals"
          region = var.aws_region
          view   = "timeSeries"
          metrics = [
            [var.api_metrics_namespace, "AnswerCount", "Service", var.project_name, "Environment", var.api_environment, { stat = "Sum" }],
            [".", "AbstentionCount", ".", ".", ".", ".", { stat = "Sum" }],
            [".", "RevisionCount", ".", ".", ".", ".", { stat = "Sum" }],
            [".", "CitationFailureCount", ".", ".", ".", ".", { stat = "Sum" }]
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "User feedback"
          region = var.aws_region
          view   = "timeSeries"
          metrics = [
            [var.api_metrics_namespace, "FeedbackCount", "Service", var.project_name, "Environment", var.api_environment, { stat = "Sum" }],
            [".", "NegativeFeedbackCount", ".", ".", ".", ".", { stat = "Sum" }]
          ]
        }
      }
    ]
  })
}
