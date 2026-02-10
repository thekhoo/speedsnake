import boto3


def assume_role(role_arn: str, role_session_name: str = "default", region: str = "eu-west-2"):
    client = boto3.client("sts", region_name=region)
    res = client.assume_role(RoleArn=role_arn, RoleSessionName=role_session_name)

    creds = res["Credentials"]
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name=region,
    )
