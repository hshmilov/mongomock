import logging
import re

from cisco_ise_adapter.consts import ISE_PORT, URL_BASE_PREFIX
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.xml2json_parser import Xml2Json

logger = logging.getLogger(f'axonius.{__name__}')


class CiscoIseConnection(RESTConnection):
    """
    Class to configure Cisco ISE via the ERS API
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         port=ISE_PORT,
                         url_base_prefix=URL_BASE_PREFIX,
                         headers={'Connection': 'keep_alive'},
                         **kwargs)

    # pylint: disable=arguments-differ
    def _do_request(self, *args, **kwargs):
        kwargs['raise_for_status'] = False
        kwargs['use_json_in_response'] = False
        kwargs['return_response_raw'] = True

        super()._do_request(*args, **kwargs)
    # pylint: enable=arguments-differ

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

    def get_device_list(self):
        devices = self.get_devices()
        if not devices['success']:
            logger.error(f'Unable to get device list {devices.get("error")} {devices.get("response")}')
            return
        for device_name, _ in devices['response']:
            try:
                device = self.get_device(device_name)
                if not device['success']:
                    logger.error(f'Unable to get device {device.get("error")} {devices.get("response")}')
                    continue
                yield device
            except Exception:
                logger.exception(f'Unable to get device')

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
        return Xml2Json(content).result

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
                for i in self._to_json(resp.text)['ns3:searchResult']['resources']['resource']
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
                'config/endpointgroup/{0}'.format(found_group['ns3:searchResult']['resources']['resource']['@id']),
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

    def get_endpoints(self):
        """
        Get all endpoints
        :return: result dictionary
        """
        extra_headers = {'Accept': 'application/vnd.com.cisco.ise.identity.endpoint.1.0+xml'}

        resp = self._get('/config/endpoint', extra_headers=extra_headers)

        result = {'success': False, 'response': '', 'error': ''}

        json_res = self._to_json(resp.text)['ns3:searchResult']

        if resp.status_code == 200 and int(json_res['@total']) > 1:
            result['success'] = True
            result['response'] = [(i['@name'], i['@id']) for i in json_res['resources']['resource']]

        elif resp.status_code == 200 and int(json_res['@total']) == 1:
            result['success'] = True
            result['response'] = [
                (json_res['resources']['resource']['@name'], json_res['resources']['resource']['@id'])
            ]
        elif resp.status_code == 200 and int(json_res['@total']) == 0:
            result['success'] = True
            result['response'] = []

        else:
            result['response'] = self._to_json(resp.text)['ns3:ersResponse']['messages']['message']['title']
            result['error'] = resp.status_code
        return result

    def get_endpoint(self, mac_address):
        """
        Get endpoint details
        :param mac_address: MAC address of the endpoint
        :return: result dictionary
        """
        is_valid = self._mac_test(mac_address)

        if not is_valid:
            raise RuntimeError('{0}. Must be in the form of AA:BB:CC:00:11:22'.format(mac_address))

        extra_headers = {'Accept': 'application/vnd.com.cisco.ise.identity.endpoint.1.0+xml'}

        result = {'success': False, 'response': '', 'error': ''}

        resp = self._get('config/endpoint?filter=mac.EQ.{0}'.format(mac_address), extra_headers=extra_headers)
        found_endpoint = self._to_json(resp.text)

        if found_endpoint['ns3:searchResult']['@total'] == '1':
            resp = self._get(
                'config/endpoint/{0}'.format(found_endpoint['ns3:searchResult']['resources']['resource']['@id']),
                extra_headers=extra_headers,
            )
            if resp.status_code == 200:
                result['success'] = True
                result['response'] = self._to_json(resp.text)['ns4:endpoint']
            elif resp.status_code == 404:
                result['response'] = '{0} not found'.format(mac_address)
                result['error'] = resp.status_code
            else:
                result['response'] = self._to_json(resp.text)['ns3:ersResponse']['messages']['message']['title']
                result['error'] = resp.status_code
        elif found_endpoint['ns3:searchResult']['@total'] == '0':
            result['response'] = '{0} not found'.format(mac_address)
            result['error'] = 404

        else:
            result['response'] = '{0} not found'.format(mac_address)
            result['error'] = resp.status_code
        return result

    def get_identity_groups(self):
        """
        Get all identity groups
        :return: result dictionary
        """
        result = {'success': False, 'response': '', 'error': ''}

        extra_headers = {'Accept': 'application/vnd.com.cisco.ise.identity.identitygroup.1.0+xml'}

        resp = self._get('/config/identitygroup', extra_headers=extra_headers)

        if resp.status_code == 200:
            result['success'] = True
            result['response'] = [
                (i['@name'], i['@id'], i['@description'])
                for i in self._to_json(resp.text)['ns3:searchResult']['resources']['resource']
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
                'config/identitygroup/{0}'.format(found_group['ns3:searchResult']['resources']['resource']['@id']),
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
            result['response'] = [(i['@name'], i['@id']) for i in json_res['resources']['resource']]
        elif resp.status_code == 200 and int(json_res['@total']) == 1:
            result['success'] = True
            result['response'] = [
                (json_res['resources']['resource']['@name'], json_res['resources']['resource']['@id'])
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
                'config/internaluser/{0}'.format(found_user['ns3:searchResult']['resources']['resource']['@id']),
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
            result['success'] = True
            result['response'] = [
                (i['@name'], i['@id']) for i in self._to_json(resp.text)['ns3:searchResult']['resources']['resource']
            ]
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

    def get_devices(self):
        """
        Get a list of devices
        :return: result dictionary
        """
        extra_headers = {'Accept': 'application/vnd.com.cisco.ise.network.networkdevice.1.0+xml'}

        resp = self._get('config/networkdevice', extra_headers=extra_headers)

        result = {'success': False, 'response': '', 'error': ''}

        json_res = self._to_json(resp.text)['ns3:searchResult']

        if resp.status_code == 200 and int(json_res['@total']) > 1:
            result['success'] = True
            result['response'] = [(i['@name'], i['@id']) for i in json_res['resources']['resource']]

        elif resp.status_code == 200 and int(json_res['@total']) == 1:
            result['success'] = True
            result['response'] = [
                (json_res['resources']['resource']['@name'], json_res['resources']['resource']['@id'])
            ]

        elif resp.status_code == 200 and int(json_res['@total']) == 0:
            result['success'] = True
            result['response'] = []

        else:
            result['response'] = self._to_json(resp.text)['ns3:ersResponse']['messages']['message']['title']
            result['error'] = resp.status_code
        return result

    def get_device(self, device):
        """
        Get device detailed info
        :param device: User ID
        :return: result dictionary
        """
        extra_headers = {'Accept': 'application/vnd.com.cisco.ise.network.networkdevice.1.0+xml'}

        result = {'success': False, 'response': '', 'error': ''}

        resp = self._get('config/networkdevice?filter=name.EQ.{0}'.format(device), extra_headers=extra_headers)
        found_device = self._to_json(resp.text)

        if found_device['ns3:searchResult']['@total'] == '1':
            resp = self._get(
                'config/networkdevice/{0}'.format(found_device['ns3:searchResult']['resources']['resource']['@id']),
                extra_headers=extra_headers,
            )
            if resp.status_code == 200:
                result['success'] = True
                result['response'] = self._to_json(resp.text)['ns4:networkdevice']
            elif resp.status_code == 404:
                result['response'] = '{0} not found'.format(device)
                result['error'] = resp.status_code
            else:
                result['response'] = self._to_json(resp.text)['ns3:ersResponse']['messages']['message']['title']
                result['error'] = resp.status_code
        elif found_device['ns3:searchResult']['@total'] == '0':
            result['response'] = '{0} not found'.format(device)
            result['error'] = 404
        else:
            result['response'] = self._to_json(resp.text)['ns3:ersResponse']['messages']['message']['title']
            result['error'] = resp.status_code
        return result
