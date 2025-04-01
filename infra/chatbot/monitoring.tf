variable "lambda_function_name" {
  description = "Lambda function name to monitor"
  type        = string
  default     = "chatbot-service"
}

variable "aws_region" {
  default = "eu-west-1"
}

resource "aws_cloudwatch_dashboard" "lambda_dashboard" {
  dashboard_name = "${var.lambda_function_name}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric",
        x    = 0,
        y    = 0,
        width = 24,
        height = 6,
        properties = {
          view     = "timeSeries",
          stacked  = false,
          region   = var.aws_region,
          metrics  = [
            [ "AWS/Lambda", "Invocations", "FunctionName", var.lambda_function_name ],
            [ ".", "Errors", ".", "." ],
            [ ".", "Duration", ".", ".", { "stat": "p90" } ]
          ],
          title= "Chatbot - Invocations, Errors, Duration (p90)"
        }
      }
    ]
  })
}
resource "aws_cloudwatch_metric_alarm" "error_alarm" {
  alarm_name          = "${var.lambda_function_name}-HighErrors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Triggers when Lambda has > 0 errors in a 1-minute window"
  dimensions = {
    FunctionName = var.lambda_function_name
  }
}
resource "aws_cloudwatch_metric_alarm" "duration_alarm" {
  alarm_name          = "${var.lambda_function_name}-HighLatency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 60
  extended_statistic  = "p90" # ✅ use this instead of 'statistic'
  threshold           = 1000
  alarm_description   = "Triggers when p90 duration exceeds 1s"
  dimensions = {
    FunctionName = var.lambda_function_name
  }
}