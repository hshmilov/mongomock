from test_helpers.machines import PROXY_IP, PROXY_PORT


client_details = [{
    # AWS EC2 Client Details
    "aws_access_key_id": "AKIAJOCJ5PGEAR6LNIFQ",
    "aws_secret_access_key": "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",
    "region_name": "us-east-2"
},
    {
    # AWS ECS Client Details
    "aws_access_key_id": "AKIAIBY62ONL7NKPY2ZA",
    "aws_secret_access_key": "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",
    "region_name": "us-east-2"
},
    {
    # AWS EKS Client Details
    "aws_access_key_id": "AKIAJNIRAK5MDDHPSLTQ",
    "aws_secret_access_key": "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",
    "region_name": "us-east-1"

}]


client_ec2_with_proxy = client_details[0].copy()
client_ecs_with_proxy = client_details[1].copy()
client_ec2_with_proxy['proxy'] = f"{PROXY_IP}:{PROXY_PORT}"
client_ecs_with_proxy['proxy'] = f"{PROXY_IP}:{PROXY_PORT}"

US_EAST_1_EKS_NODE_ID = 'i-0738869e8672dbea0'
SOME_DEVICE_ID = ['i-0ec91cae8a42be974', '17a679c2-105c-4d0f-90d7-8645ded69f58', US_EAST_1_EKS_NODE_ID]
