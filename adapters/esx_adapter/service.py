import datetime
import logging
from enum import Enum, auto
from urllib3.util.url import parse_url


from pyVmomi import vim

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter, DeviceRunningState
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.datetime import parse_date
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from esx_adapter.vcenter_api import rawify_vcenter_data, vCenterApi

logger = logging.getLogger(f'axonius.{__name__}')


# translation table between ESX values to parsed values
POWER_STATE_MAP = {
    'poweredOff': DeviceRunningState.TurnedOff,
    'poweredOn': DeviceRunningState.TurnedOn,
    'suspended': DeviceRunningState.Suspended,
}


class ESXDeviceType(Enum):
    """ Defines the state of device. i.e. if it is turned on or not """

    def _generate_next_value_(name, *args):
        return name

    ESXHost = auto()
    VMMachine = auto()


class ESXIdentifyingInfo(SmartJsonClass):
    key = Field(str, 'Type')
    value = Field(str, 'Value')


class EsxAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        connection_hostname = Field(str, 'ESX/VCenter UI Hostname')
        vm_tools_status = Field(str, 'VM Tools Status')
        vm_physical_path = Field(str, 'VM physical path')
        device_type = Field(ESXDeviceType, 'VM type')
        esx_host = Field(str, 'VM ESX Host')
        hds_total = Field(float, 'Total HDs Size (GB)')
        vm_path_name = Field(str, 'VM Path Name')
        consolidation_needed = Field(bool, 'Consolidation Needed')
        cd_summaries = ListField(str, 'CD/DVD Summaries')
        system_identifying_info = ListField(ESXIdentifyingInfo, 'Identifying Info')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return '{}/{}'.format(client_config['host'], client_config['user'])

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('host'))

    def _connect_client(self, client_config):
        client_id = self._get_client_id(client_config)
        try:
            host = client_config['host']
            url_parsed = parse_url(host)
            host = url_parsed.host
            return vCenterApi(
                host=host,
                user=client_config['user'],
                password=client_config['password'],
                verify_ssl=client_config['verify_ssl'],
                restful_api_url=client_config.get('rest_api', f'https://{host}/api'),
            ), host
        except vim.fault.InvalidLogin as e:
            message = 'Credentials invalid for ESX client for account {0}'.format(client_id)
            logger.warning(message, exc_info=True)
        except vim.fault.HostConnectFault as e:
            message = 'Unable to access vCenter, text={}, host = {}'.format(e.msg, client_config['host'])
            logger.warning(message, exc_info=True)
        except Exception as e:
            message = 'Unknown error on account {}, text={}'.format(client_id, str(e))
            logger.warning(message, exc_info=True)
        raise ClientConnectionException(message)

    def _clients_schema(self):
        """
        The schema ESXAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {'name': 'host', 'title': 'Host', 'type': 'string'},
                {'name': 'user', 'title': 'User', 'type': 'string'},
                {'name': 'password', 'title': 'Password', 'type': 'string', 'format': 'password'},
                {  # if false, it will allow for invalid SSL certificates (but still uses HTTPS)
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool',
                },
                {'name': 'rest_api', 'title': 'vCenter RESTful API URL', 'default': None, 'type': 'string'},
            ],
            'required': ['host', 'user', 'password', 'verify_ssl'],
            'type': 'array',
        }

    def _query_devices_by_client(self, client_name, client_data):
        connection, host = client_data
        return rawify_vcenter_data(connection.get_all_vms()), host

    def _parse_vm_machine(self, node, _curr_path):
        details = node.get('Details', {})
        if not details:
            return None
        guest = details.get('guest', {})
        config = details.get('config', {})

        device = self._new_device_adapter()

        tags = details.get('tags')
        if tags:
            for tag in tags:
                device.add_key_value_tag(*tag)

        device.name = node.get('Name', '')
        device.vm_path_name = config.get('vmPathName')
        device.figure_os(config.get('guestFullName', ''))

        # set device uuid according to http://www.virtu-al.net/2015/12/04/a-quick-reference-of-vsphere-ids/
        device_uuid = None
        if (details.get('esx_system_info') or {}).get('uuid'):
            # 2. ESX Host UUID
            device_uuid = details['esx_system_info']['uuid']
        elif config.get('uuid'):
            # 4. VM SMBIOS UUID
            device_uuid = config['uuid']
        if not device_uuid:
            logger.warning(f'Missing device UUID for path "{_curr_path}"')
        device.uuid = device_uuid

        device_id = device.name  # default to name
        if config.get('instanceUuid'):
            device_id = config['instanceUuid']
        elif details.get('esx_system_info'):  # set ESXHosts' IDs to be their uuid
            device_id = device_uuid or device_id
        device.id = device_id
        device.cloud_id = device_id

        device.cloud_provider = 'VMWare'
        added_macs = []
        for iface in details.get('networking', []):
            ips = [addr['ipAddress'] for addr in iface.get('ipAddresses', [])]
            if ips:
                added_macs.append(iface.get('macAddress'))
                device.add_nic(iface.get('macAddress'), ips)
        if not device.network_interfaces and 'ipAddress' in guest:
            # if nothing is found in raw.networking this will be used
            device.add_nic('', [guest.get('ipAddress')])
        hds_total = 0
        for hwdevice in details.get('hardware', {}).get('devices', []):
            try:
                if 'macAddress' in hwdevice and hwdevice['macAddress'] not in added_macs:
                    device.add_nic(mac=hwdevice['macAddress'])
                elif 'capacityInKB' in hwdevice and isinstance(hwdevice['capacityInKB'], int):
                    device_name = (hwdevice.get('deviceInfo') or {}).get('label')
                    total_size = hwdevice['capacityInKB'] / (1024.0 ** 2)
                    hds_total += total_size
                    device.add_hd(total_size=total_size, device=device_name)
                elif 'CD/DVD' in (hwdevice.get('deviceInfo') or {}).get('label') or '':
                    device.cd_summaries.append((hwdevice.get('deviceInfo') or {}).get('summary'))
            except Exception:
                logger.warning(f'Problem with hardware device', exc_info=True)
        if hds_total:
            device.hds_total = hds_total
        for hwdevice in details.get('hardware_networking', {}):
            device.add_nic(**hwdevice)

        device.esx_host = details.get('esx_host_name', None)
        device.hostname = guest.get('hostName', '')
        device.vm_tools_status = guest.get('toolsStatus', '')
        device.vm_physical_path = _curr_path + '/' + node.get('Name', '')
        device.power_state = POWER_STATE_MAP.get(
            details.get('runtime', {}).get('powerState'), DeviceRunningState.Unknown
        )
        try:
            if details.get('runtime', {}).get('powerState') == 'poweredOn':
                device.last_seen = datetime.datetime.now()
            elif self.__fetch_only_turned_on_machines:
                return None
        except Exception:
            logger.warning(f'Problem addding last seen for {details}', exc_info=True)
        if isinstance((details.get('runtime') or {}).get('consolidationNeeded'), bool):
            device.consolidation_needed = (details.get('runtime') or {}).get('consolidationNeeded')
        boot_time = details.get('runtime', {}).get('bootTime')
        if boot_time is not None:
            device.set_boot_time(boot_time=parse_date(boot_time))

        memory_size_mb = config.get('memorySizeMB')
        if memory_size_mb is not None:
            device.total_physical_memory = memory_size_mb / 1024.0
        total_num_of_cpus = config.get('numCpu')
        if total_num_of_cpus is not None:
            device.total_number_of_physical_processors = int(total_num_of_cpus)

        device.set_raw(details)
        return device

    def _parse_raw_data(self, raw_data, _curr_path: str = ''):
        """
        Parses the vms as returned from _query_devices_by_client to the format Aggregator wants

        :param node:
        :param _curr_path: internally used
        :return: iterator(dict)
        """
        if raw_data is None:
            return
        node, connection_hostname = raw_data
        node_type = node.get('Type')
        if not node_type:
            return
        if node_type == 'Template':
            return
        elif node_type == 'Machine':
            try:
                device = self._parse_vm_machine(node, _curr_path)
                device.device_type = ESXDeviceType.VMMachine
                device.connection_hostname = connection_hostname
                yield device
            except Exception:
                logger.warning('Problem getting machine', exc_info=True)
                return
        elif node_type == 'ESXHost':
            try:
                device = self._parse_vm_machine(node, _curr_path)
            except Exception:
                logger.warning('Problem getting esx host', exc_info=True)
                return
            if device is None:
                return
            try:
                details = node.get('Details', {})
                if details:
                    if details.get('config'):
                        device.hostname = details.get('config').get('name')
                    if details.get('esx_bios_info'):
                        bios_info = details.get('esx_bios_info') or {}
                        device.bios_manufacturer = bios_info.get('vendor')
                        device.bios_version = bios_info.get('biosVersion')
                    if details.get('esx_system_info'):
                        system_info = details.get('esx_system_info') or {}
                        device.device_manufacturer = system_info.get('vendor')
                        device.device_model = system_info.get('model')
                        # Available from ESXi 6.7
                        device.device_serial = system_info.get('serialNumber')
                        other_info_list = system_info.get('otherIdentifyingInfo') or []
                        identifying_info_list = []
                        for other_info in other_info_list:  # type: dict
                            key = other_info.get('key')
                            if not key:
                                continue
                            value = other_info.get('value')
                            identifying_info_list.append(ESXIdentifyingInfo(key=key, value=value))
                        device.system_identifying_info = identifying_info_list

            except Exception:
                logger.warning(f'Problem getting ESX Host name ', exc_info=True)
            device.connection_hostname = connection_hostname
            device.device_type = ESXDeviceType.ESXHost
            node_hardware = node.get('Hardware')
            if node_hardware:
                device.add_cpu(
                    cores=node_hardware['numCpuThreads'],
                    ghz=node_hardware['totalCpu'] / node_hardware['numCpuCores'] / 1024,
                )
                device.total_physical_memory = node_hardware['totalMemory'] / (1024.0 * 1024 * 1024)
            yield device
        elif node_type in ('Datacenter', 'Folder', 'Root', 'Cluster'):
            for child in node.get('Children', [{}]):
                try:
                    yield from self._parse_raw_data((child, connection_hostname), _curr_path + '/' + node['Name'])
                except Exception:
                    logger.warning(f'Problem getting special thing', exc_info=True)
                    continue
        else:
            raise RuntimeError('Found weird type of node: {}'.format(node['Type']))

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Virtualization]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'fetch_only_turned_on_machines',
                    'title': 'Fetch only turned on machines',
                    'type': 'bool'
                }
            ],
            'required': [
                'fetch_only_turned_on_machines'
            ],
            'pretty_name': 'ESX Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'fetch_only_turned_on_machines': False
        }

    def _on_config_update(self, config):
        self.__fetch_only_turned_on_machines = config.get('fetch_only_turned_on_machines') or False
