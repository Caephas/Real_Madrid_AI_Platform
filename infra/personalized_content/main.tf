data "archive_file" "personalized_content_source" {
  type        = "zip"
  source_dir  = "${path.module}/../../services/personalized_content"
  output_path = "${path.module}/../../services/personalized_content/tmp.zip"
}
resource "aws_dynamodb_table" "articles" {
  name         = "articles"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "article_id"

  attribute {
    name = "article_id"
    type = "S"
  }
}
resource "aws_ecr_repository" "personalized_content_repo" {
  name = "personalized-content-lambda-repo"
}
resource "aws_dynamodb_table" "users" {
  name         = "users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }
}

resource "aws_lambda_function" "personalized_lambda" {
  function_name = "personalized-content-service"
  role          = aws_iam_role.lambda_exec_role.arn
  package_type  = "Image"
  image_uri     = var.personalized_content_image_uri
  architectures = ["arm64"]
  timeout       = 15
  memory_size   = 512

  source_code_hash = data.archive_file.personalized_content_source.output_base64sha256

  environment {
    variables = {
      DYNAMODB_ARTICLE_TABLE = "articles"
      DYNAMODB_USER_TABLE    = "users"
    }
  }

  tracing_config {
    mode = "Active"
  }
}
resource "aws_iam_role" "lambda_exec_role" {
  name = "personalized-content-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "lambda_logging_policy" {
  name = "personalized-content-logging-policy"
  role = aws_iam_role.lambda_exec_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = [
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:StartQuery",
        "logs:GetQueryResults"
      ],
      Resource = "arn:aws:logs:eu-west-1:*:*"
    }]
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

resource "aws_iam_role_policy" "dynamodb_access_policy" {
  name = "personalized-content-dynamodb-access"
  role = aws_iam_role.lambda_exec_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ],
        Resource = [
          aws_dynamodb_table.articles.arn,
          aws_dynamodb_table.users.arn
        ]
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "personalized_logs" {
  name              = "/aws/lambda/personalized-content-service"
  retention_in_days = 7
}

resource "aws_apigatewayv2_api" "personalized_api" {
  name          = "personalized-content-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.personalized_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.personalized_lambda.invoke_arn
}

resource "aws_lambda_permission" "allow_invoke" {
  statement_id  = "AllowExecutionFromHttpApi"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.personalized_lambda.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.personalized_api.execution_arn}/*"
}

resource "aws_apigatewayv2_route" "root_route" {
  api_id    = aws_apigatewayv2_api.personalized_api.id
  route_key = "GET /"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "recommendation_route" {
  api_id    = aws_apigatewayv2_api.personalized_api.id
  route_key = "GET /recommendations/{user_id}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.personalized_api.id
  name        = "$default"
  auto_deploy = true
}