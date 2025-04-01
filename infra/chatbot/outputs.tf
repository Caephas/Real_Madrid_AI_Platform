output "api_gateway_invoke_url" {
  description = "Public URL to invoke the chatbot Lambda through API Gateway"
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}