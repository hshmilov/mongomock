
from test_helpers.machines import PROXY_IP, PROXY_PORT

client_details = {
    "aws_access_key_id": "AKIAJOCJ5PGEAR6LNIFQ",
    "aws_secret_access_key": "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",
    "region_name": "us-east-2"
}

client_with_proxy = client_details.copy()
client_with_proxy['proxy'] = f"{PROXY_IP}:{PROXY_PORT}"

SOME_DEVICE_ID = 'i-0ec91cae8a42be974'
