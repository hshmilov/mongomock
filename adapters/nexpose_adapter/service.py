from typing import Tuple

from axonius.consts.plugin_consts import PLUGIN_NAME

from axonius.fields import Field
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device import Device
from axonius.parsing_utils import normalize_adapter_device, is_different_plugin, compare_ips, macs_do_not_contradict, \
    hostnames_do_not_contradict, and_function, or_function
from axonius.scanner_adapter_base import ScannerAdapterBase, ScannerCorrelatorBase
from axonius.utils.files import get_local_config_file
import nexpose_adapter.clients as nexpose_clients

PASSWORD = 'password'
USER = 'username'
NEXPOSE_HOST = 'host'
NEXPOSE_PORT = 'port'
VERIFY_SSL = 'verify_ssl'


class NexposeScannerCorrelator(ScannerCorrelatorBase):
    def _find_correlation_with_real_adapter(self, parsed_device) -> Tuple[str, str]:
        """
        See parent class docs
        """
        NORMALIZED_AWS_ID = 'normalized_aws_id'

        def add_aws_id(adapter_device):
            """
            If our device has a AWS ID hidden somewhere in the hostnames, highlight it
            """
            if adapter_device is not parsed_device:
                # we want to modify only our given device
                return adapter_device

            aws_potential_hostname = None

            adapter_data = adapter_device['data']
            hostnames = adapter_data['raw'].get('hostNames')
            if hostnames:
                aws_potential_hostname = next((hn['name'] for hn in hostnames
                                               if hn.get('source', '').lower() == 'epsec' and
                                               'i-' in hn.get('name', '')), None)
                if aws_potential_hostname:
                    aws_potential_hostname = aws_potential_hostname[aws_potential_hostname.index('i-'):]

            adapter_device[NORMALIZED_AWS_ID] = aws_potential_hostname
            return adapter_device

        def aws_ids_match(parsed_device, remote_device):
            """
            If our device has an AWS ID - compare that will the remote device
            :param parsed_device:
            :param remote_device:
            :return:
            """
            return remote_device[PLUGIN_NAME] == 'aws_adapter' and \
                parsed_device.get(NORMALIZED_AWS_ID) == remote_device['data']['id']

        return self.find_suitable_newest(parsed_device,
                                         normalizations=[normalize_adapter_device, add_aws_id],
                                         predicates=[is_different_plugin,
                                                     or_function(and_function(compare_ips,
                                                                              macs_do_not_contradict,
                                                                              hostnames_do_not_contradict),
                                                                 aws_ids_match)
                                                     ])


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
        return NexposeScannerCorrelator
