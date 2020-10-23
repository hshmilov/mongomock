from enum import Enum


class CloudInstances(Enum):
    AWS = 'AWS'
    AZURE = 'Azure'
    GCP = 'gcloud'
    SECURITYGROUP = 'SecurityGroup'


DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 2000000

DEFAULT_HOURS_FILTER = 7 * 24  # 7 Days in hours
TOKEN_VALID_TIME = 600  # API docs - 10 minutes

URL_API_FORMAT = '{}://{}'

QUERIES = [('config where api.name = \'aws-ec2-describe-instances\'', CloudInstances.AWS.value),
           ('config where cloud.type = \'azure\' AND api.name = \'azure-vm-list\'', CloudInstances.AZURE.value),
           ('config where api.name = \'gcloud-compute-instances-list\'', CloudInstances.GCP.value)]

BODY_PARAMS = {
    'filters': [
        {
            'name': 'resource.type',
            'value': 'Azure Security Group',
            'operator': '='
        },
        {
            'name': 'resource.type',
            'value': 'ECS Security Group',
            'operator': '='
        },
        {
            'name': 'resource.type',
            'value': 'Amazon VPC Security Group',
            'operator': '='
        }
    ]
}
