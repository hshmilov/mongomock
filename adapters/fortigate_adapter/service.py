import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import format_mac
from fortigate_adapter import consts
from fortigate_adapter.client import FortigateClient
from fortigate_adapter.connection import FortimanagerConnection

logger = logging.getLogger(f'axonius.{__name__}')


class FortigateAdapter(AdapterBase, Configurable):
    """
    Connects axonius to Fortigate devices
    """

    class MyDeviceAdapter(DeviceAdapter):
        interface = Field(str, 'Interface')
        fortigate_name = Field(str, 'Fortigate Name')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': consts.FORTIGATE_HOST,
                    'title': 'Host Name',
                    'type': 'string'
                },
                {
                    'name': consts.FORTIGATE_PORT,
                    'title': 'Port',
                    'type': 'integer',
                    'format': 'port'
                },
                {
                    'name': consts.USER,  # The user needs System Configuration Read Privileges.
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': consts.PASSWORD,
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': consts.VDOM,
                    'title': 'Virtual Domain',
                    'type': 'string'
                },
                {  # if false, it will allow for invalid SSL certificates (but still uses HTTPS)
                    'name': consts.VERIFY_SSL,
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': consts.IS_FORTIMANAGER,
                    'title': 'Is Fortimanger Server',
                    'type': 'bool'
                }
            ],
            'required': [
                consts.USER,
                consts.PASSWORD,
                consts.FORTIGATE_HOST,
            ],
            'type': 'array'
        }

    def _create_fortios_device(self, raw_device):
        try:
            # list, than its a device itself
            device = self._new_device_adapter()
            hostname = raw_device.get('hostname')
            device.hostname = hostname
            fortios_name = raw_device.get('fortios_name')
            if not fortios_name:
                logger.error(f'Error no fortios name, this should be client_name')
                return None
            device.fortigate_name = fortios_name
            try:
                mac_address = format_mac(raw_device.get('mac'))
            except Exception:
                mac_address = None
            if not mac_address:
                logger.warning(f'Bad MAC address at device {raw_device}')
                return None
            device.id = 'fortigate_' + fortios_name + '_' + mac_address + '_' + (hostname or '')
            device.add_nic(mac_address, [raw_device.get('ip')] if raw_device.get('ip') else None)

            last_seen = raw_device.get('expire_time')
            # The DHCP lease time is kept in seconds and by getting the dhcp lease expiry - lease time
            # would let us know when the dhcp lease occurred which we would use as last_seen.
            try:
                device.last_seen = datetime.datetime.fromtimestamp(
                    last_seen) - datetime.timedelta(seconds=self.__dhcp_lease_time)
            except Exception:
                logger.exception(f'Problem getting last seen for device {raw_device}')
            device.interface = raw_device.get('interface')
            device.set_raw(raw_device)
            return device
        except Exception:
            logger.exception(f'Problem with device raw {raw_device}')
            return None

    def _create_fortimanager_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            logger.debug(f'DEVICE {device_raw.keys()} RAW {device_raw}')
            hostname = device_raw.get('hostname')
            name = device_raw.get('name')
            if not hostname and not name:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = hostname or name
            device.name = name
            device.hostname = hostname
            try:
                if device_raw.get('last_checked'):
                    device.last_seen = datetime.datetime.fromtimestamp(device_raw.get('last_checked'))
            except Exception:
                logger.exception(f'Problem setting last seen to {device_raw}')
            try:
                ip = device_raw.get('ip')
                if ip:
                    device.add_nic(None, [ip])
            except Exception:
                logger.exception(f'Problem adding NIC to {device_raw}')
            device.adapter_properties = [AdapterProperty.Manager.name, AdapterProperty.Network.name]
            device.set_raw({})
            return device
        except Exception:
            logger.exception(f'Problem with device raw {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):

        for raw_device, device_type in devices_raw_data:
            device = None
            if device_type == 'fortios_device':
                device = self._create_fortios_device(raw_device)
            if device_type == 'fortimanager_device':
                device = self._create_fortimanager_device(raw_device)
            if device:
                yield device

    def _query_devices_by_client(self, client_name, client_data):
        client_data, client_type = client_data
        if client_type == 'fortios':
            yield from client_data.get_all_devices(client_name)
        if client_type == 'fortimanager':
            with client_data:
                yield from client_data.get_device_list()

    def _get_client_id(self, client_config):
        return f'{client_config[consts.FORTIGATE_HOST]}:' \
               f'{client_config.get(consts.FORTIGATE_PORT, consts.DEFAULT_FORTIGATE_PORT)}'

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get(consts.FORTIGATE_HOST),
                                                client_config.get(consts.FORTIGATE_PORT, consts.DEFAULT_FORTIGATE_PORT))

    def _connect_client(self, client_config):
        try:
            if client_config.get(consts.IS_FORTIMANAGER) is True \
                    or 'fortianalyzer' in client_config[consts.FORTIGATE_HOST]:
                connection = FortimanagerConnection(domain=client_config[consts.FORTIGATE_HOST],
                                                    verify_ssl=client_config[consts.VERIFY_SSL],
                                                    username=client_config[consts.USER],
                                                    password=client_config[consts.PASSWORD],
                                                    port=client_config.get(consts.FORTIGATE_PORT))
                with connection:
                    pass  # check that the connection credentials are valid
                return connection, 'fortimanager'
            return FortigateClient(**client_config), 'fortios'
        except Exception as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config[consts.FORTIGATE_HOST], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network, AdapterProperty.Firewall]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': consts.DHCP_LEASE_TIME,
                    'title': 'DHCP Lease Time (In Seconds)',
                    'type': 'integer'
                }
            ],
            'required': [
                'onsts.DHCP_LEASE_TIME'
            ],
            'pretty_name': 'Fortigate Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            consts.DHCP_LEASE_TIME: consts.DEFAULT_DHCP_LEASE_TIME,
        }

    def _on_config_update(self, config):
        self.__dhcp_lease_time = config[consts.DHCP_LEASE_TIME]
