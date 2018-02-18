from typing import Tuple

from axonius.fields import Field
from axonius.adapter_exceptions import ClientConnectionException
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.device import Device
from axonius.scanner_adapter_base import ScannerAdapterBase, ScannerCorrelatorBase
from axonius.utils.files import get_local_config_file
import nexpose_adapter.clients as nexpose_clients

PASSWORD = 'password'
USER = 'username'
NEXPOSE_HOST = 'host'
NEXPOSE_PORT = 'port'
VERIFY_SSL = 'verify_ssl'


class NexposeScannerCorrelatorBase(ScannerCorrelatorBase):
    def _find_correlation_with_real_adapter(self, parsed_device) -> Tuple[str, str]:
        """
        check only first part of the hostname
        :param parsed_device:
        :return:
        """
        hostname = parsed_device.get('hostname', '').strip()
        if not hostname:
            return
        for adapter_device in self._all_adapter_devices:
            remote_hostname = adapter_device['data'].get('hostname')
            if isinstance(remote_hostname, str):
                if remote_hostname.split('.')[0].upper() == hostname.split('.')[0].upper():
                    return adapter_device[PLUGIN_UNIQUE_NAME], adapter_device['data']['id']


class NexposeAdapter(ScannerAdapterBase):
    """ Adapter for Rapid7's nexpose """

    class MyDevice(Device):
        risk_score = Field(float, 'Risk score')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))
        self.num_of_simultaneous_devices = int(self.config["DEFAULT"]["num_of_simultaneous_devices"])

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": NEXPOSE_HOST,
                    "title": "Host Name",
                    "type": "string"
                },
                {
                    "name": NEXPOSE_PORT,
                    "title": "Port",
                    "type": "number"
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
                },
                {  # if false, it will allow for invalid SSL certificates (but still uses HTTPS)
                    "name": VERIFY_SSL,
                    "title": "Verify SSL",
                    "type": "bool"
                }
            ],
            "required": [
                NEXPOSE_HOST,
                NEXPOSE_PORT,
                USER,
                PASSWORD,
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        # We do not use data with no timestamp.
        if len(devices_raw_data) is not 0:
            failed_to_parse = 0

            api_client_class = getattr(nexpose_clients, f"NexposeV{devices_raw_data[0]['API']}Client")

            for device_raw in devices_raw_data:
                try:
                    yield api_client_class.parse_raw_device(device_raw, self._new_device, self.logger)
                except Exception as err:
                    self.logger.exception(f"Caught exception from parsing using the {api_client_class.__name__}.")
                    failed_to_parse += 1

            if failed_to_parse != 0:
                self.logger.warning(f"Failed to parse {failed_to_parse} devices.")

    def _query_devices_by_client(self, client_name, client_data):
        if isinstance(client_data, nexpose_clients.NexposeClient):
            return client_data.get_all_devices()

    def _get_client_id(self, client_config):
        return client_config[NEXPOSE_HOST]

    def _connect_client(self, client_config):
        try:
            return nexpose_clients.NexposeV3Client(self.logger, self.num_of_simultaneous_devices, **client_config)
        except ClientConnectionException:
            return nexpose_clients.NexposeV2Client(self.logger, self.num_of_simultaneous_devices, **client_config)

    @property
    def _get_scanner_correlator(self):
        return NexposeScannerCorrelatorBase
