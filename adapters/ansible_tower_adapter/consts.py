from enum import Enum, auto

DEVICE_PER_PAGE = 100
MAX_NUMBER_OF_DEVICES = 1000000

API_HOST_URI = 'hosts'

ANSIBLE_DATA_VARBS_STATIC_MAP = [
    'ec2_state_code',
    'ec2_block_devices',
    'datastore',
    'resourcepool',
    'summary',
    'capability',
    'guest',
    'runtime',
    'config'

]

ANSIBLE_IP_ADDRESS_DATA_VARBS = [

    'ec2_private_ip_address',
    'ec2_ip_address',
    'ansible_host',
    'gce_private_ip',
    'gce_public_ip'
    'public_ip',
    'private_ip',
    'ipaddress'

]

ANSIBLE_ASSET_NAME_DATA_VARBS = [

    'ec2_public_dns_name',
    'ec2_ip_address',
    'ansible_host',
    'gce_private_ip',
    'gce_public_ip'


]


class AnsibelTowerAuthMethod(Enum):
    BasicAuth = auto()
    OAuthV2 = auto()


class AnsibelTowerInstanceType(Enum):
    host = auto()
