import json
import logging
import re

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from cisco_ise_adapter import xmltodict
from cisco_ise_adapter.consts import (
    ISE_PORT,
    MAX_NETWORK_DEVICE_PAGE,
    PAGE_SIZE,
    SECRETS,
    URL_BASE_PREFIX,
    CiscoIseDeviceType,
)

logger = logging.getLogger(f'axonius.{__name__}')


class CiscoIseConnection(RESTConnection):
    """
    Class to configure Cisco ISE via the ERS API
    """

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, port=ISE_PORT, url_base_prefix=URL_BASE_PREFIX, headers={'Connection': 'keep_alive'}, **kwargs
        )

    # pylint: disable=arguments-differ
    def _do_request(self, *args, **kwargs):
        kwargs['raise_for_status'] = False
        kwargs['use_json_in_response'] = False
        kwargs['return_response_raw'] = True
        kwargs['do_basic_auth'] = True

        resp = super()._do_request(*args, **kwargs)
        if resp.status_code == 401:
            raise RESTException(
                'The request has not been applied because it lacks '
                + 'valid authentication credentials for the target resource.'
            )
        return resp

    # pylint: enable=arguments-differ

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        # Get devices to validate that the creds are valid
        extra_headers = {'Accept': 'application/vnd.com.cisco.ise.network.networkdevice.1.0+xml'}
        self._get('config/networkdevice', extra_headers=extra_headers)

    def _strip_secrets(self, device_raw):
        if not isinstance(device_raw, dict):
            return

        for key, value in device_raw.items():
            if isinstance(value, dict):
                self._strip_secrets(value)
                continue

            if isinstance(value, list):
                for item in value:
                    if not isinstance(value, dict):
                        continue
                    self._strip_instance(item)
                continue
            if key in SECRETS:
                device_raw[key] = '*******'

    def get_device_list(self):
        for page in range(1, MAX_NETWORK_DEVICE_PAGE):
            devices = self.get_devices(page=page)
            if not devices['success']:
                logger.error(f'Unable to get device list {devices.get("error")} {devices.get("response")}')
                break
            for device_name, device_id in devices['response']:
                try:
                    device = self.get_device(device_id)
                    if not device['success']:
                        logger.error(f'Unable to get device {device.get("error")} {devices.get("response")}')
                        continue
                    self._strip_secrets(device['response'])
                    yield (CiscoIseDeviceType.NetworkDevice.name, device['response'])
                except Exception:
                    logger.exception(f'Unable to get device')
            if len(devices['response']) < PAGE_SIZE:
                break

        for page in range(1, MAX_NETWORK_DEVICE_PAGE):
            endpoints = self.get_endpoints(page=page)
            if not endpoints['success']:
                logger.error(f'Unable to get device list {endpoints.get("error")} {endpoints.get("response")}')
                break
            for endpoint_name, endpoint_id in endpoints['response']:
                try:
                    endpoint = self.get_endpoint(endpoint_id)
                    if not endpoint['success']:
                        logger.error(f'Unable to get endpoint {endpoint.get("error")} {endpoints.get("response")}')
                        continue
                    yield (CiscoIseDeviceType.EndpointDevice.name, endpoint['response'])
                except Exception:
                    logger.exception(f'Unable to get endpoint')
            if len(endpoints['response']) < PAGE_SIZE:
                break

    def get_users_list(self):
        raise NotImplementedError()

    # pylint: disable=arguments-differ
    @staticmethod
    def test_reachability(domain, verify_ssl=False):
        return super().test_reachbility(domain, port=ISE_PORT, path=URL_BASE_PREFIX, ssl=verify_ssl)

    # pylint: enable=arguments-differ

    @staticmethod
    def _to_json(content):
        """
        ISE API uses xml, this method will convert the xml to json.
        Why? JSON when you can, XML when you must!
        :param content: xml to convert to json
        :return: json result
        """
        namespaces = {
            'ers.ise.cisco.com': None,
            'v2.ers.ise.cisco.com': 'ns3',
            'network.ers.ise.cisco.com': 'ns4',
            'identity.ers.ise.cisco.com': 'ns4',
        }
        force_list = ('NetworkDeviceIPList', 'NetworkDeviceGroupList')
        return json.loads(
            json.dumps(xmltodict.parse(content, process_namespaces=True, namespaces=namespaces, force_list=force_list))
        )

    @staticmethod
    def _mac_test(mac):
        """
        Test for valid mac address
        :param mac: MAC address in the form of AA:BB:CC:00:11:22
        :return: True/False
        """
        return bool(re.search(r'([0-9A-F]{2}[:]){5}([0-9A-F]){2}', mac.upper()) is not None)

    def get_endpoint_groups(self):
        """
        Get all endpoint identity groups
        :return: result dictionary
        """
        result = {'success': False, 'response': '', 'error': ''}

        extra_headers = {'Accept': 'application/vnd.com.cisco.ise.identity.endpointgroup.1.0+xml'}

        resp = self._get('config/endpointgroup', extra_headers=extra_headers)

        if resp.status_code == 200:
            result['success'] = True
            result['response'] = [
                (i['@name'], i['@id'], i['@description'])
                for i in self._to_json(resp.text)['ns3:searchResult']['ns3:resources']['resource']
            ]
        else:
            result['response'] = self._to_json(resp.text)['ns3:ersResponse']['messages']['message']['title']
            result['error'] = resp.status_code
        return result

    def get_endpoint_group(self, group):
        """
        Get endpoint identity group details
        :param group: Name of the identity group
        :return: result dictionary
        """
        extra_headers = {'Accept': 'application/vnd.com.cisco.ise.identity.endpointgroup.1.0+xml'}

        result = {'success': False, 'response': '', 'error': ''}

        resp = self._get('config/endpointgroup?filter=name.EQ.{0}'.format(group), extra_headers=extra_headers)
        found_group = self._to_json(resp.text)

        if found_group['ns3:searchResult']['@total'] == '1':
            resp = self._get(
                'config/endpointgroup/{0}'.format(found_group['ns3:searchResult']['ns3:resources']['resource']['@id']),
                extra_headers=extra_headers,
            )
            if resp.status_code == 200:
                result['success'] = True
                result['response'] = self._to_json(resp.text)['ns4:endpointgroup']
            elif resp.status_code == 404:
                result['response'] = '{0} not found'.format(group)
                result['error'] = resp.status_code
            else:
                result['response'] = self._to_json(resp.text)['ns3:ersResponse']['messages']['message']['title']
                result['error'] = resp.status_code
        elif found_group['ns3:searchResult']['@total'] == '0':
            result['response'] = '{0} not found'.format(group)
            result['error'] = 404
        else:
            result['response'] = '{0} not found'.format(group)
            result['error'] = resp.status_code
        return result

    def get_endpoints(self, page=1, size=PAGE_SIZE):
        """
        Get all endpoints
        :return: result dictionary
        """
        extra_headers = {'Accept': 'application/vnd.com.cisco.ise.identity.endpoint.1.0+xml'}
        url_params = {'page': page, 'size': size}

        resp = self._get('config/endpoint', extra_headers=extra_headers, url_params=url_params)

        result = {'success': False, 'response': '', 'error': ''}

        json_res = self._to_json(resp.text)
        try:
            json_res = json_res['ns3:searchResult']

            if resp.status_code == 200 and int(json_res['@total']) > 1:
                result['success'] = True
                result['response'] = [(i['@name'], i['@id']) for i in json_res['ns3:resources']['resource']]

            elif resp.status_code == 200 and int(json_res['@total']) == 1:
                result['success'] = True
                result['response'] = [
                    (json_res['ns3:resources']['resource']['@name'], json_res['ns3:resources']['resource']['@id'])
                ]
            elif resp.status_code == 200 and int(json_res['@total']) == 0:
                result['success'] = True
                result['response'] = []

            else:
                result['response'] = self._to_json(resp.text)['ns3:ersResponse']['messages']['message']['title']
                result['error'] = resp.status_code
        except Exception:
            logger.exception(f'Failed to parse json_res {json_res}')
        return result

    def get_endpoint(self, device_id):
        """
        Get endpoint details
        :param mac_address: MAC address of the endpoint
        :return: result dictionary
        """

        extra_headers = {'Accept': 'application/vnd.com.cisco.ise.identity.endpoint.1.0+xml'}

        result = {'success': False, 'response': '', 'error': ''}

        resp = self._get('config/endpoint/{0}'.format(device_id), extra_headers=extra_headers)
        if resp.status_code == 200:
            result['success'] = True
            result['response'] = self._to_json(resp.text)['ns4:endpoint']
        elif resp.status_code == 404:
            result['response'] = '{0} not found'.format(device_id)
            result['error'] = resp.status_code
        else:
            result['response'] = self._to_json(resp.text)['ns3:ersResponse']['messages']['message']['title']
            result['error'] = resp.status_code
        return result

    def get_identity_groups(self):
        """
        Get all identity groups
        :return: result dictionary
        """
        result = {'success': False, 'response': '', 'error': ''}

        extra_headers = {'Accept': 'application/vnd.com.cisco.ise.identity.identitygroup.1.0+xml'}

        resp = self._get('config/identitygroup', extra_headers=extra_headers)

        if resp.status_code == 200:
            result['success'] = True
            result['response'] = [
                (i['@name'], i['@id'], i['@description'])
                for i in self._to_json(resp.text)['ns3:searchResult']['ns3:resources']['resource']
            ]
        else:
            result['response'] = self._to_json(resp.text)['ns3:ersResponse']['messages']['message']['title']
            result['error'] = resp.status_code
        return result

    def get_identity_group(self, group):
        """
        Get identity group details
        :param group: Name of the identity group
        :return: result dictionary
        """
        extra_headers = {'Accept': 'application/vnd.com.cisco.ise.identity.identitygroup.1.0+xml'}

        result = {'success': False, 'response': '', 'error': ''}

        resp = self._get('config/identitygroup?filter=name.EQ.{0}'.format(group), extra_headers=extra_headers)
        found_group = self._to_json(resp.text)

        if found_group['ns3:searchResult']['@total'] == '1':
            resp = self._get(
                'config/identitygroup/{0}'.format(found_group['ns3:searchResult']['ns3:resources']['resource']['@id']),
                extra_headers=extra_headers,
            )
            if resp.status_code == 200:
                result['success'] = True
                result['response'] = self._to_json(resp.text)['ns4:identitygroup']
            elif resp.status_code == 404:
                result['response'] = '{0} not found'.format(group)
                result['error'] = resp.status_code
            else:
                result['response'] = self._to_json(resp.text)['ns3:ersResponse']['messages']['message']['title']
                result['error'] = resp.status_code
        elif found_group['ns3:searchResult']['@total'] == '0':
            result['response'] = '{0} not found'.format(group)
            result['error'] = 404
        else:
            result['response'] = '{0} not found'.format(group)
            result['error'] = resp.status_code
        return result

    def get_users(self):
        """
        Get all internal users
        :return: List of tuples of user details
        """
        extra_headers = {'Accept': 'application/vnd.com.cisco.ise.identity.internaluser.1.1+xml'}

        resp = self._get('config/internaluser', extra_headers=extra_headers)

        result = {'success': False, 'response': '', 'error': ''}

        json_res = self._to_json(resp.text)['ns3:searchResult']

        if resp.status_code == 200 and int(json_res['@total']) > 1:
            result['success'] = True
            result['response'] = [(i['@name'], i['@id']) for i in json_res['ns3:resources']['resource']]
        elif resp.status_code == 200 and int(json_res['@total']) == 1:
            result['success'] = True
            result['response'] = [
                (json_res['ns3:resources']['resource']['@name'], json_res['ns3:resources']['resource']['@id'])
            ]
        elif resp.status_code == 200 and int(json_res['@total']) == 0:
            result['success'] = True
            result['response'] = []
        else:
            result['response'] = self._to_json(resp.text)['ns3:ersResponse']['messages']['message']['title']
            result['error'] = resp.status_code
        return result

    def get_user(self, user_id):
        """
        Get user detailed info
        :param user_id: User ID
        :return: result dictionary
        """
        extra_headers = {'Accept': 'application/vnd.com.cisco.ise.identity.internaluser.1.0+xml'}

        result = {'success': False, 'response': '', 'error': ''}

        resp = self._get('config/internaluser?filter=name.EQ.{0}'.format(user_id), extra_headers=extra_headers)
        found_user = self._to_json(resp.text)

        if found_user['ns3:searchResult']['@total'] == '1':
            resp = self._get(
                'config/internaluser/{0}'.format(found_user['ns3:searchResult']['ns3:resources']['resource']['@id']),
                extra_headers=extra_headers,
            )
            if resp.status_code == 200:
                result['success'] = True
                result['response'] = self._to_json(resp.text)['ns4:internaluser']
            elif resp.status_code == 404:
                result['response'] = '{0} not found'.format(user_id)
                result['error'] = resp.status_code
            else:
                result['response'] = self._to_json(resp.text)['ns3:ersResponse']['messages']['message']['title']
                result['error'] = resp.status_code
        elif found_user['ns3:searchResult']['@total'] == '0':
            result['response'] = '{0} not found'.format(user_id)
            result['error'] = 404
        else:
            result['response'] = 'Unknown error'
            result['error'] = resp.status_code
        return result

    def get_device_groups(self):
        """
        Get a list tuples of device groups
        :return:
        """
        result = {'success': False, 'response': '', 'error': ''}

        extra_headers = {'Accept': 'application/vnd.com.cisco.ise.network.networkdevicegroup.1.0+xml'}

        resp = self._get('config/networkdevicegroup', extra_headers=extra_headers)

        if resp.status_code == 200:
            resources = self._to_json(resp.text)['ns3:searchResult']['ns3:resources']['resource']
            result['success'] = True
            result['response'] = [(i['@name'], i['@id']) for i in resources]
        else:
            result['response'] = self._to_json(resp.text)['ns3:ersResponse']['messages']['message']['title']
            result['error'] = resp.status_code
        return result

    def get_device_group(self, device_group_oid):
        """
        Get a device group details
        :param device_group_oid: oid of the device group
        :return: result dictionary
        """
        extra_headers = {'Accept': 'application/vnd.com.cisco.ise.network.networkdevicegroup.1.0+xml'}

        resp = self._get('config/networkdevicegroup/{0}'.format(device_group_oid), extra_headers=extra_headers)

        result = {'success': False, 'response': '', 'error': ''}

        if resp.status_code == 200:
            result['success'] = True
            result['response'] = self._to_json(resp.text)['ns4:networkdevicegroup']
        elif resp.status_code == 404:
            result['response'] = '{0} not found'.format(device_group_oid)
            result['error'] = resp.status_code
        else:
            result['response'] = self._to_json(resp.text)['ns3:ersResponse']['messages']['message']['title']
            result['error'] = resp.status_code
        return result

    def get_devices(self, page=1, size=100):
        """
        Get a list of devices
        :return: result dictionary
        """
        extra_headers = {'Accept': 'application/vnd.com.cisco.ise.network.networkdevice.1.0+xml'}

        url_params = {'page': page, 'size': size}
        resp = self._get('config/networkdevice', extra_headers=extra_headers, url_params=url_params)
        result = {'success': False, 'response': '', 'error': ''}

        json_res = self._to_json(resp.text)
        try:
            json_res = self._to_json(resp.text)['ns3:searchResult']
            if resp.status_code == 200 and int(json_res['@total']) > 1:
                result['response'] = [(i['@name'], i['@id']) for i in json_res['ns3:resources']['resource']]
                result['success'] = True

            elif resp.status_code == 200 and int(json_res['@total']) == 1:
                result['response'] = [
                    (json_res['ns3:resources']['resource']['@name'], json_res['ns3:resources']['resource']['@id'])
                ]
                result['success'] = True

            elif resp.status_code == 200 and int(json_res['@total']) == 0:
                result['success'] = True
                result['response'] = []

            else:
                result['response'] = self._to_json(resp.text)['ns3:ersResponse']['messages']['message']['title']
                result['error'] = resp.status_code
        except Exception:
            logger.exception(f'Failed to parse json_res {json_res}')
        return result

    def get_device(self, device_id):
        """
        Get device detailed info
        :param device: User ID
        :return: result dictionary
        """
        extra_headers = {'Accept': 'application/vnd.com.cisco.ise.network.networkdevice.1.0+xml'}

        result = {'success': False, 'response': '', 'error': ''}
        resp = self._get('config/networkdevice/{0}'.format(device_id), extra_headers=extra_headers)
        specific_device = self._to_json(resp.text)
        try:
            if resp.status_code == 200:
                result['response'] = specific_device['ns4:networkdevice']
                result['success'] = True
            elif resp.status_code == 404:
                result['response'] = '{0} not found'.format(device_id)
                result['error'] = resp.status_code
            else:
                result['response'] = specific_device['ns3:ersResponse']['messages']['message']['title']
                result['error'] = resp.status_code
        except Exception:
            logger.exception(f'Failed to parse specific_device {specific_device}')
        return result
