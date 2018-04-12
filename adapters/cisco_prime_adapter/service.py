import logging
logger = logging.getLogger(f"axonius.{__name__}")
import copy

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter, Field, DeviceAdapterOS
from axonius.utils.files import get_local_config_file
from cisco_prime_adapter.client import CiscoPrimeClient
from axonius.adapter_exceptions import ClientConnectionException


class CiscoPrimeAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        reachability = Field(str, "reachability")

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['url']

    def _connect_client(self, client_config):
        try:
            client = CiscoPrimeClient(**client_config)
            client.connect()
            return client
        except ClientConnectionException as err:
            logger.error('Failed to connect to client {0} using config: {1}'.format(
                self._get_client_id(client_config), client_config))
            raise

    def _query_devices_by_client(self, client_name, session):
        return session.get_devices()

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": "url",
                    "title": "url",
                    "type": "string",
                    "description": "Cisco Prime Infrastructure url"
                },
                {
                    "name": "username",
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": "password",
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },

            ],
            "required": [
                "url",
                "username",
                "password",
            ],
            "type": "array"
        }

    def create_device(self, raw_device):

        # if the device dosn't have id, it isn't really managed - ignore it
        if 'deviceId' not in raw_device['summary']:
            logger.warning(f'unmanged device detected {raw_device}')
            return None

        # add basic info
        device = self._new_device_adapter()

        device.id = str(raw_device['summary']['deviceId'])
        device.hostname = raw_device['summary'].get('deviceName', '')
        device.device_model = raw_device['summary'].get('deviceType', '')
        device.device_model_family = raw_device['summary'].get('ProductFamily', '')
        device.reachability = raw_device['summary'].get('reachability', '')

        # TODO: Figure os dosen't support .build field detection. it very
        # ugly to use figure os, since we dosen't really figuring out the os
        # (we pass static string 'cisco')

        device.figure_os('cisco')
        device.os.build = raw_device['summary'].get('softwareVersion', '')

        # iterate the nics and add them
        for mac, iplist in CiscoPrimeClient.get_nics(raw_device).items():
            device.add_nic(mac, map(lambda ipsubnet: ipsubnet[0], iplist))

        device.set_raw(raw_device)

        return device

    def _parse_raw_data(self, raw_data):
        for raw_device in iter(raw_data):
            try:
                device = self.create_device(raw_device)
                if device:
                    yield device
            except Exception:
                logger.exception(f'Got exception for raw_device: {raw_device}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
