"""
ESXAdapter.py: An adapter for ESX services.
Currently, allows you to view ESX instances you possess.
"""

__author__ = "Mark Segal"

from axonius.fields import Field
from axonius.device import Device
from axonius.adapter_base import AdapterBase, DeviceRunningState
from axonius import adapter_exceptions
from pyVmomi import vim
from vcenter_api import vCenterApi, rawify_vcenter_data

# translation table between ESX values to parsed values
POWER_STATE_MAP = {
    'poweredOff': DeviceRunningState.TurnedOff.value,
    'poweredOn': DeviceRunningState.TurnedOn.value,
    'suspended': DeviceRunningState.Suspended.value,
}


class ESXAdapter(AdapterBase):

    class MyDevice(Device):
        vm_tools_status = Field(str, 'VM Tools Status')
        vm_physical_path = Field(str, 'VM physical path')
        power_state = Field(str, 'Power state')

    def __init__(self, *args, **kwargs):
        """
        Check AdapterBase documentation for additional params and exception details.
        """
        super().__init__(*args, **kwargs)

    def _get_client_id(self, client_config):
        return '{}/{}'.format(client_config['host'], client_config['user'])

    def _connect_client(self, client_config):
        client_id = self._get_client_id(client_config)
        try:
            return vCenterApi(host=client_config['host'], user=client_config['user'],
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
        raise adapter_exceptions.ClientConnectionException(message)

    def _clients_schema(self):
        """
        The schema ESXAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "properties": {
                "host": {
                    "type": "string"
                },
                "user": {
                    "type": "string"
                },
                "password": {
                    "type": "password"
                },
                "verify_ssl": {  # if false, it will allow for invalid SSL certificates (but still uses HTTPS)
                    "type": "bool"
                }
            },
            "required": [
                "host",
                "user",
                "password",
                "verify_ssl"
            ],
            "type": "object"
        }

    def _query_devices_by_client(self, client_name, client_data):
        return rawify_vcenter_data(client_data.get_all_vms())

    def _parse_raw_data(self, node, _curr_path: str = ""):
        """
        Parses the vms as returned from _query_devices_by_client to the format Aggregator wants

        :param node:
        :param _curr_path: internally used
        :return: iterator(dict)
        """
        if node.get('Type', '') == 'Machine':
            details = node.get('Details', {})
            guest = details.get('guest', {})
            device = self._new_device()
            device.name = node.get('Name', '')
            device.figure_os(details.get('config', {}).get('guestFullName', ''))
            device.id = details.get('config', {})['instanceUuid']
            device.network_interfaces = []
            for iface in details.get('networking', []):
                ips = [addr['ipAddress'] for addr in iface.get('ipAddresses', [])]
                if ips:
                    device.add_nic(iface.get('macAddress'), ips)
            if not device.network_interfaces and 'ipAddress' in guest:
                # if nothing is found in raw.networking this will be used
                device.add_nic(mac='', ips=[guest.get('ipAddress')])
            device.hostname = guest.get('hostName', '')
            device.vm_tools_status = guest.get('toolsStatus', '')
            device.vm_physical_path = _curr_path + "/" + node.get('Name', '')
            device.power_state = POWER_STATE_MAP.get(details.get('runtime', {}).get('powerState'),
                                                     DeviceRunningState.Unknown.value)
            device.set_raw(details)
            yield device
        elif node.get('Type', '') in ("Datacenter", "Folder", "Root"):
            for child in node.get('Children', [{}]):
                yield from self._parse_raw_data(child, _curr_path + "/" + node['Name'])
        else:
            raise RuntimeError("Found weird type of node: {}".format(node['Type']))
