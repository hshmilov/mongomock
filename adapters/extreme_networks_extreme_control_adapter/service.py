import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.utils.files import get_local_config_file
from extreme_networks_extreme_control_adapter.connection import ExtremeNetworksExtremeControlConnection
from extreme_networks_extreme_control_adapter.client_id import get_client_id
from extreme_networks_extreme_control_adapter.structures import ExtremeNetworksExtremeControlDeviceInstance, \
    PhysicalPort

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class ExtremeNetworksExtremeControlAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(ExtremeNetworksExtremeControlDeviceInstance):
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
        connection = ExtremeNetworksExtremeControlConnection(domain=client_config['domain'],
                                                             verify_ssl=client_config['verify_ssl'],
                                                             https_proxy=client_config.get('https_proxy'),
                                                             proxy_username=client_config.get('proxy_username'),
                                                             proxy_password=client_config.get('proxy_password'),
                                                             username=client_config['username'],
                                                             password=client_config['password'])
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
        The schema ExtremeNetworksExtremeControlAdapter expects from configs

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
                    'title': 'User ID',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
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
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_extreme_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.system_object_identifier = device_raw.get('sysOid')
            device.site_id = device_raw.get('siteId')
            try:
                device.hardware_mode = device_raw.get('hwMode')
            except Exception:
                logger.warning(f'Invalid hardware mode, got {device_raw.get("hwMode")}')
            device.slot_number = device_raw.get('slotNumber')
            device.host_site = device_raw.get('hostSite')
            device.software_version = device_raw.get('softwareVersion')

            ports = device_raw.get('ports')
            if isinstance(ports, list):
                physical_ports = []
                for port in ports:
                    if isinstance(port, dict):
                        physical_port = PhysicalPort()
                        physical_port.id = port.get('id')
                        physical_port.number = port.get('portNumber')
                        physical_port.name = port.get('string')
                        try:
                            physical_port.port_type = port.get('portType')
                        except Exception:
                            logger.warning(f'Invalid port type, got {port.get("portType")}')
                        physical_port.alias = port.get('portAlias')
                        try:
                            physical_port.speed = port.get('portSpeed')
                        except Exception:
                            logger.warning(f'Invalid port speed, got {port.get("portSpeed")}')
                        physical_port.default_policy = port.get('defaultPolicy')
                        physical_port.vlan_id = port.get('pvid')
                        physical_ports.append(physical_port)
                device.physical_ports = physical_ports
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('serialNumber') or '')

            device.device_serial = device_raw.get('serialNumber')
            device.device_model = device_raw.get('switchType')
            device.description = device_raw.get('sysDescription')
            device.hostname = device_raw.get('systemName')

            os_string = device_raw.get('operatingSystem')
            device.figure_os(os_string=os_string)

            ips = device_raw.get('mgmtIpAddress') or []
            if isinstance(ips, str):
                ips = [ips]
            device.add_nic(mac=device_raw.get('macaddress'),
                           ips=ips,
                           port=device_raw.get('mgmtPort'))

            self._fill_extreme_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching ExtremeNetworksExtremeControl Device for {device_raw}')
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
                logger.exception(f'Problem with fetching ExtremeNetworksExtremeControl Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
