from enum import Enum, auto
from pyVmomi import vim

from axonius.adapter_base import AdapterBase, DeviceRunningState
from axonius.adapter_exceptions import ClientConnectionException
from axonius.device import Device
from axonius.fields import Field
from axonius.parsing_utils import parse_date
from axonius.utils.files import get_local_config_file
from esx_adapter.vcenter_api import vCenterApi, rawify_vcenter_data


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
    class MyDevice(Device):
        vm_tools_status = Field(str, 'VM Tools Status')
        vm_physical_path = Field(str, 'VM physical path')
        power_state = Field(DeviceRunningState, 'VM Power state')
        device_type = Field(ESXDeviceType, 'VM type')
        esx_host = Field(str, 'VM ESX Host')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return '{}/{}'.format(client_config['host'], client_config['user'])

    def _connect_client(self, client_config):
        client_id = self._get_client_id(client_config)
        try:
            return vCenterApi(self.logger,
                              host=client_config['host'], user=client_config['user'],
                              password=client_config['password'],
                              verify_ssl=client_config['verify_ssl'])
        except vim.fault.InvalidLogin as e:
            message = "Credentials invalid for ESX client for account {0}".format(client_id)
            self.logger.error(message)
        except vim.fault.HostConnectFault as e:
            message = "Unable to access vCenter, text={}, host = {}".format(e.msg, client_config['host'])
            self.logger.exception(message)
        except Exception as e:
            message = "Unknown error on account {}, text={}".format(client_id, str(e))
            self.logger.exception(message)
        raise ClientConnectionException(message)

    def _clients_schema(self):
        """
        The schema ESXAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "host",
                    "title": "Host",
                    "type": "string"
                },
                {
                    "name": "user",
                    "title": "User",
                    "type": "string"
                },
                {
                    "name": "password",
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },
                {  # if false, it will allow for invalid SSL certificates (but still uses HTTPS)
                    "name": "verify_ssl",
                    "title": "Verify SSL",
                    "type": "bool"
                }
            ],
            "required": [
                "host",
                "user",
                "password",
                "verify_ssl"
            ],
            "type": "array"
        }

    def _query_devices_by_client(self, client_name, client_data):
        return rawify_vcenter_data(client_data.get_all_vms())

    def _parse_vm_machine(self, node, _curr_path):
        details = node.get('Details', {})
        if not details:
            return None
        guest = details.get('guest', {})
        config = details.get('config', {})

        device = self._new_device()
        device.name = node.get('Name', '')
        device.figure_os(config.get('guestFullName', ''))
        try:
            device.id = details['config']['instanceUuid']
        except KeyError:
            device.id = device.name  # default to name

        added_macs = []
        device.network_interfaces = []
        for iface in details.get('networking', []):
            ips = [addr['ipAddress'] for addr in iface.get('ipAddresses', [])]
            if ips:
                added_macs.append(iface.get('macAddress'))
                device.add_nic(iface.get('macAddress'), ips, self.logger)
        if not device.network_interfaces and 'ipAddress' in guest:
            # if nothing is found in raw.networking this will be used
            device.add_nic('', [guest.get('ipAddress')], self.logger)

        for hwdevice in details.get('hardware', {}).get('devices', []):
            if 'macAddress' in hwdevice and hwdevice['macAddress'] not in added_macs:
                device.add_nic(mac=hwdevice['macAddress'])

        device.esx_host = details.get('esx_host_name', None)
        device.hostname = guest.get('hostName', '')
        device.vm_tools_status = guest.get('toolsStatus', '')
        device.vm_physical_path = _curr_path + "/" + node.get('Name', '')
        device.power_state = POWER_STATE_MAP.get(details.get('runtime', {}).get('powerState'),
                                                 DeviceRunningState.Unknown)
        boot_time = details.get("runtime", {}).get("bootTime")
        if boot_time is not None:
            device.boot_time = parse_date(boot_time)

        memory_size_mb = config.get("memorySizeMB")
        if memory_size_mb is not None:
            device.total_physical_memory = memory_size_mb / 1024.0
        total_num_of_cpus = config.get("numCpu")
        if total_num_of_cpus is not None:
            device.total_number_of_physical_processors = int(total_num_of_cpus)

        device.set_raw(details)
        return device

    def _parse_raw_data(self, node, _curr_path: str = ""):
        """
        Parses the vms as returned from _query_devices_by_client to the format Aggregator wants

        :param node:
        :param _curr_path: internally used
        :return: iterator(dict)
        """
        node_type = node.get('Type')
        if not node_type:
            return
        if node_type == 'Machine':
            device = self._parse_vm_machine(node, _curr_path)
            device.device_type = ESXDeviceType.VMMachine
            yield device
        elif node_type == 'ESXHost':
            device = self._parse_vm_machine(node, _curr_path)
            if device is None:
                return
            device.device_type = ESXDeviceType.ESXHost
            node_hardware = node.get('Hardware')
            if node_hardware:
                device.add_cpu(cores=node_hardware['numCpuThreads'],
                               ghz=node_hardware['totalCpu'] / node_hardware['numCpuCores'] / 1024)
                device.total_physical_memory = node_hardware['totalMemory'] / (1024.0 * 1024 * 1024)
            yield device
        elif node_type in ("Datacenter", "Folder", "Root"):
            for child in node.get('Children', [{}]):
                yield from self._parse_raw_data(child, _curr_path + "/" + node['Name'])
        else:
            raise RuntimeError("Found weird type of node: {}".format(node['Type']))
