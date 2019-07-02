#!/usr/local/bin/python3
"""
The following file contains a function to get devices from Axonius by specific filter.
"""
import json

from axoniussdk import argument_parser
from axoniussdk.client import RESTClient

__author__ = 'Axonius, Inc'

# How many devices to query per request
PAGING_LIMIT = 50


class ArgumentParser(argument_parser.ArgumentParser):
    """ Argumentparser for the script """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_argument('filter')
        self.add_argument('-a', '--all-info',
                          default=False,
                          action='store_true',
                          help='Fetch all Fields')
        self.description = \
            '''Example:
  %(prog)s 'specific_data.data.hostname == "a"' -x https://axonius.local --username admin -p password1 --no-verify-ssl
  %(prog)s 'specific_data.data.hostname == "a"' 192.168.1.2 -x https://axonius.local --api-key xxxx --api-secret yyyy'''


def get_devices_by_filter(client: RESTClient, api_filter: str, all_info: bool = False):
    """
    Queries Axonius API about specific devices.
    :param RESTClient client: Axnoius RESTClient
    :param str api_filter: an Axonius filter (the one that appears in the gui after using the query builder)
    :param bool all_info: if True, returns all info about the device. else, returns only basic info.
    :return:
    """
    fields = None
    if all_info:
        fields = ','.join(['specific_data.data'])
    else:
        # Ask the API to return only specific fields
        fields = ','.join([
            'specific_data.data.hostname',
            'specific_data.data.name',
            'specific_data.data.network_interfaces.mac',
            'specific_data.data.network_interfaces.ips',
        ])
    status_code, first_page = client.get_devices(skip=0, limit=PAGING_LIMIT,
                                                 filter_=api_filter, fields=fields)
    if status_code != 200:
        raise RuntimeError(f'Failed to get devices {status_code} {first_page}')

    yield from first_page['assets']
    total_devices = first_page['page']['totalResources']

    count = PAGING_LIMIT
    while count < total_devices:
        status_code, resp = client.get_devices(skip=count, limit=PAGING_LIMIT)
        yield from resp['assets']
        count += PAGING_LIMIT


def main():
    args = ArgumentParser().parse_args()
    client = RESTClient(args.axonius_url,
                        auth=args.auth,
                        headers=args.headers,
                        verify=not args.no_verify_ssl)

    for device in get_devices_by_filter(client, args.filter, args.all_info):
        print(json.dumps(device, indent=6))

    return 0


if __name__ == '__main__':
    main()
