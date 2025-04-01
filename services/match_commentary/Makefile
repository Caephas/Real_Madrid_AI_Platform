# ======== CONFIG ==========
SERVICE_NAME := match-commentary
ECR_REPO := 557690602321.dkr.ecr.eu-west-1.amazonaws.com/$(SERVICE_NAME)-lambda-repo
IMAGE_TAG := latest
IMAGE_URI := $(ECR_REPO):$(IMAGE_TAG)
INFRA_DIR=../../infra/match_commentary

# ======== COMMANDS ==========
monitoring:
	cd $(INFRA_DIR) && terraform init && terraform apply -target=aws_cloudwatch_dashboard.lambda_dashboard -auto-approve	

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
	@echo "🔐 Logging into ECR..."
	aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin $(ECR_REPO)

push: login
	docker push $(IMAGE_URI)

deploy:
	cd $(INFRA_DIR) && terraform init && terraform apply -auto-approve

all: build tag push deploy
	@echo "Deployment complete for $(SERVICE_NAME)"