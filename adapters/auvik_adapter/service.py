import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from auvik_adapter.connection import AuvikConnection
from auvik_adapter.client_id import get_client_id
from auvik_adapter.structures import AuvikDeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')


class AuvikAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(AuvikDeviceInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = AuvikConnection(domain=client_config['domain'],
                                     verify_ssl=client_config['verify_ssl'],
                                     https_proxy=client_config.get('https_proxy'),
                                     proxy_username=client_config.get('proxy_username'),
                                     proxy_password=client_config.get('proxy_password'),
                                     username=client_config['username'],
                                     password=client_config['apikey'])
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema AuvikAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Host Name or IP Address',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
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
                    'type': 'string'
                },
                {
                    'name': 'proxy_username',
                    'title': 'HTTPS Proxy User Name',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS Proxy Password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                'domain',
                'username',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_auvik_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            attributes = device_raw.get('attributes')
            if not isinstance(attributes, dict):
                attributes = {}
            device.device_type = attributes.get('deviceType')
            device.software_version = attributes.get('softwareVersion')
            device.firmware_version = attributes.get('firmwareVersion')
            device.last_modified = parse_date(attributes.get('lastModified'))
            device.online_status = attributes.get('onlineStatus')
            device_details_raw = device_raw.get('device_details_raw')
            if not isinstance(device_details_raw, dict):
                device_details_raw = {}
            discovery_status = device_details_raw.get('discoveryStatus')
            if not isinstance(discovery_status, dict):
                discovery_status = {}
            manage_status = device_details_raw.get('manageStatus')
            if isinstance(manage_status, bool):
                device.manage_status = manage_status
            device.traffic_insights_status = device_details_raw.get('trafficInsightsStatus')
            device.discovery_snmp = discovery_status.get('snmp')
            device.discovery_wmi = discovery_status.get('wmi')
            device.discovery_vmware = discovery_status.get('vmware')
            device.discovery_login = discovery_status.get('login')
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id
            attributes = device_raw.get('attributes')
            if not isinstance(attributes, dict):
                attributes = {}
            if attributes.get('ipAddresses'):
                device.add_nic(ips=attributes.get('ipAddresses'))
            device.hostname = attributes.get('deviceName')
            device.device_model = attributes.get('makeModel')
            device.device_manufacturer = attributes.get('vendorName')
            device.device_serial = attributes.get('serialNumber')
            device.description = attributes.get('description')
            device.last_seen = parse_date(attributes.get('lastSeenTime'))
            self._fill_auvik_device_fields(device_raw, device)

            device.set_raw(device_raw)

            return device
        except Exception:
            logger.exception(f'Problem with fetching Auvik Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching Auvik Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
