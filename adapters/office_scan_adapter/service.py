import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.fields import Field, ListField
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from office_scan_adapter.connection import OfficeScanConnection
from office_scan_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class OfficeScanAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        isolation_status = Field(str, 'Isolation Status')
        folder_path = Field(str, 'Folder Path')
        capabilities = ListField(str, 'Capabilities')
        ad_domain = Field(str, 'Application Domain')
        product = Field(str, 'Product')
        managing_server_id = Field(str, 'Managing Server Id')
        entity_id = Field(str, 'Entity Id')

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
        connection = OfficeScanConnection(domain=client_config['domain'],
                                          verify_ssl=client_config['verify_ssl'],
                                          https_proxy=client_config.get('https_proxy'),
                                          app_id=client_config['app_id'],
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
        The schema OfficeScanAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'OfficeScan Domain',
                    'type': 'string'
                },
                {
                    'name': 'app_id',
                    'title': 'Application Id',
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
                'app_id',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('entity_id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('host_name') or '')
            device.entity_id = device_raw.get('entity_id')
            device.hostname = device_raw.get('host_name')
            try:
                if isinstance(device_raw.get('ip_address_list'), str):
                    ips = device_raw.get('ip_address_list').split(',')
                else:
                    ips = None
                if isinstance(device_raw.get('mac_address_list'), str):
                    macs = device_raw.get('mac_address_list').split(',')
                else:
                    macs = None
                device.add_ips_and_macs(macs=macs, ips=ips)
            except Exception:
                logger.exception(f'Problem getting nic for {device_raw}')
            device.isolation_status = device_raw.get('isolation_status')
            device.folder_path = device_raw.get('folder_path')
            try:
                if isinstance(device_raw.get('capabilities'), list):
                    device.capabilities = device_raw.get('capabilities')
            except Exception:
                logger.exception(f'Problem getting capabilities')
            device.ad_domain = device_raw.get('ad_domain')
            device.product = device_raw.get('product')
            device.managing_server_id = device_raw.get('managing_server_id')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching OfficeScan Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]
