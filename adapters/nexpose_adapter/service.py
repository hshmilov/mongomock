import logging

logger = logging.getLogger(f'axonius.{__name__}')

from axonius.fields import Field, ListField
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.adapter_base import AdapterProperty
from axonius.utils.files import get_local_config_file
from axonius.plugin_base import add_rule, return_error
import axonius.clients.nexpose as nexpose_clients
from axonius.clients.nexpose.nexpose_v3_client import ScanData, NexposeVuln, NexposePolicy
from axonius.clients.rest.connection import RESTConnection

PASSWORD = 'password'
USER = 'username'
NEXPOSE_HOST = 'host'
NEXPOSE_PORT = 'port'
VERIFY_SSL = 'verify_ssl'


class NexposeAdapter(ScannerAdapterBase):
    """ Adapter for Rapid7's nexpose """
    DEFAULT_LAST_SEEN_THRESHOLD_HOURS = 24 * 365 * 2

    class MyDeviceAdapter(DeviceAdapter):
        nexpose_id = Field(str, 'Nexpose ID')
        r7_agent_id = Field(str, 'Rapid7 Agent ID')
        nexpose_hostname = Field(str, 'Nexpose Hostname')
        risk_score = Field(float, 'Risk score')
        vulnerabilities_critical = Field(int, "Critical Vulnerabilities")
        vulnerabilities_exploits = Field(int, "Exploits Vulnerabilities")
        vulnerabilities_malwareKits = Field(int, "MalwareKits Vulnerabilities")
        vulnerabilities_moderate = Field(int, "Moderate Vulnerabilities")
        vulnerabilities_severe = Field(int, "Severe Vulnerabilities")
        vulnerabilities_total = Field(int, "Total Vulnerabilities")
        location_tags = ListField(str, "Locations")
        owner_tags = ListField(str, "Owners")
        criticality_tags = ListField(str, "Criticality")
        custom_tags = ListField(str, "Custom Tags")
        nexpose_type = Field(str, 'Nexpose Device Type')
        assessed_for_policies = Field(bool, 'Assessed For Policies')
        assessed_for_vulnerabilities = Field(bool, 'Assessed For Vulnerabilities')
        scans_data = ListField(ScanData, 'Scans Data')
        nexpose_vulns = ListField(NexposeVuln, 'Nexpose Vulnerabilities')
        nexpose_policies = ListField(NexposePolicy, 'Nexpose Policies')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": NEXPOSE_HOST,
                    "title": "Host name",
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
                    "title": "User name",
                    "type": "string"
                },
                {
                    "name": PASSWORD,
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },
                {
                    'name': 'token',
                    'title': 'Token (for 2FA only)',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'fetch_tags',
                    'title': 'Fetch tags',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_sw',
                    'type': 'bool',
                    'title': 'Fetch installed software'
                },
                {
                    'name': 'fetch_ports',
                    'type': 'bool',
                    'title': 'Fetch open ports'
                },
                {
                    'name': 'fetch_policies',
                    'title': 'Fetch policies',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_vulnerabilities',
                    'title': 'Fetch vulnerabilities',
                    'type': 'bool'
                },
                {
                    'name': 'num_of_simultaneous_devices',
                    'title': 'Number of simultaneous devices',
                    'type': 'integer'
                },
                {
                    'name': 'drop_only_ip_devices',
                    'title': 'Do not fetch devices with no MAC address and no hostname',
                    'type': 'bool'
                },
                {
                    'name': 'site_name_exclude_list',
                    'title': 'Site name exclude list',
                    'type': 'string'
                },
                {  # if false, it will allow for invalid SSL certificates (but still uses HTTPS)
                    "name": VERIFY_SSL,
                    "title": "Verify SSL",
                    "type": "bool"
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
                {
                    'name': 'proxy_username',
                    'title': 'HTTPS Proxy User Name',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS Proxy Password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            "required": [
                NEXPOSE_HOST,
                NEXPOSE_PORT,
                USER,
                PASSWORD,
                VERIFY_SSL,
                'drop_only_ip_devices',
                'fetch_vulnerabilities',
                'fetch_policies',
                'fetch_ports',
                'fetch_tags',
                'fetch_sw'
            ],
            "type": "array"
        }

    def _refetch_device(self, client_id, client_data, device_id):
        connection, nexpose_hostname = client_data
        asset_data = connection.get_asset_data(device_id)
        asset_data['API'] = '3'
        client_config = self._get_client_config_by_client_id(client_id)
        for device in self._parse_raw_data([(asset_data, nexpose_hostname, client_config)]):
            return device

    @add_rule('add_ips_to_site', methods=['POST'])
    def add_ips_to_asset(self):
        if self.get_method() != 'POST':
            return return_error('Method not supported', 405)
        rapid7_dict = self.get_request_data_as_object()
        success = False
        try:
            for client_id in self._clients:
                try:
                    client_config = self._get_client_config_by_client_id(client_id)
                    num_of_simultaneous_devices = client_config.get('num_of_simultaneous_devices') or 50
                    conn = nexpose_clients.NexposeV3Client(num_of_simultaneous_devices, host=client_config['host'],
                                                           port=client_config['port'],
                                                           username=client_config['username'],
                                                           password=client_config['password'],
                                                           verify_ssl=client_config['verify_ssl'],
                                                           token=client_config.get('token'),
                                                           https_proxy=client_config.get('https_proxy'),
                                                           proxy_username=client_config.get('proxy_username'),
                                                           proxy_password=client_config.get('proxy_password'),
                                                           )
                    result_status = conn.add_ips_to_site(rapid7_dict)
                    success = success or result_status
                    if success is True:
                        return '', 200
                except Exception:
                    logger.exception(f'Could not connect to {client_id}')
        except Exception as e:
            logger.exception('Got exception while adding ips to site')
            return str(e), 400
        return 'Failure', 400

    def _parse_raw_data(self, devices_raw_data):
        # We do not use data with no timestamp.
        failed_to_parse = 0
        api_client_class = None
        for device_raw, nexpose_hostname, client_config in devices_raw_data:
            try:
                if api_client_class is None:
                    api_client_class = getattr(nexpose_clients, f"NexposeV{device_raw['API']}Client")
                drop_only_ip_devices = client_config.get('drop_only_ip_devices') or False
                fetch_vulnerabilities = client_config.get('fetch_vulnerabilities') or False
                site_name_exclude_list = client_config.get('site_name_exclude_list')
                device = api_client_class.parse_raw_device(device_raw, self._new_device_adapter,
                                                           drop_only_ip_devices=drop_only_ip_devices,
                                                           fetch_vulnerabilities=fetch_vulnerabilities,
                                                           site_name_exclude_list=site_name_exclude_list)
                if device:
                    device.nexpose_hostname = nexpose_hostname
                    yield device
            except Exception as err:
                logger.exception(
                    f"Caught exception from parsing using the API version: "
                    f"{api_client_class.__name__ if api_client_class is not None else ''}. for device {device_raw}")

                failed_to_parse += 1

        if failed_to_parse != 0:
            logger.warning(f"Failed to parse {failed_to_parse} devices.")

    def _query_devices_by_client(self, client_name, client_data):
        client_config = self._get_client_config_by_client_id(client_name)
        connection, nexpose_hostname = client_data
        if isinstance(connection, nexpose_clients.NexposeClient):
            fetch_vulnerabilities = client_config.get('fetch_vulnerabilities') or False
            for device_raw in connection.get_all_devices(fetch_tags=client_config.get('fetch_tags') or False,
                                                         fetch_policies=client_config.get('fetch_policies') or False,
                                                         fetch_vulnerabilities=fetch_vulnerabilities,
                                                         fetch_sw=client_config.get('fetch_sw') or False,
                                                         fetch_ports=client_config.get('fetch_ports') or False):
                yield device_raw, nexpose_hostname, client_config

    def _get_client_id(self, client_config):
        return client_config[NEXPOSE_HOST] + '_' + client_config[USER]

    def _connect_client(self, client_config):
        num_of_simultaneous_devices = client_config.get('num_of_simultaneous_devices') or 50
        try:
            return nexpose_clients.NexposeV3Client(num_of_simultaneous_devices, host=client_config['host'],
                                                   port=client_config['port'], username=client_config['username'],
                                                   password=client_config['password'],
                                                   verify_ssl=client_config['verify_ssl'],
                                                   token=client_config.get('token'),
                                                   https_proxy=client_config.get('https_proxy'),
                                                   proxy_username=client_config.get('proxy_username'),
                                                   proxy_password=client_config.get('proxy_password'),
                                                   ),\
                client_config[NEXPOSE_HOST]
        except ClientConnectionException:
            return nexpose_clients.NexposeV2Client(num_of_simultaneous_devices, host=client_config['host'],
                                                   port=client_config['port'], username=client_config['username'],
                                                   password=client_config['password'],
                                                   verify_ssl=client_config['verify_ssl'],
                                                   token=client_config.get('token'),
                                                   https_proxy=client_config.get('https_proxy'),
                                                   proxy_username=client_config.get('proxy_username'),
                                                   proxy_password=client_config.get('proxy_password'),
                                                   ),\
                client_config[NEXPOSE_HOST]

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get(NEXPOSE_HOST), client_config.get(NEXPOSE_PORT))

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network, AdapterProperty.Vulnerability_Assessment]
