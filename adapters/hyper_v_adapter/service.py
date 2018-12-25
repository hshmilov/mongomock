import logging
import os

logger = logging.getLogger(f'axonius.{__name__}')

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.parsing import format_mac
from axonius.utils.files import get_local_config_file
from hyper_v_adapter.exceptions import HyperVException
from hyper_v_adapter.connection import HyperVConnection

HYPER_V_HOST = 'host'
PASSWORD = 'password'
USER = 'username'


class HyperVAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        pass

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config[HYPER_V_HOST]

    @property
    def _use_wmi_smb_path(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), self.config['paths']['wmi_smb_path']))

    @property
    def _python_27_path(self):
        return self.config['paths']['python_27_path']

    def _connect_client(self, client_config):
        try:
            return HyperVConnection(client_config[HYPER_V_HOST], client_config[USER], client_config[PASSWORD],
                                    self._use_wmi_smb_path, self._python_27_path)
        except HyperVException as e:
            message = "Error connecting to client with host {0}, reason: {1}".format(
                client_config[HYPER_V_HOST], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Hyper-V server

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Hyper-V wmi connection

        :return: A json with all the attributes returned from the Hyper-V Server
        """
        return client_data.get_devices()

    def _clients_schema(self):
        """
        The schema HyperV adapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": HYPER_V_HOST,
                    "title": "Host Name",
                    "type": "string"
                },
                {
                    "name": USER,
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": PASSWORD,
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                }
            ],
            "required": [
                HYPER_V_HOST,
                USER,
                PASSWORD,
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for raw_device in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device.name = raw_device.get('ElementName')
                device.id = raw_device['Name']

                for current_switch in raw_device['Switches']:
                    device.add_nic(mac=format_mac(current_switch['PermanentAddress']))

                for current_network in raw_device['Networks']:
                    device.add_nic(ips=current_network['IPAddresses'], subnets=[
                        f'{ip}/{subnet}'
                        for ip, subnet in zip(current_network['IPAddresses'], current_network['Subnets'])
                    ])

                for current_cpu in raw_device['Cpus']:
                    device.add_cpu(name=current_cpu['UniqueID'], load_percentage=current_cpu['LoadPercentage'])

                for current_dd in raw_device['DiskDrives']:
                    device.add_hd(total_size=current_dd['MaxMediaSize'] / 100000000)  # kilobytes

                # Issues with large numbers on mongo insert.
                raw_device.pop('DiskDrives')

                device.set_raw(raw_device)
                yield device
            except Exception:
                logger.exception("Failed to parse device.")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Virtualization, AdapterProperty.Assets]
