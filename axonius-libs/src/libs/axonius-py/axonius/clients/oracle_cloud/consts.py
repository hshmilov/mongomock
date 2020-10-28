from enum import Enum

ORACLE_CLOUD_DOMAIN = 'https://oraclecloud.com'
ORACLE_CLOUD_USER = 'user'
ORACLE_KEY_FILE = 'key_file'
ORACLE_FINGERPRINT = 'fingerprint'
ORACLE_TENANCY = 'tenancy'
ORACLE_REGION = 'region'
ORACLE_PRIVATE_KEY_FILE_PATH = 'oci_api_key.pem'
RULE_DIRECTION_INGRESS = 'INGRESS'
RULE_DIRECTION_EGRESS = 'EGRESS'
MAX_NUMBER_OF_DEVICES = 2000000
OCI_PROTOCOLS_MAP = {
    '1': 'ICMP',
    '6': 'TCP',
    '17': 'UDP',
    '58': 'ICMPv6'
}
CIS_API_KEY_ROTATION_DAYS = 90


class YieldMode(Enum):
    """
    Yield modes for oci.pagination methods
    """
    RAW = 'response'
    RESPONSE = 'response'  # Return the raw response
    MODEL = 'record'  # Use this to auto-parse the result's .data() into the model object
    RECORD = 'record'
    DEFAULT = 'response'

    def __str__(self):
        """ String representation of the value """
        return str(self.value)


class SecurityRuleOrigin(Enum):
    """
    Enum for "origin" field of Security Rule
    """
    SECLIST = 'Security List'
    NSG = 'NSG'

    @classmethod
    def values(cls):
        return list(x.value for x in cls)
