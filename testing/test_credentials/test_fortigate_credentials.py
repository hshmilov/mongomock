# These credentials are for our very own fortigate router.
# Readonly credentials only for System Configuration created especially for the adapter and
# The dhcp_lease time is a week in seconds (as defaulted in our router).
# The ssl cert of our router is not signed so verify_ssl is False.
client_details = {
    'host': '192.168.10.1',
    'port': '443',
    'username': 'axonius-readonly',
    'password': 'Password2',
    'verify_ssl': False,
    'dhcp_lease_time': 604800
}

SOME_DEVICE_ID = 'a4:e9:75:78:fc:c3'.upper()

FETCHED_DEVICE_EXAMPLE = {
    'ip': '192.168.254.4',
    'mac': 'a4:e9:75:78:fc:c3'.upper(),
    'hostname': 'iPad',
    'expire': 'Sun Feb 11 20:46:13 2018',
    'expire_time': 1518374773,
    'status': 'leased',
    'interface': 'guests',
    'type': 'ipv4',
    'reserved': False
}
