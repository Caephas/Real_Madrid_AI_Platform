output "sagemaker_role_arn" {
  value = aws_iam_role.sagemaker_execution_role.arn
}

output "performance_bucket_name" {
  value = aws_s3_bucket.performance_prediction_bucket.bucket
}