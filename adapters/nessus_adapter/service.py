import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.adapter_exceptions import AdapterException, ClientConnectionException
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.adapter_base import AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from nessus_adapter.connection import NessusConnection
from nessus_adapter.exceptions import NessusException
from axonius.utils.parsing import parse_date
from axonius.fields import Field, JsonStringFormat, ListField
from axonius.smart_json_class import SmartJsonClass


HOST = 'host'
PORT = 'port'
USERNAME = 'username'
PASSWORD = 'password'


class NessusVulnerability(SmartJsonClass):
    plugin_id = Field(str, "Plugin ID")
    plugin_name = Field(str, "Plugin Name")
    severity = Field(int, "Severity")
    severity_index = Field(int, "Severity Index")
    vuln_index = Field(int, "Vulnerability Index")


class NessusAdapter(ScannerAdapterBase):
    """ An adapter for Tenable's Nessus Vulnerability scanning platform. """

    class MyDeviceAdapter(DeviceAdapter):
        vulnerabilities = ListField(NessusVulnerability, "Vulnerability")

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        """
        A unique value, from a predefined field, representing given client

        :param client_config: Object containing values for needed client credentials
        :return: str unique id for the client
        """
        return client_config[HOST]

    def _connect_client(self, client_config):
        """


        :param client_config:
        :return:
        """
        try:
            connection = NessusConnection(host=client_config[HOST],
                                          port=(client_config[PORT] if PORT in client_config else None))
            connection.set_credentials(username=client_config[USERNAME], password=client_config[PASSWORD])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except NessusException as e:
            port = client_config[PORT] if PORT in client_config else ''
            message = 'Error connecting to client with address {0} and port {1}, reason: {2}'.format(
                client_config[HOST], port, str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Use given connection to fetch all scans and for each scan, fetch all hosts.

        :param client_name: Unique name representing the client
        :param client_data: NessusConnection providing access to the client
        :return:
        """
        try:
            with client_data:
                device_dict = {}
                devices_count = 0
                # Get all scans for client
                for scan in client_data.get_scans():
                    if scan.get('id') is None:
                        continue
                    # Get all hosts for scan
                    for host in client_data.get_hosts(scan['id']):
                        if host.get('host_id') is None:
                            continue
                        devices_count += 1
                        if devices_count % 1000 == 0:
                            logger.info(f"Got {devices_count} hosts requests so far")
                        # Get specific details of the host
                        host_details = client_data.get_host_details(scan['id'], host['host_id'])
                        if not host_details:
                            continue

                        host_id = host.get('host_id')
                        if host_id not in device_dict:
                            # Add host that is not yet listed in dict
                            host_details['scans'] = {}
                            device_dict[host_id] = host_details
                        # Add current scan info to the host, by scan id
                        device_dict[host_id]['scans'][scan['id']] = host

                return device_dict.values()
        except NessusException:
            logger.exception(f'Error querying devices from client {client_name}')
            raise AdapterException('Nessus Adapter failed querying devices for {0}'.format(client_name))

    def _clients_schema(self):
        """
        Definition of the credentials needed for connecting to a Nessus client.
        Once connection is established, use returned token in requests' HTTP header:
        X-Cookie: token={returned token}

        :return: JSON schema defining the credential properties
        """
        return {
            'items': [
                {
                    'name': HOST,
                    'title': 'Host Address',
                    'type': 'string'
                },
                {
                    'name': PORT,
                    'title': 'Port',
                    'type': 'integer',
                },
                {
                    'name': USERNAME,
                    'title': 'Username',
                    'type': 'string'
                },
                {
                    'name': PASSWORD,
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [HOST, USERNAME, PASSWORD],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        """
        Generator creating parsed version of each device

        :param devices_raw_data: Data as originally retrieved from Nessus
        :return: Data structured as expected by adapters
        """
        for device_raw in devices_raw_data:
            device = self._new_device_adapter()
            device.figure_os(device_raw.get('info', {}).get('operating-system', ''))
            device.add_nic(device_raw.get('info', {}).get('mac-address', ''),
                           [device_raw.get('info', {}).get('host-ip', '')])
            device.last_seen = parse_date(str(device_raw.get('info', {}).get('host_end', '')))
            device.hostname = device_raw.get('info', {}).get("netbios-name")
            vulnerabilities_raw = device_raw.get("vulnerabilities", [])
            device.vulnerabilities = []
            for vulnerability_raw in vulnerabilities_raw:
                try:
                    new_vulnerability = NessusVulnerability()
                    new_vulnerability.plugin_id = vulnerability_raw.get("plugin_id")
                    new_vulnerability.plugin_name = vulnerability_raw.get("plugin_name")
                    new_vulnerability.severity = vulnerability_raw.get("severity")
                    new_vulnerability.severity_index = vulnerability_raw.get("severity_index")
                    new_vulnerability.vuln_index = vulnerability_raw.get("vuln_index")
                    device.vulnerabilites.append(new_vulnerability)
                except:
                    logger.exception(f"Problem adding vulnerability {vulnerability_raw}")
            device.scanner = True
            device.set_raw(device_raw)
            yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network, AdapterProperty.Vulnerability_Assessment]
