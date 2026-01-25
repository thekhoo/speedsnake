# SpeedSnake Infrastructure

This directory contains CloudFormation templates and deployment scripts for SpeedSnake's AWS infrastructure.

## Overview

The infrastructure uses a two-stage CloudFormation deployment system:

1. **IAM Deployment Role** (`deployment-role.yml`) - Creates a deployment role specific to this repository
2. **Infrastructure Resources** (`template.yml`) - Creates the S3 bucket for storing speedtest results

The deployment uses GitHub Actions with OIDC authentication and role chaining:
```
GitHub Actions → Central OIDC Role → Deployment Role → Deploy Infrastructure
```

## Files

- **`deployment-role.yml`** - CloudFormation template for the IAM deployment role
- **`template.yml`** - CloudFormation template for S3 bucket infrastructure
- **`update-deployment-role.py`** - Python script to deploy/update the IAM role locally
- **`README.md`** - This documentation file

## Prerequisites

### AWS Setup

1. **Central OIDC Role** - A central OIDC role must already exist that can assume roles with:
   - Prefix: `GithubActions-PR-thekhoo-*`
   - Tag: `allow-github-actions-access=true`

2. **AWS Credentials** - For local IAM role deployment, configure AWS credentials:
   ```bash
   # Option 1: AWS CLI profile
   export AWS_PROFILE=your-profile

   # Option 2: Environment variables
   export AWS_ACCESS_KEY_ID=your-key
   export AWS_SECRET_ACCESS_KEY=your-secret
   ```

3. **Python Dependencies** - Install boto3 for the deployment script:
   ```bash
   # With pip
   pip install boto3

   # With uv
   uv pip install boto3
   ```

### GitHub Secrets

The following secrets must be configured in the GitHub repository (Settings → Secrets and variables → Actions):

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `AWS_OIDC_ROLE_ARN` | ARN of the central OIDC role | `arn:aws:iam::123456789012:role/CentralOIDCRole` |
| `AWS_DEPLOY_ROLE_ARN` | ARN of the speedsnake deployment role (created in Step 1) | `arn:aws:iam::123456789012:role/GithubActions-PR-thekhoo-speedsnake-deploy` |
| `AWS_REGION` | Target AWS region for deployments | `us-east-1` |

## Deployment Order

### Step 1: Deploy IAM Role (One-Time Setup)

The IAM deployment role must be created first, before the infrastructure can be deployed.

**Run the deployment script locally:**

```bash
cd infrastructure

# Deploy the IAM role
python update-deployment-role.py \
  --region us-east-1 \
  --central-role-arn arn:aws:iam::123456789012:role/CentralOIDCRole

# Or with AWS CLI profile
python update-deployment-role.py \
  --region us-east-1 \
  --central-role-arn arn:aws:iam::123456789012:role/CentralOIDCRole \
  --profile your-profile

# Dry run (validate only, no deployment)
python update-deployment-role.py \
  --region us-east-1 \
  --central-role-arn arn:aws:iam::123456789012:role/CentralOIDCRole \
  --dry-run
```

**After successful deployment:**

1. The script will display the deployment role ARN
2. Add the role ARN to GitHub secrets as `AWS_DEPLOY_ROLE_ARN`
3. Ensure `AWS_OIDC_ROLE_ARN` and `AWS_REGION` secrets are also configured

### Step 2: Deploy Infrastructure (Automatic)

Once the IAM role is created and secrets are configured, infrastructure deployments happen automatically via GitHub Actions.

**Automatic deployment triggers:**
- Push to `main` branch when `infrastructure/template.yml` changes
- Manual trigger via GitHub Actions UI (workflow_dispatch)

**The workflow will:**
1. Authenticate with central OIDC role using GitHub OIDC token
2. Assume the deployment role using role chaining
3. Validate the CloudFormation template
4. Deploy or update the S3 bucket infrastructure
5. Display stack outputs (bucket name, ARN, region)

## Manual Deployment

### Deploy IAM Role Manually (Alternative to Script)

```bash
aws cloudformation deploy \
  --stack-name speedsnake-deployment-role \
  --template-file deployment-role.yml \
  --parameter-overrides \
    GitHubOrg=thekhoo \
    GitHubRepo=speedsnake \
    CentralOIDCRoleArn=arn:aws:iam::123456789012:role/CentralOIDCRole \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# Get role ARN from stack outputs
aws cloudformation describe-stacks \
  --stack-name speedsnake-deployment-role \
  --query 'Stacks[0].Outputs[?OutputKey==`RoleArn`].OutputValue' \
  --output text
```

### Deploy Infrastructure Manually (For Testing)

```bash
# Validate template
aws cloudformation validate-template \
  --template-body file://template.yml

# Deploy stack
aws cloudformation deploy \
  --stack-name speedsnake-infrastructure \
  --template-file template.yml \
  --parameter-overrides \
    BucketName=speedsnake \
    Environment=production \
  --region us-east-1

# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name speedsnake-infrastructure \
  --query 'Stacks[0].Outputs'
```

## IAM Deployment Role Details

**Role Name:** `GithubActions-PR-thekhoo-speedsnake-deploy`

**Trust Policy:** Allows assumption by the central OIDC role

**Permissions:**
- CloudFormation: Full access to stacks with `speedsnake-*` prefix
- S3: Full access to buckets with `speedsnake*` prefix
- S3: List all buckets (for validation)

**Tags:**
- `allow-github-actions-access=true` (required for central role to assume)
- `Project=speedsnake`
- `ManagedBy=CloudFormation`

## Infrastructure Resources

### S3 Bucket

**Resource:** `SpeedtestResultsBucket`

**Configuration:**
- **Name:** `speedsnake-<AWS-Account-ID>` (globally unique)
- **Versioning:** Enabled (for data protection)
- **Encryption:** AES256 server-side encryption
- **Public Access:** Blocked (all four settings)
- **Tags:** Project, Environment, ManagedBy, Purpose

**Outputs:**
- `BucketName` - The created bucket name
- `BucketArn` - The bucket ARN for IAM policies
- `BucketRegion` - The region where bucket was created

## Updating Stacks

### Update IAM Role

Re-run the deployment script with new parameters:

```bash
python update-deployment-role.py \
  --region us-east-1 \
  --central-role-arn arn:aws:iam::123456789012:role/CentralOIDCRole
```

Or update manually:

```bash
aws cloudformation update-stack \
  --stack-name speedsnake-deployment-role \
  --template-body file://deployment-role.yml \
  --parameters \
    ParameterKey=GitHubOrg,ParameterValue=thekhoo \
    ParameterKey=GitHubRepo,ParameterValue=speedsnake \
    ParameterKey=CentralOIDCRoleArn,ParameterValue=arn:aws:iam::123456789012:role/CentralOIDCRole \
  --capabilities CAPABILITY_NAMED_IAM
```

### Update Infrastructure

Infrastructure updates happen automatically when you push changes to `infrastructure/template.yml` on the `main` branch.

Or update manually:

```bash
aws cloudformation update-stack \
  --stack-name speedsnake-infrastructure \
  --template-body file://template.yml \
  --parameters \
    ParameterKey=BucketName,UsePreviousValue=true \
    ParameterKey=Environment,UsePreviousValue=true
```

## Deleting Stacks

### Delete Infrastructure First

```bash
# Empty the S3 bucket first (required before deletion)
aws s3 rm s3://speedsnake-<account-id> --recursive

# Delete the infrastructure stack
aws cloudformation delete-stack \
  --stack-name speedsnake-infrastructure

# Wait for deletion to complete
aws cloudformation wait stack-delete-complete \
  --stack-name speedsnake-infrastructure
```

### Delete IAM Role Second

```bash
aws cloudformation delete-stack \
  --stack-name speedsnake-deployment-role

aws cloudformation wait stack-delete-complete \
  --stack-name speedsnake-deployment-role
```

## Troubleshooting

### IAM Role Deployment Issues

**Error: "No credentials found"**
- Solution: Configure AWS credentials using AWS CLI or environment variables
- Verify: `aws sts get-caller-identity`

**Error: "Access Denied"**
- Solution: Ensure your AWS credentials have permissions to create IAM roles and CloudFormation stacks
- Required permissions: `iam:CreateRole`, `iam:PutRolePolicy`, `iam:TagRole`, `cloudformation:CreateStack`

**Error: "Role already exists"**
- Solution: The script will update the existing stack automatically
- If stuck, delete the stack and re-run: `aws cloudformation delete-stack --stack-name speedsnake-deployment-role`

### Infrastructure Deployment Issues

**Error: "User is not authorized to assume role"**
- Solution: Verify the deployment role ARN in GitHub secrets matches the created role
- Verify the central OIDC role has permission to assume roles with prefix `GithubActions-PR-thekhoo-*`
- Verify the deployment role has tag `allow-github-actions-access=true`

**Error: "Bucket already exists"**
- Solution: S3 bucket names are globally unique. The template uses account ID suffix to avoid conflicts
- If the bucket exists in another account, change the `BucketName` parameter

**Error: "Template validation failed"**
- Solution: Check template syntax using `aws cloudformation validate-template --template-body file://template.yml`
- Ensure YAML indentation is correct

### GitHub Actions Workflow Issues

**Error: "Could not assume role"**
- Solution: Verify all three GitHub secrets are configured correctly:
  - `AWS_OIDC_ROLE_ARN` - Central OIDC role ARN
  - `AWS_DEPLOY_ROLE_ARN` - Deployment role ARN
  - `AWS_REGION` - Target region
- Verify the central OIDC role trust policy allows GitHub OIDC federation

**Workflow doesn't trigger**
- Solution: Ensure changes to `infrastructure/template.yml` are pushed to `main` branch
- Check workflow file path: `.github/workflows/deploy-infrastructure.yml`
- Manually trigger via GitHub Actions UI (workflow_dispatch)

## Security Best Practices

1. **Least Privilege**: The deployment role only has permissions for `speedsnake-*` stacks and `speedsnake*` buckets
2. **Role Chaining**: Uses two-stage authentication (OIDC → Deployment role) for better security
3. **OIDC Authentication**: No long-lived AWS credentials stored in GitHub
4. **Tag-Based Access Control**: Central OIDC role checks for `allow-github-actions-access` tag before assuming
5. **Encrypted Storage**: S3 bucket uses server-side encryption (AES256)
6. **Block Public Access**: All public access is blocked on the S3 bucket
7. **Versioning**: S3 versioning enabled for data protection

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│           GitHub Actions Workflow                       │
│                                                          │
│  Step 1: Authenticate with AWS OIDC                     │
│  ├─> Use OIDC token                                     │
│  └─> Assume: Central OIDC Role                          │
│      (AWS_OIDC_ROLE_ARN)                                │
│                                                          │
│  Step 2: Assume deployment role                         │
│  ├─> Use credentials from Step 1                        │
│  ├─> Check: Role prefix = GithubActions-PR-thekhoo-*    │
│  ├─> Check: Tag allow-github-actions-access = true      │
│  └─> Assume: speedsnake-deploy role                     │
│      (AWS_DEPLOY_ROLE_ARN)                              │
│                                                          │
│  Step 3: Deploy CloudFormation                          │
│  ├─> Use credentials from Step 2                        │
│  └─> Create/Update: S3 bucket                           │
└─────────────────────────────────────────────────────────┘
```

## Future Enhancements

The following features are planned but not yet implemented:

1. **S3 Upload Integration** - Modify Python code to upload parquet files to S3
2. **Lifecycle Policies** - Add S3 lifecycle rules for data retention and transitions
3. **Cross-Region Replication** - Replicate data to secondary region for disaster recovery
4. **IAM Policies for Upload** - Create IAM user/role for application to upload data
5. **CloudWatch Alarms** - Monitor bucket size and upload failures
6. **S3 Event Notifications** - Trigger processing on new uploads (Lambda, SNS, SQS)
7. **Bucket Policies** - Fine-grained access control for different use cases
8. **CloudFormation Exports** - Export bucket name/ARN for other stacks to reference

## Support

For issues or questions:
- Check the [troubleshooting section](#troubleshooting) above
- Review CloudFormation stack events: `aws cloudformation describe-stack-events --stack-name speedsnake-infrastructure`
- Review GitHub Actions workflow logs in the repository's Actions tab
- Open an issue in the repository
