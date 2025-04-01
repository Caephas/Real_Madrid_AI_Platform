data "archive_file" "match_commentary_source" {
  type        = "zip"
  source_dir  = "${path.module}/../../services/match_commentary"
  output_path = "${path.module}/../../services/match_commentary/tmp.zip"
}

resource "aws_lambda_function" "match_commentary_lambda" {
  function_name = "match-commentary-service"
  role          = aws_iam_role.lambda_exec_role.arn
  package_type  = "Image"
  image_uri     = var.match_commentary_image_uri
  architectures = ["arm64"]
  timeout       = 15
  memory_size   = 512
  source_code_hash = data.archive_file.match_commentary_source.output_base64sha256

  environment {
    variables = {
      API_FOOTBALL_BASE_URL = var.api_football_base_url
      API_FOOTBALL_KEY      = var.api_football_key
      DYNAMODB_TABLE        = "match_events"
    }
  }

  tracing_config {
    mode = "Active"
  }
}

resource "aws_iam_role_policy" "lambda_logging_policy" {
  name = "match-commentary-logging-policy"
  role = aws_iam_role.lambda_exec_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:StartQuery",
          "logs:GetQueryResults"
        ],
        Resource = "arn:aws:logs:eu-west-1:*:*"
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "match_commentary_logs" {
  name              = "/aws/lambda/match-commentary-service"
  retention_in_days = 7
}

resource "aws_iam_role" "lambda_exec_role" {
  name = "match-commentary-lambda-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Principal = {
        Service = "lambda.amazonaws.com"
      },
      Effect = "Allow",
      Sid = ""
    }]
  })
}
resource "aws_dynamodb_table" "match_events" {
  name           = "match_events"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "event_id"

  attribute {
    name = "event_id"
    type = "S"
  }

  tags = {
    Name = "Match Events Table"
  }
}
resource "aws_iam_role_policy" "dynamodb_write_policy" {
  name = "match-commentary-dynamodb-write"
  role = aws_iam_role.lambda_exec_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "dynamodb:PutItem"
        ],
        Resource = aws_dynamodb_table.match_events.arn
      }
    ]
  })
}



resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_xray_access" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

resource "aws_apigatewayv2_api" "match_commentary_api" {
  name          = "match-commentary-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "match_commentary_lambda_integration" {
  api_id           = aws_apigatewayv2_api.match_commentary_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.match_commentary_lambda.invoke_arn
}

resource "aws_lambda_permission" "match_commentary_api_permission" {
  statement_id  = "AllowMatchCommentaryInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.match_commentary_lambda.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.match_commentary_api.execution_arn}/*"
}

resource "aws_apigatewayv2_route" "root_route" {
  api_id    = aws_apigatewayv2_api.match_commentary_api.id
  route_key = "GET /"
  target    = "integrations/${aws_apigatewayv2_integration.match_commentary_lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "match_commentary_route" {
  api_id    = aws_apigatewayv2_api.match_commentary_api.id
  route_key = "GET /commentary/{team_id}"
  target    = "integrations/${aws_apigatewayv2_integration.match_commentary_lambda_integration.id}"
}

resource "aws_ecr_repository" "match_commentary_repo" {
  name = "match-commentary-lambda-repo"
}
resource "aws_apigatewayv2_stage" "match_commentary_stage" {
  api_id      = aws_apigatewayv2_api.match_commentary_api.id
  name        = "$default"
  auto_deploy = true
}