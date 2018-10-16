#!/usr/local/bin/python3
"""
The following file queries Axonius to get devices by their asset name or host name.
"""
import sys
import json

from get_devices_by_filter import get_devices_by_filter

__author__ = 'Axonius, Inc'

# A query that searches for devices with hostname or asset name that includes a specific string
FILTER = 'specific_data.data.hostname == regex("{0}", "i") or specific_data.data.name == regex("{0}", "i")'


# pylint: disable=E0632
def main():
    try:
        _, axonius_addr, api_key, api_secret, param = sys.argv
    except Exception:
        sys.stderr.write('Usage: {0} [Axonius address] [API key] [API secret] [asset or host name]'.format(sys.argv[0]))
        return -1

    for device in get_devices_by_filter(axonius_addr, api_key, api_secret, FILTER.format(param), False):
        print(json.dumps(device, indent=6))

    return 0


if __name__ == '__main__':
    sys.exit(main())
