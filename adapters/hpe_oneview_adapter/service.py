import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.hpe_oneview.connection import HpeOneviewConnection
from axonius.clients.hpe_oneview.consts import POWER_STATE_DICT
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, int_or_none, MB_TO_GB_CONVERT
from hpe_oneview_adapter.client_id import get_client_id
from hpe_oneview_adapter.structures import HpeOneviewDeviceInstance, DeviceSlot

logger = logging.getLogger(f'axonius.{__name__}')


class HpeOneviewAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(HpeOneviewDeviceInstance):
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
        connection = HpeOneviewConnection(domain=client_config.get('domain'),
                                          verify_ssl=client_config.get('verify_ssl'),
                                          https_proxy=client_config.get('https_proxy'),
                                          proxy_username=client_config.get('proxy_username'),
                                          proxy_password=client_config.get('proxy_password'),
                                          username=client_config.get('username'),
                                          password=client_config.get('password'),
                                          username_domain=client_config.get('username_domain'))
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
        The schema HpeOneviewAdapter expects from configs

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
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'username_domain',
                    'title': 'Authentication Login Domain',
                    'type': 'string'
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

    # pylint: disable=too-many-locals, too-many-nested-blocks, too-many-branches, too-many-statements
    @staticmethod
    def _fill_hpe_oneview_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.asset_tag = device_raw.get('asset_tag')
            if isinstance(device_raw.get('capabilities'), list):
                device.capabilities = device_raw.get('capabilities')
            device.category = device_raw.get('category')
            device.etag = device_raw.get('eTag')
            device.form_factor = device_raw.get('formFactor')
            device.generation = device_raw.get('generation')
            device.intelligent_provisioning_version = device_raw.get('intelligentProvisioningVersion')
            device.licensing_intent = device_raw.get('licensingIntent')
            device.location_uri = device_raw.get('locationUri')
            device.maintenance_state = device_raw.get('maintenanceState')
            device.maintenance_state_reason = device_raw.get('maintenanceStateReason')
            device.migration_state = device_raw.get('migrationState')
            device.modified = parse_date(device_raw.get('modified'))
            device.mp_firmware_version = device_raw.get('mpFirmwareVersion')
            device.rom_version = device_raw.get('romVersion')
            device.refresh_state = device_raw.get('refreshState')
            device.one_time_boot = device_raw.get('oneTimeBoot')
            device.mp_model = device_raw.get('mpModel')
            device.mp_state = device_raw.get('mpState')
            device.part_number = device_raw.get('partNumber')
            device.physical_server_hardware_uri = device_raw.get('physicalServerHardwareUri')
            device.platform = device_raw.get('platform')
            device.position = device_raw.get('position')
            device.power_lock = parse_bool_from_raw(device_raw.get('powerLock'))
            device.device_state = device_raw.get('state')
            device.device_status = device_raw.get('status')
            device_slots = device_raw.get('deviceSlots')
            if not isinstance(device_slots, list):
                device_slots = []
            for device_slot in device_slots:
                try:
                    if not isinstance(device_slot, dict):
                        continue
                    device.device_slots.append(DeviceSlot(device_name=device_slot.get('deviceName'),
                                                          location=device_slot.get('location')))
                    physical_ports = device_slot.get('physicalPorts')
                    if not isinstance(physical_ports, list):
                        physical_ports = []
                    for physical_port in physical_ports:
                        try:
                            if not isinstance(physical_port, dict):
                                continue
                            mac = physical_port.get('mac')
                            port_number = physical_port.get('portNumber')
                            if port_number:
                                port_number = str(port_number)
                            if mac:
                                device.add_nic(mac=mac,
                                               port=port_number,
                                               port_type=physical_port.get('type'))
                        except Exception:
                            logger.exception(f'Problem with Physical port')
                except Exception:
                    logger.exception(f'Problem with Device slot {device_slot}')

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('serverName')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('serialNumber') or '')
            device.device_serial = device_raw.get('serialNumber')
            device.description = device_raw.get('description')
            device.name = device_raw.get('serverName')
            device.first_seen = parse_date(device_raw.get('created'))
            device.figure_os(device_raw.get('hostOsType'))
            device.device_model = device_raw.get('model')
            device.total_number_of_physical_processors = int_or_none(device_raw.get('processorCount'))
            device.power_state = POWER_STATE_DICT.get(device_raw.get('powerState'))
            if isinstance(device_raw.get('memoryMb'), int):
                device.total_physical_memory = device_raw.get('memoryMb') / MB_TO_GB_CONVERT
            mp_host_info = device_raw.get('mpHostInfo')
            if not isinstance(mp_host_info, dict):
                mp_host_info = {}
            device.hostname = mp_host_info.get('mpHostName')
            ips_raw = mp_host_info.get('mpIpAddresses')
            if not isinstance(ips_raw, list):
                ips_raw = []
            for ip_raw in ips_raw:
                try:
                    if not isinstance(ip_raw, dict):
                        continue
                    device.add_nic(ips=[ip_raw.get('address')])
                except Exception:
                    logger.exception(f'Problem with ip {ip_raw}')
            self._fill_hpe_oneview_device_fields(device_raw, device)
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching HpeOneview Device for {device_raw}')
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
                logger.exception(f'Problem with fetching HpeOneview Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Agent]
