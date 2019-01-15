#!/usr/local/bin/python3
"""
The following file queries Axonius to get devices by their ip
"""

import json

from axoniussdk import argument_parser
from axoniussdk.client import RESTClient

from get_devices_by_filter import get_devices_by_filter

__author__ = 'Axonius, Inc'

# A query that searches for devices with a specific ip. Note: this must be the full ip and not a subset of it.
FILTER = 'specific_data.data.network_interfaces.ips == "{0}"'


class ArgumentParser(argument_parser.ArgumentParser):
    """ Argumentparser for the script """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_argument('ip', help='ip to filter')
        self.description = \
            '''Example:
  %(prog)s 192.168.1.1 -x https://axonius.local --username admin -p password1 --no-verify-ssl
  %(prog)s 192.168.1.2 -x https://axonius.local --api-key xxxx --api-secret yyyy'''


def get_devices_by_ip(client, ip):
    yield from get_devices_by_filter(client, FILTER.format(ip), False)


def main():
    args = ArgumentParser().parse_args()
    client = RESTClient(args.axonius_url,
                        auth=args.auth,
                        headers=args.headers,
                        verify=not args.no_verify_ssl)

    for device in get_devices_by_ip(client, args.ip):
        print(json.dumps(device, indent=6))

    return 0


if __name__ == '__main__':
    main()
