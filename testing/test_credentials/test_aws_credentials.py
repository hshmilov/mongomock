from test_helpers.machines import PROXY_IP, PROXY_PORT

US_EAST_2_ECS_NODE_ID = '17a679c2-105c-4d0f-90d7-8645ded69f58'
US_EAST_2_EC2_BUILDS_MACHINE_ID = 'i-0ec91cae8a42be974'
US_EAST_1_EKS_NODE_ID = 'i-0738869e8672dbea0'

# client details with ids
client_details = [
    ({
        "aws_access_key_id": "AKIAJOCJ5PGEAR6LNIFQ",
        "aws_secret_access_key": "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",
        "region_name": "us-east-2"
    }, US_EAST_2_EC2_BUILDS_MACHINE_ID),
    # currently unavailable
    # ({
    #     "aws_access_key_id": "AKIAIBY62ONL7NKPY2ZA",
    #     "aws_secret_access_key": "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",
    #     "region_name": "us-east-2"
    # }, US_EAST_2_ECS_NODE_ID)
    ({
        "aws_access_key_id": "AKIAJNIRAK5MDDHPSLTQ",
        "aws_secret_access_key": "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",
        "region_name": "us-east-1"
    }, US_EAST_1_EKS_NODE_ID)
]

client_ec2_with_proxy = client_details[0][0].copy()
client_ecs_with_proxy = client_details[1][0].copy()
client_ec2_with_proxy['proxy'] = f"{PROXY_IP}:{PROXY_PORT}"
client_ecs_with_proxy['proxy'] = f"{PROXY_IP}:{PROXY_PORT}"
