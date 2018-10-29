from test_helpers.machines import PROXY_IP, PROXY_PORT
from test_helpers.file_mock_credentials import FileForCredentialsMock

US_EAST_1_ECS_FARGATE_CONTAINER_ID = 'arn:aws:ecs:us-east-1:405773942477:container/dd52300c-ce17-4206-99da-a343a51bfafb'
US_EAST_2_EC2_BUILDS_MACHINE_ID = 'i-0ec91cae8a42be974'
US_EAST_1_EKS_NODE_ID = 'i-02380686d4ee7e12e'
US_EAST_1_TEST_1_AWS_DEV_2_ROLE_TEST = 'i-00203ff84d4b860e5'
US_EAST_1_TEST_1_AWS_DEV_3_ROLE_TEST = 'i-047dbdf6219f95e45'

# The following IAM account is:
# arn:aws:iam::405773942477:user/Axonius-Readonly
# ec2:Describe*,ecs:Describe*,eks:Describe*,eks:List*,ecs:List*,ec2:Get*
# and also sts:AssumeRole for specific ARNs
EC2_ECS_EKS_READONLY_ACCESS_KEY_ID = 'AKIAIQIF42V5LZG4EARQ'
EC2_ECS_EKS_READONLY_SECRET_ACCESS_KEY = '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'

# client details with ids
client_details = [
    ({
        "aws_access_key_id": EC2_ECS_EKS_READONLY_ACCESS_KEY_ID,
        "aws_secret_access_key": EC2_ECS_EKS_READONLY_SECRET_ACCESS_KEY,
        "region_name": "us-east-2",
        'get_all_regions': False
    }, [US_EAST_2_EC2_BUILDS_MACHINE_ID]),
    ({
        "aws_access_key_id": EC2_ECS_EKS_READONLY_ACCESS_KEY_ID,
        "aws_secret_access_key": EC2_ECS_EKS_READONLY_SECRET_ACCESS_KEY,
        "region_name": "us-east-1",
        'get_all_regions': False
    }, [US_EAST_1_ECS_FARGATE_CONTAINER_ID]),
    ({
        "aws_access_key_id": EC2_ECS_EKS_READONLY_ACCESS_KEY_ID,
        "aws_secret_access_key": EC2_ECS_EKS_READONLY_SECRET_ACCESS_KEY,
        "region_name": "us-east-1",
        'get_all_regions': False,
        'roles_to_assume_list': FileForCredentialsMock(
            'file.txt',
            'arn:aws:iam::817364327683:role/AxoniusDevRole, arn:aws:iam::802876684602:role/Axonius-Readonly-Role'
        )
    }, [US_EAST_1_EKS_NODE_ID, US_EAST_1_TEST_1_AWS_DEV_2_ROLE_TEST, US_EAST_1_TEST_1_AWS_DEV_3_ROLE_TEST])
]

client_ec2_with_proxy = client_details[0][0].copy()
client_ecs_with_proxy = client_details[1][0].copy()
client_ec2_with_proxy['proxy'] = f"{PROXY_IP}:{PROXY_PORT}"
client_ecs_with_proxy['proxy'] = f"{PROXY_IP}:{PROXY_PORT}"
