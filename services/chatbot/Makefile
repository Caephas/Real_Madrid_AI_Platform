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
	@echo "🔐 Logging into ECR..."
	aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin $(ECR_REPO)

push: login
	docker push $(IMAGE_URI)

deploy:
	cd $(TERRAFORM_DIR) && terraform init && terraform apply -auto-approve

all: build tag push deploy
	@echo "Deployment complete for $(SERVICE_NAME)"