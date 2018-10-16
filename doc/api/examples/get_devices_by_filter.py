#!/usr/local/bin/python3
"""
The following file contains a function to get devices from Axonius by specific filter.
"""
import requests
import urllib3

__author__ = 'Axonius, Inc'

# How many devices to query per request
PAGING_LIMIT = 50

# Suppress InsecureRequestWarning: Unverified HTTPS request
urllib3.disable_warnings()


def get_devices_by_filter(axonius_addr, api_key, api_secret, api_filter, all_info):
    """
    Queries Axonius API about specific devices.
    :param str axonius_addr: ip or host of an Axonius system
    :param str api_key: an api key of an Axonius user with sufficient privileges.
    :param str api_secret: an api secret of an Axonius user with sufficient privilegs.
    :param str api_filter: an Axonius filter (the one that appears in the gui after using the query builder)
    :param bool all_info: if True, returns all info about the device. else, returns only basic info.
    :return:
    """
    devices_api_url = 'https://{0}/api/V1/devices'.format(axonius_addr)
    headers = {'api-key': api_key, 'api-secret': api_secret}

    def make_request(skip):
        params = {
            'filter': api_filter,
            'skip': skip,
            'limit': PAGING_LIMIT
        }
        if all_info is not True:
            # Ask the API to return only specific fields
            params['fields'] = ','.join([
                'specific_data.data.hostname',
                'specific_data.data.name',
                'specific_data.data.network_interfaces.mac',
                'specific_data.data.network_interfaces.ips',
            ])

        response = requests.get(
            devices_api_url,
            params=params,
            headers=headers,
            verify=False
        )

        # Verify that we got a valid response and return it as json
        response.raise_for_status()
        return response.json()

    first_page = make_request(0)
    yield from first_page['assets']
    total_devices = first_page['page']['totalResources']

    count = PAGING_LIMIT
    while count < total_devices:
        yield from make_request(count)['assets']
        count += PAGING_LIMIT
