import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from cisco_ise_adapter.connection import CiscoIseConnection
from cisco_ise_adapter.client_id import get_client_id
from cisco_ise_adapter.consts import CLIENT_CONFIG_FIELDS, CLIENT_CONFIG_TITLES, REQUIRED_SCHEMA_FIELDS

logger = logging.getLogger(f'axonius.{__name__}')


class CiscoIseAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        fields = CLIENT_CONFIG_FIELDS
        return CiscoIseConnection.test_reachability(domain=client_config.get(fields.domain),
                                                    verify_ssl=client_config.get(fields.verify_ssl) or False)

    @staticmethod
    def get_connection(client_config):
        fields = CLIENT_CONFIG_FIELDS
        connection = CiscoIseConnection(domain=client_config[fields.domain],
                                        verify_ssl=client_config[fields.verify_ssl],
                                        https_proxy=client_config.get(fields.https_proxy),
                                        username=client_config[fields.username],
                                        password=client_config[fields.password])
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config[CLIENT_CONFIG_FIELDS.domain], str(e))
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
        The schema CiscoIseAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': CLIENT_CONFIG_FIELDS.domain,
                    'title': CLIENT_CONFIG_TITLES.domain,
                    'type': 'string'
                },
                {
                    'name': CLIENT_CONFIG_FIELDS.domain,
                    'title': CLIENT_CONFIG_TITLES.domain,
                    'type': 'string'
                },
                {
                    'name': CLIENT_CONFIG_FIELDS.password,
                    'title': CLIENT_CONFIG_TITLES.password,
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': CLIENT_CONFIG_FIELDS.verify_ssl,
                    'title': CLIENT_CONFIG_TITLES.verify_ssl,
                    'type': 'bool'
                },
                {
                    'name': CLIENT_CONFIG_FIELDS.https_proxy,
                    'title': CLIENT_CONFIG_TITLES.https_proxy,
                    'type': 'bool'
                },
            ],
            'required': REQUIRED_SCHEMA_FIELDS,
            'type': 'array',
        }

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('@id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id
            device.name = device_raw.get('@name')
            try:
                ips = []
                for iface in device_raw.get('NetworkDeviceIPList', []):
                    ip = iface.get('ipaddress')
                    if ip:
                        ips.append(ip)

                self.add_ips_and_macs(ips=ips)
            except Exception:
                logger.exception('Unable to set networkdeviceIPList')

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching CiscoIse Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
