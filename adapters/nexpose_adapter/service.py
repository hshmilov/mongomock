import logging

logger = logging.getLogger(f'axonius.{__name__}')
from typing import Tuple

from axonius.consts.plugin_consts import PLUGIN_NAME, PLUGIN_UNIQUE_NAME

from axonius.fields import Field, ListField
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.scanner_adapter_base import ScannerAdapterBase, ScannerCorrelatorBase
from axonius.adapter_base import AdapterProperty
from axonius.utils.files import get_local_config_file
import nexpose_adapter.clients as nexpose_clients
from axonius.clients.rest.connection import RESTConnection

PASSWORD = 'password'
USER = 'username'
NEXPOSE_HOST = 'host'
NEXPOSE_PORT = 'port'
VERIFY_SSL = 'verify_ssl'


class NexposeScannerCorrelator(ScannerCorrelatorBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._all_aws_devices_by_id = {x['data']['id']: x
                                       for x in self._all_adapter_devices
                                       if x[PLUGIN_NAME] == 'aws_adapter'}

    def _find_correlation_with_real_adapter(self, parsed_device) -> Tuple[str, str]:
        """
        See parent class docs
        """

        # first, lets see if we have an AWS hostname - if is so, let's try to correlate accordingly
        adapter_data = parsed_device['data']
        hostnames = adapter_data['raw'].get('hostNames')
        if hostnames:
            aws_potential_hostname = next((hn['name'] for hn in hostnames
                                           if hn.get('source', '').lower() == 'epsec' and
                                           'i-' in hn.get('name', '')), None)
            if aws_potential_hostname:
                aws_potential_hostname = aws_potential_hostname[aws_potential_hostname.index('i-'):]
                aws_potential_correlation = self._all_aws_devices_by_id.get(aws_potential_hostname)
                if aws_potential_correlation:
                    return aws_potential_correlation[PLUGIN_UNIQUE_NAME], aws_potential_correlation['data']['id']

        return super()._find_correlation_with_real_adapter(parsed_device)


class NexposeAdapter(ScannerAdapterBase):
    """ Adapter for Rapid7's nexpose """

    class MyDeviceAdapter(DeviceAdapter):
        risk_score = Field(float, 'Risk score')
        vulnerabilities_critical = Field(int, "Critical Vulnerabiliies")
        vulnerabilities_exploits = Field(int, "Exploits Vulnerabiliies")
        vulnerabilities_malwareKits = Field(int, "MalwareKits Vulnerabiliies")
        vulnerabilities_moderate = Field(int, "Moderate Vulnerabiliies")
        vulnerabilities_severe = Field(int, "Severe Vulnerabiliies")
        vulnerabilities_total = Field(int, "Total Vulnerabiliies")
        nexpose_tags = ListField(str, "Nexpose Tags")

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)
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
                    "type": "integer",
                    "format": "port"
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
        failed_to_parse = 0
        api_client_class = None
        for device_raw in devices_raw_data:
            try:
                if api_client_class is None:
                    api_client_class = getattr(nexpose_clients, f"NexposeV{device_raw['API']}Client")
                yield api_client_class.parse_raw_device(device_raw, self._new_device_adapter)
            except Exception as err:
                logger.exception(
                    f"Caught exception from parsing using the API version: "
                    f"{api_client_class.__name__ if api_client_class is not None else ''}. for device {device_raw}")

                failed_to_parse += 1

        if failed_to_parse != 0:
            logger.warning(f"Failed to parse {failed_to_parse} devices.")

    def _query_devices_by_client(self, client_name, client_data):
        if isinstance(client_data, nexpose_clients.NexposeClient):
            yield from client_data.get_all_devices()

    def _get_client_id(self, client_config):
        return client_config[NEXPOSE_HOST]

    def _connect_client(self, client_config):
        try:
            return nexpose_clients.NexposeV3Client(self.num_of_simultaneous_devices, **client_config)
        except ClientConnectionException:
            return nexpose_clients.NexposeV2Client(self.num_of_simultaneous_devices, **client_config)

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get(NEXPOSE_HOST), client_config.get(NEXPOSE_PORT))

    @property
    def _get_scanner_correlator(self):
        return NexposeScannerCorrelator

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network, AdapterProperty.Vulnerability_Assessment]
