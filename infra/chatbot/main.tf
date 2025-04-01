provider "aws" {
  region = "eu-west-1"
}

resource "aws_ecr_repository" "chatbot_repo" {
  name = "chatbot-lambda-repo"
}

resource "aws_iam_role" "lambda_exec_role" {
  name = "chatbot-lambda-exec-role"
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

resource "aws_iam_role_policy" "lambda_logging_policy" {
  name = "lambda-logging-policy"
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

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
resource "aws_iam_role_policy_attachment" "lambda_xray_access" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}
resource "aws_cloudwatch_log_group" "chatbot_logs" {
  name              = "/aws/lambda/chatbot-microservice"
  retention_in_days = 7
}

resource "aws_lambda_function" "chatbot_lambda" {
  function_name = "chatbot-microservice"
  role          = aws_iam_role.lambda_exec_role.arn
  package_type  = "Image"
  image_uri     = var.ecr_image_uri
  timeout       = 15
  memory_size   = 512
  architectures = ["arm64"]
  source_code_hash = filebase64sha256("${path.module}/../../services/chatbot/Dockerfile")
  
  environment {
    variables = {
      GEMINI_API_KEY = var.gemini_api_key
    }
  }

  tracing_config {
    mode = "Active"
  }

}


resource "aws_apigatewayv2_api" "http_api" {
  name          = "chatbot-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.http_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.chatbot_lambda.invoke_arn
}
resource "aws_lambda_permission" "allow_http_api_invoke" {
  statement_id  = "AllowExecutionFromHttpApi"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.chatbot_lambda.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*"
}

resource "aws_apigatewayv2_route" "chatbot_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /chat"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}
resource "aws_apigatewayv2_route" "root_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}
resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}
