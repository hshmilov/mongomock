import logging
import datetime

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from zscaler_adapter.connection import ZscalerConnection
from zscaler_adapter.client_id import get_client_id
from zscaler_adapter.consts import DEFAULT_DOMAIN

logger = logging.getLogger(f'axonius.{__name__}')


class ZscalerAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        company_name = Field(str, 'Company Name')
        detail = Field(str, 'Detail')
        registration_state = Field(str, 'Registration State')
        policy_name = Field(str, 'Policy Name')
        owner = Field(str, 'Owner')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _get_domain(client_config):
        return client_config.get('domain') or DEFAULT_DOMAIN

    @staticmethod
    def _test_reachability(client_config):
        domain = ZscalerAdapter._get_domain(client_config)
        return RESTConnection.test_reachability(domain)

    @staticmethod
    def get_connection(client_config):
        connection = ZscalerConnection(domain=ZscalerAdapter._get_domain(client_config),
                                       verify_ssl=client_config['verify_ssl'],
                                       https_proxy=client_config.get('https_proxy'),
                                       username=client_config['username'],
                                       password=client_config['password'],
                                       apikey=client_config['apikey'])
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            domain = self._get_domain(client_config)
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(domain, str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema ZscalerAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Zscaler Domain',
                    'type': 'string',
                    'default': DEFAULT_DOMAIN,
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
                    'type': 'string',
                    'format': 'password',
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'bool'
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _create_device(device, device_raw):
        if not device_raw.get('id'):
            logger.warning(f'Bad device with no ID {device_raw}')
            return None

        device.id = 'zscaler_' + str(device_raw.get('id'))

        if device_raw.get('machineHostname'):
            device.id = device.id + '_' + device_raw['machineHostname']

        if device_raw.get('macAddress'):
            device.add_nic(mac=device_raw.get('macAddress'))
        device.figure_os(device_raw.get('osVersion'))
        device.hostname = device_raw.get('machineHostname')
        device.device_manufacturer = device_raw.get('manufacturer')

        try:
            timestamp = device_raw.get('last_seen_time')
            if timestamp:
                device.last_seen = datetime.datetime.fromtimestamp(int(timestamp))
        except Exception:
            logger.exception('Failed to set last seen')

        if device_raw.get('user'):
            device.last_used_users.append(device_raw.get('user'))

        device.policy_name = device_raw.get('policyName')
        device.owner = device_raw.get('owner')
        device.company_name = device_raw.get('companyName')
        device.detail = device_raw.get('detail')
        device.set_raw(device_raw)
        return device

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device = self._create_device(device, device_raw)
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching Zscaler Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
