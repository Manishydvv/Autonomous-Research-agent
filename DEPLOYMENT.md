# AWS & Terraform Deployment Guide

This project uses **Terraform** to provision a complete, production-grade AWS environment from scratch, and **GitHub Actions** for automated CI/CD deployment.

---

## 1. Prerequisites

Before you begin, ensure you have the following installed on your local machine:
- [AWS CLI](https://aws.amazon.com/cli/) (`aws configure` with an Administrator Access Key)
- [Terraform](https://developer.hashicorp.com/terraform/install)
- Git

*Note: You do NOT need Docker installed locally. GitHub Actions handles all image building.*

---

## 2. Infrastructure Overview

The Terraform code is modularized into a professional directory structure (`terraform/`):
- `vpc.tf`: Networking (Public/Private Subnets, Internet Gateway)
- `ecs.tf`: Fargate Cluster, Auto-scaling, Task Definitions, and ECR Repos
- `rds.tf`: PostgreSQL database (pgvector)
- `redis.tf`: ElastiCache Redis
- `alb.tf`: Application Load Balancer
- `secrets.tf`: AWS Secrets Manager
- `bedrock.tf`: AI Content Guardrails

---

## 3. Step-by-Step Deployment

### Step 1: Create the Remote State Backend
Terraform requires a highly secure S3 bucket and DynamoDB table to store its state file and lock deployments. Run the provided bootstrap script to create these automatically.

**Windows:**
```cmd
.\bootstrap.bat
```
**Mac / Linux:**
```bash
chmod +x bootstrap.sh
./bootstrap.sh
```

### Step 2: Initialize & Apply Terraform
Navigate into the terraform folder and initialize the backend:
```bash
cd terraform
terraform init
```

Next, deploy the infrastructure. You must provide a master API key (used to secure your FastAPI endpoints). We use placeholders for the Docker images since they haven't been built yet.
```bash
terraform apply -var="api_key=your_secure_password" -var="app_image=placeholder" -var="pyrit_image=placeholder"
```
Type `yes` when prompted. **This process takes 5-10 minutes** as AWS provisions the PostgreSQL RDS database. 

*At the end of the deployment, save the `alb_dns` output (e.g., `research-agent-alb-xxx.us-east-1.elb.amazonaws.com`). This is your app's public URL!*

---

## 4. Configuring Secrets

Terraform created an AWS Secrets Manager vault for you, but filled it with dummy values to prevent accidentally committing your API keys to GitHub.

1. Go to the **AWS Console → Secrets Manager**
2. Search for the secret named `research-agent/config`
3. Click **Retrieve secret value → Edit**
4. Replace the `"REPLACE_ME"` placeholders with your actual keys:
   - `OPENAI_API_KEY`
   - `GROQ_API_KEY`
   - `LANGSMITH_API_KEY`

---

## 5. CI/CD Pipeline (GitHub Actions)

Your app will automatically build and deploy whenever you push code to the `main` branch. 

Before you push, you must give GitHub permission to access your AWS account:
1. Go to your repository on GitHub.com
2. Navigate to **Settings → Secrets and variables → Actions → New repository secret**
3. Add the following two secrets:
   - `AWS_ACCESS_KEY_ID` (Your IAM user access key)
   - `AWS_SECRET_ACCESS_KEY` (Your IAM user secret key)

Now, trigger the deployment:
```bash
git add .
git commit -m "Initial AWS deployment"
git push origin main
```
Go to the **Actions** tab in GitHub to watch it build the `uv`-optimized Docker images and push them to ECR!

---

## 6. Teardown & Deletion

When you are finished testing, you can completely destroy all AWS resources with a single command to stop all billing charges:

```bash
cd terraform
terraform destroy -var="api_key=placeholder" -var="app_image=placeholder" -var="pyrit_image=placeholder"
```
Type `yes` when prompted. 

*Note: This will safely delete the ECS cluster, databases, and load balancers. It intentionally leaves behind the S3 State Bucket and DynamoDB lock table, as those cost $0.00/month while empty and are required for future deployments.*
