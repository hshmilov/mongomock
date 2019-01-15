#!/usr/local/bin/python3
"""
The following file queries Axonius to get devices by their asset name or host name.
"""
import json

from axoniussdk import argument_parser
from axoniussdk.client import RESTClient

from get_devices_by_filter import get_devices_by_filter


__author__ = 'Axonius, Inc'

# A query that searches for devices with hostname or asset name that includes a specific string
FILTER = 'specific_data.data.hostname == regex("{0}", "i") or specific_data.data.name == regex("{0}", "i")'


class ArgumentParser(argument_parser.ArgumentParser):
    """ Argumentparser for the script """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_argument('name', help='name to filter')
        self.description = \
            '''Example:
  %(prog)s pc-name -x https://axonius.local --username admin -p password1 --no-verify-ssl'
  %(prog)s pc-name -x https://axonius.local --api-key xxxx --api-secret yyyy'''


def get_devices_by_name(client, name):
    yield from get_devices_by_filter(client, FILTER.format(name), False)


def main():
    args = ArgumentParser().parse_args()
    client = RESTClient(args.axonius_url,
                        auth=args.auth,
                        headers=args.headers,
                        verify=not args.no_verify_ssl)

    for device in get_devices_by_name(client, args.name):
        print(json.dumps(device, indent=6))

    return 0


if __name__ == '__main__':
    main()
