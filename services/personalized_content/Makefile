# ---------- CONFIG ----------
SERVICE_NAME=personalized-content
AWS_ACCOUNT_ID=557690602321
REGION=eu-west-1
IMAGE_REPO=$(AWS_ACCOUNT_ID).dkr.ecr.$(REGION).amazonaws.com/$(SERVICE_NAME)-lambda-repo
TAG=latest
INFRA_DIR=../../infra/personalized_content
# ---------- COMMANDS ----------

# 0. ECR Login
login:
	@echo "🔐 Logging into ECR..."
	aws ecr get-login-password --region $(REGION) | docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.$(REGION).amazonaws.com

# 1. Build Docker Image
build:
	docker build -t $(SERVICE_NAME)-lambda .

# 2. Tag Docker Image
tag:
	docker tag $(SERVICE_NAME)-lambda:$(TAG) $(IMAGE_REPO):$(TAG)

# 3. Push to ECR (includes login)
push: login
	docker push $(IMAGE_REPO):$(TAG)

# 4. Terraform Deploy
deploy:
	cd $(INFRA_DIR) && terraform init && terraform apply -auto-approve

# 5. Full Flow
all: build tag push deploy
	@echo "Deployment complete for $(SERVICE_NAME)"