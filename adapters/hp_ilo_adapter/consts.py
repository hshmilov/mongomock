MAX_NUMBER_OF_DEVICES = 2000000

DEFAULT_TOKEN_EXPIRATION = 1800

API_AUTH_SUFFIX = 'redfish/v1/SessionService/Sessions/'
SYSTEM_API_SUFFIX = 'redfish/v1/Systems'

MAC_IPV4_REGEX = 'MAC\(([^,]+?),[^/]+?/IPv4\(([^)]+?)\)'  # pylint: disable=anomalous-backslash-in-string
MAC_IPV6_REGEX = 'MAC\(([^,]+?),[^/]+?/IPv6\(([^)]+?)\)'  # pylint: disable=anomalous-backslash-in-string
