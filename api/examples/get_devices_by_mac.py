#!/usr/bin/env python3
"""
The following file queries Axonius to get devices by their mac
"""
import json

from axoniussdk import argument_parser
from axoniussdk.client import RESTClient

from get_devices_by_filter import get_devices_by_filter

__author__ = 'Axonius, Inc'

# A query that searches for devices of which mac address contains the param.
# For example, if the param would be 03:00:ec all devices with mac that contains this string will return.
FILTER = 'specific_data.data.network_interfaces.mac == regex("{0}", "i")'


class ArgumentParser(argument_parser.ArgumentParser):
    """ Argumentparser for the script """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_argument('mac', help='mac to filter')
        self.description = \
            '''Example:
  %(prog)s 00:11:22:33:44:55 -x https://axonius --username admin -p password1 --no-verify-ssl
  %(prog)s 00:11:22:33:44:55 -x https://axonius --api-key xxxx --api-secret yyyy'''


def get_devices_by_mac(client, mac):
    yield from get_devices_by_filter(client, FILTER.format(mac), False)


def main():
    args = ArgumentParser().parse_args()
    client = RESTClient(args.axonius_url,
                        auth=args.auth,
                        headers=args.headers,
                        verify=not args.no_verify_ssl)

    for device in get_devices_by_mac(client, args.mac):
        print(json.dumps(device, indent=6))

    return 0


if __name__ == '__main__':
    main()
