import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.utils.files import get_local_config_file
from axonius.clients.rest.connection import RESTException
from axonius.utils.datetime import parse_date
from axonius.fields import Field, ListField
from tanium_adapter.connection import TaniumConnection
from tanium_adapter.consts import ENDPOINT_TYPE, DISCOVERY_TYPE, DISCOVER_METHODS

logger = logging.getLogger(f'axonius.{__name__}')


class TaniumAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        tanium_type = Field(str, 'Tanium Device Type', enum=[ENDPOINT_TYPE, DISCOVERY_TYPE])
        created_at = Field(datetime.datetime, 'Created At')
        updated_at = Field(datetime.datetime, 'Updated At')
        is_managed = Field(bool, 'Is Managed')
        unmanageable = Field(bool, 'Unmanageable')
        ignored = Field(bool, 'Ignored')
        methods_used = ListField(str, 'Methods Used')
        natipaddress = Field(str, 'NAT IP Address')
        discovery_tags = ListField(str, 'Discovery Tags')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return client_config['domain']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def get_connection(client_config):
        connection = TaniumConnection(domain=client_config['domain'],
                                      verify_ssl=client_config['verify_ssl'],
                                      username=client_config['username'],
                                      password=client_config['password'],
                                      https_proxy=client_config.get('https_proxy'))
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config), (client_config.get('fetch_discovery') or False)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Tanium domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Tanium connection

        :return: A json with all the attributes returned from the Tanium Server
        """
        connection, fetch_discovery = client_data
        with connection:
            yield from connection.get_device_list(fetch_discovery=fetch_discovery)

    @staticmethod
    def _clients_schema():
        """
        The schema TaniumAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Tanium Domain',
                    'type': 'string'
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
                    'name': 'fetch_discovery',
                    'type': 'bool',
                    'title': 'Fetch Tanium Discover Devices'
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
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'verify_ssl',
                'fetch_discovery'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _create_endpoint_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device.tanium_type = ENDPOINT_TYPE
            device_id = device_raw.get('computer_id')
            if not device_id:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + device_raw.get('host_name')
            device.uuid = str(device_raw.get('computer_id')) if device_raw.get('computer_id') else None
            hostname = device_raw.get('host_name')
            if hostname and hostname.endswith('(none)'):
                hostname = hostname[:-len('(none)')]
            device.hostname = hostname
            device.add_agent_version(agent=AGENT_NAMES.tanium, version=device_raw.get('full_version'))
            device.last_seen = parse_date(device_raw.get('last_registration'))
            ip_address = device_raw.get('ipaddress_client')
            if ip_address:
                device.add_nic(None, ip_address.split(','))
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Tanium Device {device_raw}')
            return None

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _create_discovery_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device.tanium_type = DISCOVERY_TYPE
            device_id = device_raw.get('macaddress')
            if not device_id:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + str(device_raw.get('computerid'))
            ips = [device_raw.get('ipaddress')] if device_raw.get('ipaddress') else None
            device.add_nic(mac=device_raw.get('macaddress'), ips=ips)
            device.uuid = str(device_raw.get('computerid')) if device_raw.get('computerid') else None
            device.natipaddress = device_raw.get('natipaddress')
            device.hostname = device_raw.get('hostname')
            try:
                if isinstance(device_raw.get('tags'), str) and device_raw.get('tags'):
                    device.discovery_tags = device_raw.get('tags').split(',')
            except Exception:
                logger.exception(f'Problem getting tags for {device_raw}')
            try:
                if isinstance(device_raw.get('ports'), str) and device_raw.get('ports'):
                    for port_raw in device_raw.get('ports').split(','):
                        device.add_open_port(port_id=port_raw)
            except Exception:
                logger.exception(f'Problem getting ports for {device_raw}')
            device.figure_os(device_raw.get('os'))
            try:
                if isinstance(device_raw.get('method'), str) and device_raw.get('method'):
                    methods = device_raw.get('method').split(',')
                    methods_used = dict(zip(DISCOVER_METHODS, methods))
                    for key, value in methods_used.items():
                        if value == '1':
                            device.methods_used.append(key)
            except Exception:
                logger.exception(f'Problem getting methods for {device_raw}')
            device.updated_at = parse_date(device_raw.get('updatedAt'))
            device.last_seen = parse_date(device_raw.get('lastDiscoveredAt'))
            device.created_at = parse_date(device_raw.get('createdAt'))
            device.first_seen = parse_date(device_raw.get('createdAt'))
            if isinstance(device_raw.get('unmanageable'), int):
                device.unmanageable = device_raw.get('unmanageable') == 1
            if isinstance(device_raw.get('ismanaged'), int):
                device.is_managed = device_raw.get('ismanaged') == 1
            if isinstance(device_raw.get('ignored'), int):
                device.ignored = device_raw.get('ignored') == 1
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Tanium Device {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, device_type in devices_raw_data:
            device = None
            if device_type == ENDPOINT_TYPE:
                device = self._create_endpoint_device(device_raw)
            elif device_type == DISCOVERY_TYPE:
                device = self._create_discovery_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
