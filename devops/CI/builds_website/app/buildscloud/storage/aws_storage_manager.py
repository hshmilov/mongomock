import boto3


class AWSStorageManager:
    def __init__(self, credentials: dict):
        super().__init__()
        self.s3_client = boto3.client('s3', **credentials)
