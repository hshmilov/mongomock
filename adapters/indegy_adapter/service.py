import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.types.ssl_state import MANDATORY_SSL_CONFIG_SCHEMA
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.fields import Field

from indegy_adapter.connection import IndegyConnection
from indegy_adapter.client_id import get_client_id
from indegy_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class IndegyAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        vendor = Field(str, 'Vendor')
        state = Field(str, 'State')
        device_type = Field(str, 'Type')
        firmware_version = Field(str, 'Firmware Version')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'), port=consts.DEFAULT_API_PORT)

    def get_connection(self, client_config):
        try:
            connection = IndegyConnection(domain=client_config['domain'],
                                          verify_ssl=client_config['verify_ssl'],
                                          port=consts.DEFAULT_API_PORT,
                                          https_proxy=client_config.get('https_proxy'),
                                          private_key=self._grab_file_contents(client_config['private_key']),
                                          cert_file=self._grab_file_contents(client_config['cert_file']))
            with connection:
                pass
            return connection
        except Exception as e:
            raise ClientConnectionException(e)

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
        The schema IndegyAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Indegy Domain',
                    'type': 'string'
                },
                {
                    'name': 'robot_name',
                    'title': 'Robot Name',
                    'type': 'string'
                },
                *MANDATORY_SSL_CONFIG_SCHEMA,
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'robot_name',
                'private_key',
                'cert_file',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id
            device.device_type = device_raw.get('type')
            device.state = device_raw.get('state')
            device.device_model = device_raw.get('modelName')
            device.device_model_family = device_raw.get('family')
            device.figure_os(device_raw.get('os'))
            device.firmware_version = device_raw.get('firmwareVersion')
            device.vendor = device_raw.get('vendor')
            last_seen = None
            # loop each interface for getting interface's ips, mac and last_seen
            interfaces = device_raw.get('interfaces') if isinstance(device_raw.get('interfaces'), list) else []
            for interface in interfaces:
                interface_data = interface.get('interface_data')
                if interface_data:
                    last_seen_str = interface_data.get('lastSeen')
                    if last_seen_str:
                        interface_last_seen = parse_date(last_seen_str)
                        if last_seen is None or interface_last_seen > last_seen:
                            last_seen = interface_last_seen
                    ips_data = interface_data.get('ips')
                    ips = [x.get('ip').strip() for x in ips_data if x.get('ip')] if isinstance(ips_data, list) else None
                    device.add_nic(interface_data.get('mac'), ips)

            if last_seen:
                device.last_seen = last_seen
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Indegy Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Network]
