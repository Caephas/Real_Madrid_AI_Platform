# ======== CONFIG ==========
SERVICE_NAME := chatbot
ECR_REPO := 557690602321.dkr.ecr.eu-west-1.amazonaws.com/$(SERVICE_NAME)-lambda-repo
IMAGE_TAG := latest
IMAGE_URI := $(ECR_REPO):$(IMAGE_TAG)
TERRAFORM_DIR := ../../infra/$(SERVICE_NAME)

# ======== COMMANDS ==========
monitoring:
	cd $(TERRAFORM_DIR) && terraform apply -target=aws_cloudwatch_dashboard.lambda_dashboard -auto-approve

alerts:
	cd $(TERRAFORM_DIR) && terraform apply \
		-target=aws_cloudwatch_metric_alarm.error_alarm \
		-target=aws_cloudwatch_metric_alarm.duration_alarm \
		-auto-approve	

build:
	docker build -t $(SERVICE_NAME)-lambda .

tag:
	docker tag $(SERVICE_NAME)-lambda:latest $(IMAGE_URI)

login:
	@echo "Logging into ECR..."
	aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin $(ECR_REPO)

# Phase 1: Create only the ECR repository (and any other prerequisites)
deploy-ecr:
	cd $(TERRAFORM_DIR) && terraform init && terraform apply -target=aws_ecr_repository.chatbot_repo -auto-approve

# Phase 3: Deploy the remaining infrastructure
deploy-all:
	cd $(TERRAFORM_DIR) && terraform apply -auto-approve

# Push the Docker image (after repository exists)
push: login
	docker push $(IMAGE_URI)

# The final "all" target orchestrates the sequence:
# 1. Build & Tag the image.
# 2. Deploy ECR repository via Terraform.
# 3. Push the image.
# 4. Deploy remaining resources.
# 5. Apply monitoring configuration.
all: build tag deploy-ecr push deploy-all monitoring
	@echo "Deployment complete for $(SERVICE_NAME)"

destroy:
	@echo "Destroying all resources for $(SERVICE_NAME)..."
	cd $(TERRAFORM_DIR) && terraform destroy -auto-approve
	@echo "Deleting all ECR images (if any)..."
	-aws ecr list-images --repository-name $(SERVICE_NAME)-lambda-repo --region eu-west-1 --query 'imageIds[*]' --output json | jq -c '.' | xargs -I {} aws ecr batch-delete-image --repository-name $(SERVICE_NAME)-lambda-repo --region eu-west-1 --image-ids '{}'
	@echo "Deleting ECR repository..."
	-aws ecr delete-repository --repository-name $(SERVICE_NAME)-lambda-repo --region eu-west-1 --force
	@echo "Removing local Docker images..."
	-docker rmi $(IMAGE_URI) || true
	-docker rmi $(SERVICE_NAME)-lambda || true
	@echo "Cleanup complete for $(SERVICE_NAME)"