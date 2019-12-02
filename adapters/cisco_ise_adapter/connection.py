import json
import logging
import re

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.plugin_base import PluginBase
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

    @property
    def top_endpoint_page(self):
        # top_endpoint_page is a variable that is saved between connections. It saves the last page that was fetched
        # to support fetching from the next page in the next cycle.
        return PluginBase.Instance.keyval.get(f'{self.client_id}_top_endpoint_page') or 0

    @top_endpoint_page.setter
    def top_endpoint_page(self, value):
        PluginBase.Instance.keyval[f'{self.client_id}_top_endpoint_page'] = value

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
                    # https://axonius.atlassian.net/browse/AX-5135
                    # self._strip_instance(item)
                continue
            if key in SECRETS:
                device_raw[key] = '*******'

    # pylint: disable=too-many-branches
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
            endpoints = self.get_endpoints(page=(page + self.top_endpoint_page))
            if not endpoints['success']:
                logger.error(f'Unable to get device list {endpoints.get("error")} {endpoints.get("response")}')
                self.top_endpoint_page = 0
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
                self.top_endpoint_page = 0
                break
        if page == MAX_NETWORK_DEVICE_PAGE - 1:
            self.top_endpoint_page += MAX_NETWORK_DEVICE_PAGE

    def get_users_list(self):
        raise NotImplementedError()

    # pylint: disable=arguments-differ
    @staticmethod
    def test_reachability(domain):
        return super().test_reachbility(domain, port=ISE_PORT, path=URL_BASE_PREFIX, ssl=True)

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

    # pylint: disable=invalid-name
    @staticmethod
    def get_ns(json_, field, ns='ns3'):
        return json_.get(field) or json_.get(':'.join([ns, field]))
    # pylint: enable=invalid-name

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
            json_res = self.get_ns(json_res, 'searchResult')

            if resp.status_code == 200 and int(json_res['@total']) > 1:
                result['success'] = True
                result['response'] = [(i['@name'], i['@id']) for i in self.get_ns(json_res, 'resources')['resource']]

            elif resp.status_code == 200 and int(json_res['@total']) == 1:
                result['success'] = True
                result['response'] = [
                    (self.get_ns(json_res, 'resources')['resource']['@name'],
                     self.get_ns(json_res, 'resources')['resource']['@id'])
                ]
            elif resp.status_code == 200 and int(json_res['@total']) == 0:
                result['success'] = True
                result['response'] = []

            else:
                response = self.get_ns(self._to_json(resp.text), 'ersResponse')
                result['response'] = resp['messages']['message']['title']
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
            result['response'] = self.get_ns(self._to_json(resp.text), 'endpoint', 'ns4')
        elif resp.status_code == 404:
            result['response'] = '{0} not found'.format(device_id)
            result['error'] = resp.status_code
        else:
            result['response'] = self.get_ns(self._to_json(resp.text), 'ersResponse')['messages']['message']['title']
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
            json_res = self.get_ns(self._to_json(resp.text), 'searchResult')
            if resp.status_code == 200 and int(json_res['@total']) > 1:
                result['response'] = [(i['@name'], i['@id']) for i in self.get_ns(json_res, 'resources')['resource']]
                result['success'] = True

            elif resp.status_code == 200 and int(json_res['@total']) == 1:
                result['response'] = [
                    (self.get_ns(json_res, 'resources')['resource']['@name'],
                     self.get_ns(json_res, 'resources')['resource']['@id'])
                ]
                result['success'] = True

            elif resp.status_code == 200 and int(json_res['@total']) == 0:
                result['success'] = True
                result['response'] = []

            else:
                response = self.get_ns(self._to_json(resp.text), 'ersResponse')
                result['response'] = response['messages']['message']['title']
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
                result['response'] = self.get_ns(specific_device, 'networkdevice', 'ns4')
                result['success'] = True
            elif resp.status_code == 404:
                result['response'] = '{0} not found'.format(device_id)
                result['error'] = resp.status_code
            else:
                result['response'] = self.get_ns(specific_device, 'ersResponse')['messages']['message']['title']
                result['error'] = resp.status_code
        except Exception:
            logger.exception(f'Failed to parse specific_device {specific_device}')
        return result
