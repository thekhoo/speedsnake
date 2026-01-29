#!/usr/bin/env python3
"""
Deploy or update the IAM deployment role for SpeedSnake infrastructure.

This script creates or updates a CloudFormation stack that provisions
the IAM role used by GitHub Actions to deploy infrastructure.

Usage:
    python update-deployment-role.py --region us-east-1 --central-role-arn arn:aws:iam::123456789012:role/CentralOIDCRole
    python update-deployment-role.py --region us-east-1 --central-role-arn arn:aws:iam::123456789012:role/CentralOIDCRole --dry-run

Requirements:
    - boto3 library (install with: pip install boto3 or uv pip install boto3)
    - AWS credentials configured (AWS CLI profile or environment variables)
    - Permissions to create/update IAM roles and CloudFormation stacks
"""

import argparse
import sys
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound
except ImportError:
    print("Error: boto3 library not found. Install it with: pip install boto3")
    sys.exit(1)


STACK_NAME = "speedsnake-deployment-role"
TEMPLATE_FILE = "deployment-role.yml"


def validate_template(cfn_client, template_body):
    """Validate the CloudFormation template."""
    try:
        print("Validating CloudFormation template...")
        cfn_client.validate_template(TemplateBody=template_body)
        print("✓ Template is valid")
        return True
    except ClientError as e:
        print(f"✗ Template validation failed: {e.response['Error']['Message']}")
        return False


def stack_exists(cfn_client, stack_name):
    """Check if a CloudFormation stack exists."""
    try:
        cfn_client.describe_stacks(StackName=stack_name)
        return True
    except ClientError as e:
        if "does not exist" in str(e):
            return False
        raise


def deploy_stack(cfn_client, stack_name, template_body, parameters, dry_run=False):
    """Deploy or update the CloudFormation stack."""
    exists = stack_exists(cfn_client, stack_name)

    if dry_run:
        action = "update" if exists else "create"
        print(f"DRY RUN: Would {action} stack '{stack_name}'")
        print(f"Parameters: {parameters}")
        return None

    try:
        if exists:
            print(f"Updating existing stack: {stack_name}")
            response = cfn_client.update_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Parameters=parameters,
                Capabilities=["CAPABILITY_NAMED_IAM"],
                Tags=[
                    {"Key": "Project", "Value": "speedsnake"},
                    {"Key": "ManagedBy", "Value": "update-deployment-role.py"},
                ],
            )
            print(f"Stack update initiated. StackId: {response['StackId']}")
            return "UPDATE_IN_PROGRESS"
        else:
            print(f"Creating new stack: {stack_name}")
            response = cfn_client.create_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Parameters=parameters,
                Capabilities=["CAPABILITY_NAMED_IAM"],
                Tags=[
                    {"Key": "Project", "Value": "speedsnake"},
                    {"Key": "ManagedBy", "Value": "update-deployment-role.py"},
                ],
            )
            print(f"Stack creation initiated. StackId: {response['StackId']}")
            return "CREATE_IN_PROGRESS"
    except ClientError as e:
        error_message = e.response["Error"]["Message"]
        if "No updates are to be performed" in error_message:
            print("✓ No changes detected - stack is already up to date")
            return "NO_CHANGES"
        else:
            print(f"✗ Stack operation failed: {error_message}")
            raise


def wait_for_stack(cfn_client, stack_name, operation):
    """Wait for stack operation to complete."""
    if operation == "NO_CHANGES":
        return True

    print(f"Waiting for stack operation to complete...")
    waiter_name = "stack_create_complete" if operation == "CREATE_IN_PROGRESS" else "stack_update_complete"

    try:
        waiter = cfn_client.get_waiter(waiter_name)
        waiter.wait(StackName=stack_name, WaiterConfig={"Delay": 5, "MaxAttempts": 120})
        print("✓ Stack operation completed successfully")
        return True
    except Exception as e:
        print(f"✗ Stack operation failed: {e}")
        return False


def get_stack_outputs(cfn_client, stack_name):
    """Get outputs from the CloudFormation stack."""
    try:
        response = cfn_client.describe_stacks(StackName=stack_name)
        stack = response["Stacks"][0]
        outputs = {output["OutputKey"]: output["OutputValue"] for output in stack.get("Outputs", [])}
        return outputs
    except ClientError as e:
        print(f"Error getting stack outputs: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser(
        description="Deploy or update the IAM deployment role for SpeedSnake",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy the IAM role
  python update-deployment-role.py --region us-east-1 --central-role-arn arn:aws:iam::123456789012:role/CentralOIDCRole

  # Dry run (validate only, no deployment)
  python update-deployment-role.py --region us-east-1 --central-role-arn arn:aws:iam::123456789012:role/CentralOIDCRole --dry-run

  # Specify GitHub org and repo
  python update-deployment-role.py --region us-east-1 --central-role-arn arn:aws:iam::123456789012:role/CentralOIDCRole --github-org myorg --github-repo myrepo
        """,
    )

    parser.add_argument("--region", required=True, help="AWS region (e.g., us-east-1)")

    parser.add_argument(
        "--central-role-arn",
        required=True,
        help="ARN of the central OIDC role that will assume the deployment role",
    )

    parser.add_argument("--github-org", default="thekhoo", help="GitHub organization name (default: thekhoo)")

    parser.add_argument("--github-repo", default="speedsnake", help="GitHub repository name (default: speedsnake)")

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate template without deploying",
    )

    parser.add_argument("--profile", help="AWS CLI profile to use (optional)")

    args = parser.parse_args()

    # Find template file
    script_dir = Path(__file__).parent
    template_path = script_dir / TEMPLATE_FILE

    if not template_path.exists():
        print(f"Error: Template file not found: {template_path}")
        sys.exit(1)

    # Read template
    with open(template_path, "r") as f:
        template_body = f.read()

    # Initialize AWS client
    try:
        session_kwargs = {"region_name": args.region}
        if args.profile:
            session_kwargs["profile_name"] = args.profile

        session = boto3.Session(**session_kwargs)
        cfn_client = session.client("cloudformation")

        # Verify credentials
        sts_client = session.client("sts")
        identity = sts_client.get_caller_identity()
        print(f"Using AWS Account: {identity['Account']}")
        print(f"Using AWS Region: {args.region}")
        if args.profile:
            print(f"Using AWS Profile: {args.profile}")
        print()

    except ProfileNotFound:
        print(f"Error: AWS profile '{args.profile}' not found")
        sys.exit(1)
    except NoCredentialsError:
        print("Error: No AWS credentials found. Configure credentials using AWS CLI or environment variables.")
        sys.exit(1)
    except Exception as e:
        print(f"Error initializing AWS client: {e}")
        sys.exit(1)

    # Validate template
    if not validate_template(cfn_client, template_body):
        sys.exit(1)

    # Prepare parameters
    parameters = [
        {"ParameterKey": "GitHubOrg", "ParameterValue": args.github_org},
        {"ParameterKey": "GitHubRepo", "ParameterValue": args.github_repo},
        {"ParameterKey": "CentralOIDCRoleArn", "ParameterValue": args.central_role_arn},
    ]

    # Deploy stack
    operation = deploy_stack(cfn_client, STACK_NAME, template_body, parameters, dry_run=args.dry_run)

    if args.dry_run:
        print("\nDry run completed. No changes were made.")
        sys.exit(0)

    if operation is None:
        sys.exit(1)

    # Wait for completion
    if not wait_for_stack(cfn_client, STACK_NAME, operation):
        sys.exit(1)

    # Display outputs
    outputs = get_stack_outputs(cfn_client, STACK_NAME)
    if outputs:
        print("\n" + "=" * 70)
        print("Stack Outputs:")
        print("=" * 70)
        for key, value in outputs.items():
            print(f"{key}: {value}")
        print("=" * 70)

        if "RoleArn" in outputs:
            print("\nNext steps:")
            print("1. Add this role ARN to GitHub repository secrets:")
            print(f"   Secret name: AWS_DEPLOY_ROLE_ARN")
            print(f"   Secret value: {outputs['RoleArn']}")
            print("\n2. Ensure these secrets are also configured:")
            print("   - AWS_OIDC_ROLE_ARN: ARN of the central OIDC role")
            print("   - AWS_REGION: Target AWS region (e.g., us-east-1)")
            print("\n3. Push infrastructure changes to trigger automatic deployment")

    print("\n✓ Deployment completed successfully")


if __name__ == "__main__":
    main()
