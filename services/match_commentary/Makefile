# ======== CONFIG ==========
SERVICE_NAME := match-commentary
ECR_REPO := 557690602321.dkr.ecr.eu-west-1.amazonaws.com/$(SERVICE_NAME)-lambda-repo
IMAGE_TAG := latest
IMAGE_URI := $(ECR_REPO):$(IMAGE_TAG)
INFRA_DIR := ../../infra/match_commentary

# ======== COMMANDS ==========
monitoring:
	cd $(INFRA_DIR) && terraform apply -target=aws_cloudwatch_dashboard.lambda_dashboard -auto-approve

alerts:
	cd $(INFRA_DIR) && terraform apply \
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

# Phase 1: Create only the ECR repository (and any prerequisites)
deploy-ecr:
	cd $(INFRA_DIR) && terraform init && terraform apply -target=aws_ecr_repository.match_commentary_repo -auto-approve

# Phase 3: Deploy the remaining infrastructure
deploy-all:
	cd $(INFRA_DIR) && terraform apply -auto-approve

# Push the Docker image (after the repository exists)
push: login
	docker push $(IMAGE_URI)

# The final "all" target orchestrates the sequence:
# 1. Build & Tag the image.
# 2. Deploy ECR repository via Terraform.
# 3. Push the image.
# 4. Deploy the remaining resources.
# 5. Apply monitoring and alerts.
all: build tag deploy-ecr push deploy-all monitoring alerts
	@echo "Deployment complete for $(SERVICE_NAME)"

destroy:
	@echo "Destroying all resources for $(SERVICE_NAME)..."
	cd $(INFRA_DIR) && terraform destroy -auto-approve
	@echo "Cleanup complete for $(SERVICE_NAME)"