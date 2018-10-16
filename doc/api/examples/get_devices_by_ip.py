#!/usr/local/bin/python3
"""
The following file queries Axonius to get devices by their ip
"""
import sys
import json

from get_devices_by_filter import get_devices_by_filter

__author__ = 'Axonius, Inc'

# A query that searches for devices with a specific ip. Note: this must be the full ip and not a subset of it.
FILTER = 'specific_data.data.network_interfaces.ips == "{0}"'


# pylint: disable=E0632
def main():
    try:
        _, axonius_addr, api_key, api_secret, param = sys.argv
    except Exception:
        sys.stderr.write('Usage: {0} [Axonius address] [API key] [API secret] [ip]'.format(sys.argv[0]))
        return -1

    for device in get_devices_by_filter(axonius_addr, api_key, api_secret, FILTER.format(param), False):
        print(json.dumps(device, indent=6))

    return 0


if __name__ == '__main__':
    sys.exit(main())
