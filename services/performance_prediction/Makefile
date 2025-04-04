# ========================
#  Real Madrid - Performance Prediction
# ========================

# -------- CONFIG --------
include $(SERVICE_DIR).env
export
SERVICE_NAME := performance_prediction
SERVICE_DIR := .
INFRA_DIR := ../../infra/$(SERVICE_NAME)
S3_BUCKET := real-madrid-performance-data-bucket

# -------- INFRA --------

setup:
	cd $(INFRA_DIR) && terraform init && terraform apply -auto-approve

monitoring:
	cd $(INFRA_DIR) && terraform init && terraform apply -target=aws_cloudwatch_dashboard.lambda_dashboard -auto-approve

alerts:
	cd $(INFRA_DIR) && terraform apply \
		-target=aws_cloudwatch_metric_alarm.error_alarm \
		-target=aws_cloudwatch_metric_alarm.duration_alarm \
		-auto-approve

plan:
	cd $(INFRA_DIR) && terraform plan

show:
	cd $(INFRA_DIR) && terraform show

# -------- SAGEMAKER FLOW --------
split-data:
	S3_BUCKET=$(S3_BUCKET) poetry run python $(SERVICE_DIR)/scripts/split_data.py

train:
	SAGEMAKER_ROLE_ARN=$(SAGEMAKER_ROLE_ARN) S3_BUCKET=$(S3_BUCKET) poetry run python $(SERVICE_DIR)/scripts/run_training_job.py

train-dnn:
	S3_BUCKET=$(S3_BUCKET) poetry run python $(SERVICE_DIR)/scripts/run_dnn_training_job.py

predict:
	poetry run python $(SERVICE_DIR)/api/match_prediction_api.py

# -------- CLEANUP --------
clean-model:
	aws s3 rm s3://$(S3_BUCKET)/performance/model/ --recursive

clean-input:
	aws s3 rm s3://$(S3_BUCKET)/performance/input/ --recursive

clean: clean-model clean-input

# -------- ALL-IN-ONE --------
all: setup split-data train
	@echo "Performance Prediction pipeline complete!"

# -------- DESTROY ALL RESOURCES --------
destroy:
	@echo "Destroying all resources for $(SERVICE_NAME)..."
	cd $(INFRA_DIR) && terraform destroy -auto-approve
	@echo "Deleting all S3 model data (if any)..."
	-aws s3 rm s3://$(S3_BUCKET)/performance/model/ --recursive
	@echo "Deleting all S3 input data (if any)..."
	-aws s3 rm s3://$(S3_BUCKET)/performance/input/ --recursive
	@echo "Cleanup complete for $(SERVICE_NAME)"

destroy-all: clean destroy
	@echo "All AWS resources created for Real Madrid - Performance Prediction have been destroyed."