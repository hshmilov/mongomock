from test_helpers.machines import PROXY_IP, PROXY_PORT

US_EAST_1_ECS_FARGATE_NODE_ID = 'arn:aws:ecs:us-east-1:405773942477:task/75fb42ed-565b-44f0-b2dd-1f8cc53463ac'
US_EAST_2_EC2_BUILDS_MACHINE_ID = 'i-0ec91cae8a42be974'
US_EAST_1_EKS_NODE_ID = 'i-02380686d4ee7e12e'

# The following IAM account is:
# arn:aws:iam::405773942477:user/Axonius-Readonly
# ec2:Describe*,ecs:Describe*,eks:Describe*,eks:List*,ecs:List*,ec2:Get*
EC2_ECS_EKS_READONLY_ACCESS_KEY_ID = 'AKIAIQIF42V5LZG4EARQ'
EC2_ECS_EKS_READONLY_SECRET_ACCESS_KEY = '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'

# client details with ids
client_details = [
    ({
        "aws_access_key_id": EC2_ECS_EKS_READONLY_ACCESS_KEY_ID,
        "aws_secret_access_key": EC2_ECS_EKS_READONLY_SECRET_ACCESS_KEY,
        "region_name": "us-east-2",
        'get_all_regions': False
    }, US_EAST_2_EC2_BUILDS_MACHINE_ID),
    ({
        "aws_access_key_id": EC2_ECS_EKS_READONLY_ACCESS_KEY_ID,
        "aws_secret_access_key": EC2_ECS_EKS_READONLY_SECRET_ACCESS_KEY,
        "region_name": "us-east-1",
        'get_all_regions': False
    }, US_EAST_1_ECS_FARGATE_NODE_ID),
    ({
        "aws_access_key_id": EC2_ECS_EKS_READONLY_ACCESS_KEY_ID,
        "aws_secret_access_key": EC2_ECS_EKS_READONLY_SECRET_ACCESS_KEY,
        "region_name": "us-east-1",
        'get_all_regions': False
    }, US_EAST_1_EKS_NODE_ID)
]

client_ec2_with_proxy = client_details[0][0].copy()
client_ecs_with_proxy = client_details[1][0].copy()
client_ec2_with_proxy['proxy'] = f"{PROXY_IP}:{PROXY_PORT}"
client_ecs_with_proxy['proxy'] = f"{PROXY_IP}:{PROXY_PORT}"
