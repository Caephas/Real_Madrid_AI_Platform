# ---------- CONFIG ----------
SERVICE_NAME := personalized-content
AWS_ACCOUNT_ID := 557690602321
REGION := eu-west-1
ECR_REPO := $(AWS_ACCOUNT_ID).dkr.ecr.$(REGION).amazonaws.com/$(SERVICE_NAME)-lambda-repo
IMAGE_TAG := latest
IMAGE_URI := $(ECR_REPO):$(IMAGE_TAG)
TERRAFORM_DIR := ../../infra/personalized_content
LAMBDA_NAME := personalized-content-service

# ======== MONITORING ==========
monitoring:
	cd $(TERRAFORM_DIR) && terraform init && terraform apply -target=aws_cloudwatch_dashboard.lambda_dashboard -auto-approve
	@echo "Dashboard: https://$(REGION).console.aws.amazon.com/cloudwatch/home#dashboards:name=$(LAMBDA_NAME)-dashboard"

alerts:
	cd $(TERRAFORM_DIR) && terraform apply \
		-target=aws_cloudwatch_metric_alarm.error_alarm \
		-target=aws_cloudwatch_metric_alarm.duration_alarm \
		-auto-approve

# ---------- COMMANDS ----------

# 0. ECR Login
login:
	@echo "Logging into ECR..."
	aws ecr get-login-password --region $(REGION) | docker login --username AWS --password-stdin $(ECR_REPO)

# 1. Build Docker Image
build:
	docker build -t $(SERVICE_NAME)-lambda .

# 2. Tag Docker Image
tag:
	docker tag $(SERVICE_NAME)-lambda:latest $(IMAGE_URI)

# Phase 1: Create only the ECR repository (and any other prerequisites)
deploy-ecr:
	cd $(TERRAFORM_DIR) && terraform init && terraform apply -target=aws_ecr_repository.personalized_content_repo -auto-approve

# Phase 3: Deploy the remaining infrastructure
deploy-all:
	cd $(TERRAFORM_DIR) && terraform apply -auto-approve

# 3. Push the Docker image (after repository exists)
push: login
	docker push $(IMAGE_URI)

# 4. Full Flow: Orchestrate the sequence
all: build tag deploy-ecr push deploy-all monitoring alerts
	@echo "Deployment complete for $(SERVICE_NAME)"

# -------- DESTROY ALL RESOURCES --------
destroy:
	@echo "Destroying all resources for $(SERVICE_NAME)..."
	cd $(TERRAFORM_DIR) && terraform destroy -auto-approve
	@echo "Deleting all ECR images (if any)..."
	-aws ecr list-images --repository-name $(SERVICE_NAME)-lambda-repo --region $(REGION) --query 'imageIds[*]' --output json | jq -c '.' | xargs -I {} aws ecr batch-delete-image --repository-name $(SERVICE_NAME)-lambda-repo --region $(REGION) --image-ids '{}'
	@echo "Deleting ECR repository..."
	-aws ecr delete-repository --repository-name $(SERVICE_NAME)-lambda-repo --region $(REGION) --force
	@echo "Removing local Docker images..."
	-docker rmi $(IMAGE_URI) || true
	-docker rmi $(SERVICE_NAME)-lambda || true
	@echo "Cleanup complete for $(SERVICE_NAME)"