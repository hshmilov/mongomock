#!/usr/local/bin/python3
"""
The following file contains a function to get devices from Axonius by specific filter.
"""

from axoniussdk.client import RESTClient

__author__ = 'Axonius, Inc'

# How many devices to query per request
PAGING_LIMIT = 50


def get_devices_by_filter(client: RESTClient, api_filter: str, all_info: str):
    """
    Queries Axonius API about specific devices.
    :param RESTClient client: Axnoius RESTClient
    :param str api_filter: an Axonius filter (the one that appears in the gui after using the query builder)
    :param bool all_info: if True, returns all info about the device. else, returns only basic info.
    :return:
    """
    fields = None
    if all_info is not True:
        # Ask the API to return only specific fields
        fields = ','.join([
            'specific_data.data.hostname',
            'specific_data.data.name',
            'specific_data.data.network_interfaces.mac',
            'specific_data.data.network_interfaces.ips',
        ])

    status_code, first_page = client.get_devices(skip=0, limit=PAGING_LIMIT,
                                                 filter_=api_filter, fields=fields)
    yield from first_page['assets']
    total_devices = first_page['page']['totalResources']

    count = PAGING_LIMIT
    while count < total_devices:
        status_code, resp = client.get_devices(skip=count, limit=PAGING_LIMIT)
        yield from resp['assets']
        count += PAGING_LIMIT
