import logging
from enum import Enum, auto

from pyVmomi import vim

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter, DeviceRunningState
from axonius.fields import Field
from axonius.utils.datetime import parse_date
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


class EsxAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        vm_tools_status = Field(str, 'VM Tools Status')
        vm_physical_path = Field(str, 'VM physical path')
        device_type = Field(ESXDeviceType, 'VM type')
        esx_host = Field(str, 'VM ESX Host')

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
            return vCenterApi(
                host=host,
                user=client_config['user'],
                password=client_config['password'],
                verify_ssl=client_config['verify_ssl'],
                restful_api_url=client_config.get('rest_api', f'https://{host}/api'),
            )
        except vim.fault.InvalidLogin as e:
            message = 'Credentials invalid for ESX client for account {0}'.format(client_id)
            logger.exception(message)
        except vim.fault.HostConnectFault as e:
            message = 'Unable to access vCenter, text={}, host = {}'.format(e.msg, client_config['host'])
            logger.exception(message)
        except Exception as e:
            message = 'Unknown error on account {}, text={}'.format(client_id, str(e))
            logger.exception(message)
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
        return rawify_vcenter_data(client_data.get_all_vms())

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
        device.figure_os(config.get('guestFullName', ''))
        try:
            device.id = details['config']['instanceUuid']
            device.cloud_id = details['config']['instanceUuid']
        except KeyError:
            device.id = device.name  # default to name

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

        for hwdevice in details.get('hardware', {}).get('devices', []):
            if 'macAddress' in hwdevice and hwdevice['macAddress'] not in added_macs:
                device.add_nic(mac=hwdevice['macAddress'])

        for hwdevice in details.get('hardware_networking', {}):
            device.add_nic(**hwdevice)

        device.esx_host = details.get('esx_host_name', None)
        device.hostname = guest.get('hostName', '')
        device.vm_tools_status = guest.get('toolsStatus', '')
        device.vm_physical_path = _curr_path + '/' + node.get('Name', '')
        device.power_state = POWER_STATE_MAP.get(
            details.get('runtime', {}).get('powerState'), DeviceRunningState.Unknown
        )
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

    def _parse_raw_data(self, node, _curr_path: str = ''):
        """
        Parses the vms as returned from _query_devices_by_client to the format Aggregator wants

        :param node:
        :param _curr_path: internally used
        :return: iterator(dict)
        """
        if node is None:
            return
        node_type = node.get('Type')
        if not node_type:
            return
        if node_type == 'Template':
            return
        elif node_type == 'Machine':
            try:
                device = self._parse_vm_machine(node, _curr_path)
                device.device_type = ESXDeviceType.VMMachine
                yield device
            except Exception:
                logger.exception('Problem getting machine')
                return
        elif node_type == 'ESXHost':
            try:
                device = self._parse_vm_machine(node, _curr_path)
            except Exception:
                logger.exception('Problem getting esx host')
                return
            if device is None:
                return
            try:
                details = node.get('Details', {})
                if details and details.get('config'):
                    device.hostname = details.get('config').get('name')
            except Exception:
                logger.exception(f'Problem getting ESX Host name ')
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
                    yield from self._parse_raw_data(child, _curr_path + '/' + node['Name'])
                except Exception:
                    logger.exception(f'Problem getting special thing')
                    continue
        else:
            raise RuntimeError('Found weird type of node: {}'.format(node['Type']))

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Virtualization]
