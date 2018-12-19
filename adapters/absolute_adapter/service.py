import logging
import datetime

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import is_domain_valid
from axonius.fields import Field
from absolute_adapter.connection import AbsoluteConnection
from absolute_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class AbsoluteAdapter(AdapterBase):
    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        public_ip = Field(str, 'Public IP')
        is_stes_active = Field(bool, 'Is STES Active')
        is_stolen = Field(bool, 'Is Active')
        last_updated = Field(datetime.datetime, 'Last Updated')
        device_origin = Field(str, 'Origin')
        device_src = Field(str, 'Device Src')
        policy_group_name = Field(str, 'Policy Group Name')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def _connect_client(client_config):
        try:
            connection = AbsoluteConnection(domain=client_config['domain'],
                                            verify_ssl=client_config['verify_ssl'],
                                            token_id=client_config['token_id'],
                                            client_secret=client_config['client_secret'],
                                            data_center=client_config['data_center'])
            with connection:
                pass
            return connection
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
        The schema AbsoluteAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Absolute Domain',
                    'type': 'string'
                },
                {
                    'name': 'data_center',
                    'title': 'Data Center',
                    'type': 'string'
                },
                {
                    'name': 'token_id',
                    'title': 'Token ID',
                    'type': 'string'
                },
                {
                    'name': 'client_secret',
                    'title': 'Client Secret',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                }
            ],
            'required': [
                'domain',
                'data_center',
                'verify_ssl',
                'client_secret',
                'token_id'
            ],
            'type': 'array'
        }

    # pylint: disable=R0912,R0915
    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('id')
                if not device_id:
                    logger.warning(f'Bad device with no id {device_raw}')
                    continue
                device.id = device_id + '_' + (device_raw.get('fullSystemName') or '')
                hostname = device_raw.get('fullSystemName') or device_raw.get('systemName')
                if hostname and hostname.lower().endswith('.local'):
                    hostname = hostname[:-len('.local')]
                if hostname and hostname.lower().endswith('.workgroup'):
                    hostname = hostname[:-len('.workgroup')]
                device.hostname = hostname
                try:
                    if device_raw.get('lastUpdatedUtc'):
                        device.last_updated = datetime.datetime.fromtimestamp(device_raw.get('lastUpdatedUtc') / 1000)
                except Exception:
                    logger.exception(f'Problem adding last seen to {device_raw}')
                try:
                    if device_raw.get('lastConnectedUtc'):
                        device.last_seen = datetime.datetime.fromtimestamp(device_raw.get('lastConnectedUtc') / 1000)
                except Exception:
                    logger.exception(f'Problem adding last updated to {device_raw}')
                device.device_model = device_raw.get('systemModel')
                device.device_manufacturer = device_raw.get('systemManufacturer')
                device.device_serial = device_raw.get('serial')
                domain = device_raw.get('domain')
                if is_domain_valid(domain):
                    device.part_of_domain = True
                    device.domain = domain
                else:
                    device.part_of_domain = False
                if device_raw.get('username'):
                    device.last_used_users = [device_raw.get('username')]
                if isinstance(device_raw.get('totalPhysicalRamBytes'), int):
                    device.total_physical_memory = device_raw.get('totalPhysicalRamBytes') / (1024**3)
                if isinstance(device_raw.get('availablePhysicalRamBytes'), int):
                    device.free_physical_memory = device_raw.get('availablePhysicalRamBytes') / (1024**3)
                bios_details = device_raw.get('bios')
                if bios_details and isinstance(bios_details, dict):
                    device.bios_serial = bios_details.get('serialNumber')
                    device.bios_version = bios_details.get('version')
                volumes_raw = device_raw.get('volumes')
                if not isinstance(volumes_raw, list):
                    volumes_raw = []
                for volume_raw in volumes_raw:
                    try:
                        device.add_hd(name=volume_raw.get('name'),
                                      file_system=volume_raw.get('fileSystem'),
                                      total_size=float(device_raw.get('sizeBytes') or 0) / (1024**3),
                                      free_size=float(device_raw.get('freeSpaceBytes') or 0) / (1024 ** 3))
                    except Exception:
                        logger.exception(f'Problem adding disk {volume_raw}')
                try:
                    cpu_info = device_raw.get('cpu')
                    if cpu_info:
                        device.add_cpu(bitness=cpu_info.get('dataWidth'),
                                       name=cpu_info.get('name'),
                                       cores=cpu_info.get('logicalCores'),
                                       ghz=(cpu_info.get('processorSpeed') or 0) / 1024.0)
                except Exception:
                    logger.exception(f'Problem adding cpu to {device_raw}')
                device.device_src = device_raw.get('src')
                device.policy_group_name = device_raw.get('policyGroupName')
                device.origin = device_raw.get('origin')
                device.is_stolen = device_raw.get('isStolen')
                device.is_stes_active = device_raw.get('isCTESActive')
                device.public_ip = device_raw.get('publicIp')
                nics = device_raw.get('networkAdapters')
                if not isinstance(nics, list):
                    nics = []
                for nic_raw in nics:
                    try:
                        ipv4 = nic_raw.get('ipV4Address')
                        ipv6 = nic_raw.get('ipV6Address')
                        ips = []
                        if ipv4:
                            ips.append(ipv4)
                        if ipv6:
                            ips.append(ipv6)
                        if not ips:
                            ips = None
                        mac = device_raw.get('macAddress')
                        if not mac:
                            mac = None
                        if ips or mac:
                            device.add_nic(mac, ips, speed=str(nic_raw.get('speed')) is nic_raw.get('speed'))
                    except Exception:
                        logger.exception(f'Problem adding nic to {device_raw} nic {nic_raw}')
                device.figure_os((device_raw.get('os') or {}).get('name'))
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Absolute Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
