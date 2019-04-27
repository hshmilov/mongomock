import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.fields import Field, ListField
from axonius.utils.datetime import parse_date
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from cloudflare_adapter.connection import CloudflareConnection
from cloudflare_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class CloudflareAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        cnames = ListField(str, 'CNames')
        zone_name = Field(str, 'Zone Name')
        locked = Field(bool, 'Locked')
        created_on = Field(datetime.datetime, 'Created On')
        modified_on = Field(datetime.datetime, 'Modified On')
        proxiable = Field(bool, 'Proxiable')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def get_connection(client_config):
        connection = CloudflareConnection(domain=client_config['domain'],
                                          verify_ssl=client_config['verify_ssl'],
                                          https_proxy=client_config.get('https_proxy'),
                                          username=client_config['user_email'],
                                          apikey=client_config['apikey'])
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
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
        The schema CloudflareAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Cloudflare Domain',
                    'type': 'string'
                },
                {
                    'name': 'user_email',
                    'title': 'User Email',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
                    'type': 'string',
                    'format': 'password'
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
                'user_email',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw, cnamas_dict):
        try:
            device = self._new_device_adapter()
            if device_raw.get('type') not in ['A', 'AAAA']:
                return None
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')
            device.hostname = device_raw.get('name')
            if cnamas_dict.get(device_raw.get('name')):
                device.cnames = cnamas_dict.get(device_raw.get('name'))
            if device_raw.get('content'):
                device.add_nic(ips=[device_raw.get('content')])
            device.zone_name = device_raw.get('zone_name')
            if isinstance(device_raw.get('locked'), bool):
                device.locked = bool(device_raw.get('locked'))
            device.created_on = parse_date(device_raw.get('created_on'))
            device.modified_on = parse_date(device_raw.get('modified_on'))
            if isinstance(device_raw.get('proxiable'), bool):
                device.proxiable = bool(device_raw.get('proxiable'))
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Cloudflare Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, cnamas_dict in devices_raw_data:
            device = self._create_device(device_raw, cnamas_dict)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
