# SpeedSnake Infrastructure

This directory contains CloudFormation templates and deployment scripts for SpeedSnake's AWS infrastructure.

## Overview

The infrastructure uses a **fully automated** two-stage CloudFormation deployment system via GitHub Actions:

1. **IAM Deployment Role** (`deployment-role.yml`) - Automatically creates a repository-specific deployment role
2. **Infrastructure Resources** (`template.yml`) - Creates the S3 bucket for storing speedtest results

The deployment uses GitHub Actions with OIDC authentication and multi-stage role chaining:
```
GitHub Actions → OIDC Entry Role → Create Deployment Role → Deploy deployment-role.yml (creates github-actions-{owner}-{repo})
                                  → OIDC Entry Role → github-actions-{owner}-{repo} → Deploy template.yml
```

**Key Feature**: The deployment role is created automatically by the GitHub Actions workflow - no manual script execution required!

## Files

- **`deployment-role.yml`** - CloudFormation template for the IAM deployment role
- **`template.yml`** - CloudFormation template for S3 bucket infrastructure
- **`update-deployment-role.py`** - Python script to deploy/update the IAM role locally (optional, for manual deployment)
- **`README.md`** - This documentation file

## Prerequisites

### AWS Setup

The following IAM roles must already exist in your AWS account:

1. **OIDC Entry Role** (`github-actions-oidc-entry-role`)
   - Purpose: Entry point for GitHub Actions runners
   - Allows GitHub OIDC provider to assume this role
   - Can assume other roles for specific operations

2. **Create Deployment Role** (`github-actions-create-deployment-role`)
   - Purpose: Universal role that can create repository-specific deployment roles
   - Trust policy: Can be assumed by `github-actions-oidc-entry-role`
   - Permissions: Create/update IAM roles and CloudFormation stacks for deployment roles

These are **one-time setup** roles that are shared across all repositories in your organization.

### GitHub Secrets

The following secrets must be configured in the GitHub repository (Settings → Secrets and variables → Actions):

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `AWS_OIDC_ENTRY_ROLE_ARN` | ARN of the OIDC entry role | `arn:aws:iam::123456789012:role/github-actions-oidc-entry-role` |
| `AWS_CREATE_DEPLOYMENT_ROLE_ARN` | ARN of the create deployment role | `arn:aws:iam::123456789012:role/github-actions-create-deployment-role` |
| `AWS_REGION` | Target AWS region for deployments | `us-east-1` |

**Note**: The repository-specific deployment role (`github-actions-{owner}-{repo}`) is created automatically by the workflow - no secret needed!

## Deployment Order

### Setup: Configure GitHub Secrets (One-Time)

Add the required secrets to your GitHub repository (Settings → Secrets and variables → Actions):

1. `AWS_OIDC_ENTRY_ROLE_ARN` - ARN of your OIDC entry role
2. `AWS_CREATE_DEPLOYMENT_ROLE_ARN` - ARN of your create deployment role
3. `AWS_REGION` - Target AWS region (e.g., `us-east-1`)

### Automated Deployment (No Manual Steps Required!)

Once secrets are configured, **everything happens automatically** via GitHub Actions:

**Automatic deployment triggers:**
- Push to `main` branch when `infrastructure/deployment-role.yml` OR `infrastructure/template.yml` changes
- Manual trigger via GitHub Actions UI (workflow_dispatch)

**The workflow automatically:**

**Stage 1: Deploy Deployment Role** (if `deployment-role.yml` changed)
1. Checks which files changed
2. If `deployment-role.yml` changed:
   - Assumes `github-actions-oidc-entry-role`
   - Then assumes `github-actions-create-deployment-role`
   - Deploys CloudFormation stack to create `github-actions-{owner}-{repo}` role
   - Outputs the role ARN

**Stage 2: Deploy Infrastructure** (if `template.yml` changed)
1. Assumes `github-actions-oidc-entry-role`
2. Constructs deployment role ARN: `arn:aws:iam::{account-id}:role/github-actions-{owner}-{repo}`
3. Assumes the repository-specific deployment role
4. Validates and deploys the S3 bucket infrastructure
5. Displays stack outputs (bucket name, ARN, region)

**Result**: Both the deployment role and infrastructure are created/updated automatically without any manual intervention!

## Manual Deployment (Advanced/Optional)

> **Note**: Manual deployment is optional. The GitHub Actions workflow handles everything automatically. Use manual deployment only for testing or troubleshooting.

### Deploy IAM Role Manually with AWS CLI

```bash
aws cloudformation deploy \
  --stack-name speedsnake-deployment-role \
  --template-file deployment-role.yml \
  --parameter-overrides \
    GitHubOrg=thekhoo \
    GitHubRepo=speedsnake \
    CreateDeploymentRoleArn=arn:aws:iam::123456789012:role/github-actions-create-deployment-role \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# Get role ARN from stack outputs
aws cloudformation describe-stacks \
  --stack-name speedsnake-deployment-role \
  --query 'Stacks[0].Outputs[?OutputKey==`RoleArn`].OutputValue' \
  --output text

# Result: arn:aws:iam::123456789012:role/github-actions-thekhoo-speedsnake
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

**Role Name:** `github-actions-{owner}-{repo}` (e.g., `github-actions-thekhoo-speedsnake`)

**Trust Policy:** Allows assumption by `github-actions-create-deployment-role`

**Permissions:**
- CloudFormation: Full access to stacks with `speedsnake-*` prefix
- S3: Full access to buckets with `speedsnake*` prefix
- S3: List all buckets (for validation)

**Tags:**
- `Project=speedsnake`
- `ManagedBy=CloudFormation`
- `Repository={owner}/{repo}`

**Created By:** GitHub Actions workflow automatically when `deployment-role.yml` is pushed to `main`

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
- Solution: Verify GitHub secrets are configured correctly:
  - `AWS_OIDC_ENTRY_ROLE_ARN` - Entry point role ARN
  - `AWS_CREATE_DEPLOYMENT_ROLE_ARN` - Create deployment role ARN
  - `AWS_REGION` - Target AWS region
- Verify the OIDC entry role can assume the create deployment role
- Verify the create deployment role can create IAM roles
- Verify the deployment role exists (it's created automatically on first run)

**Error: "Bucket already exists"**
- Solution: S3 bucket names are globally unique. The template uses account ID suffix to avoid conflicts
- If the bucket exists in another account, change the `BucketName` parameter

**Error: "Template validation failed"**
- Solution: Check template syntax using `aws cloudformation validate-template --template-body file://template.yml`
- Ensure YAML indentation is correct

### GitHub Actions Workflow Issues

**Error: "Could not assume role"**
- Solution: Verify all three GitHub secrets are configured correctly:
  - `AWS_OIDC_ENTRY_ROLE_ARN` - OIDC entry role ARN
  - `AWS_CREATE_DEPLOYMENT_ROLE_ARN` - Create deployment role ARN
  - `AWS_REGION` - Target region
- Verify the OIDC entry role trust policy allows GitHub OIDC federation
- Check the CloudFormation stack events for detailed error messages

**Workflow doesn't trigger**
- Solution: Ensure changes to `infrastructure/deployment-role.yml` or `infrastructure/template.yml` are pushed to `main` branch
- Check workflow file path: `.github/workflows/deploy-infrastructure.yml`
- Manually trigger via GitHub Actions UI (workflow_dispatch)
- Review the workflow paths filter in the workflow file

## Security Best Practices

1. **Least Privilege**: The deployment role only has permissions for `speedsnake-*` stacks and `speedsnake*` buckets
2. **Multi-Stage Role Chaining**: Uses three-stage authentication (OIDC Entry → Create Deployment → Repository Deployment) for enhanced security
3. **OIDC Authentication**: No long-lived AWS credentials stored in GitHub
4. **Dynamic Role ARN Construction**: Deployment role ARN is constructed at runtime from repository owner and name
5. **Automated Role Creation**: Deployment roles are created by a universal `create-deployment-role`, ensuring consistent permissions
6. **Encrypted Storage**: S3 bucket uses server-side encryption (AES256)
7. **Block Public Access**: All public access is blocked on the S3 bucket
8. **Versioning**: S3 versioning enabled for data protection

## Architecture Diagram

### Stage 1: Deploy Deployment Role (if deployment-role.yml changed)

```
┌─────────────────────────────────────────────────────────┐
│      GitHub Actions: Deploy Deployment Role             │
│                                                          │
│  Step 1: Authenticate with OIDC                         │
│  ├─> Use OIDC token from GitHub                         │
│  └─> Assume: github-actions-oidc-entry-role             │
│      (AWS_OIDC_ENTRY_ROLE_ARN)                          │
│                                                          │
│  Step 2: Assume create deployment role                  │
│  ├─> Use credentials from Step 1 (role chaining)        │
│  └─> Assume: github-actions-create-deployment-role      │
│      (AWS_CREATE_DEPLOYMENT_ROLE_ARN)                   │
│                                                          │
│  Step 3: Deploy deployment role CloudFormation          │
│  ├─> Use credentials from Step 2                        │
│  ├─> Deploy: deployment-role.yml                        │
│  └─> Creates: github-actions-{owner}-{repo}             │
└─────────────────────────────────────────────────────────┘
```

### Stage 2: Deploy Infrastructure (if template.yml changed)

```
┌─────────────────────────────────────────────────────────┐
│      GitHub Actions: Deploy Infrastructure              │
│                                                          │
│  Step 1: Authenticate with OIDC                         │
│  ├─> Use OIDC token from GitHub                         │
│  └─> Assume: github-actions-oidc-entry-role             │
│      (AWS_OIDC_ENTRY_ROLE_ARN)                          │
│                                                          │
│  Step 2: Assume repository deployment role              │
│  ├─> Use credentials from Step 1 (role chaining)        │
│  ├─> Construct ARN dynamically from repo owner/name     │
│  └─> Assume: github-actions-{owner}-{repo}              │
│      (e.g., github-actions-thekhoo-speedsnake)          │
│                                                          │
│  Step 3: Deploy infrastructure CloudFormation           │
│  ├─> Use credentials from Step 2                        │
│  ├─> Deploy: template.yml                               │
│  └─> Creates: S3 bucket                                 │
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
