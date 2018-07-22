import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.utils.files import get_local_config_file
from axonius.fields import Field, ListField
from axonius.clients.rest.exception import RESTException
from tenable_io_adapter.connection import TenableIoConnection
from axonius.utils.parsing import parse_date
from axonius.devices.device_adapter import DeviceAdapter


class TenableIoAdapter(ScannerAdapterBase):
    DEFAULT_LAST_SEEN_THRESHOLD_HOURS = None

    class MyDeviceAdapter(DeviceAdapter):
        has_agent = Field(bool, "Has Agent")
        plugin_and_severity = ListField(str, "Plugin and severity")

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _connect_client(self, client_config):
        try:
            connection = TenableIoConnection(domain=client_config["domain"], verify_ssl=client_config["verify_ssl"],
                                             username=client_config.get("username"),
                                             password=client_config.get("password"),
                                             url_base_prefix="/", headers={'Content-Type': 'application/json',
                                                                           'Accept': 'application/json'},
                                             access_key=client_config.get('access_key'),
                                             secret_key=client_config.get('secret_key'))

            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except RESTException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        try:
            client_data.connect()
            yield from client_data.get_device_list()
        finally:
            client_data.close()

    def _clients_schema(self):
        """
        The schema TenableIOAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "domain",
                    "title": "TenableIO Domain",
                    "type": "string"
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
                {
                    "name": "verify_ssl",
                    "title": "Verify SSL",
                    "type": "bool"
                },
                {
                    'name': 'access_key',
                    'title': 'Access API Key (instead of user/password)',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'secret_key',
                    'title': 'Secret API key (instead of user/password)',
                    'type': 'string',
                    'format': 'password'
                },

            ],
            "required": [
                "domain",
                "verify_ssl"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device.has_agent = bool(device_raw.get("has_agent"))
                try:
                    device.last_seen = parse_date(device_raw.get("last_seen", ""))
                except Exception:
                    logger.exception(f"Problem with last seen for {device_raw}")
                try:
                    ipv4_raw = device_raw.get("ipv4s", [])
                    ipv6_raw = device_raw.get("ipv6s", [])
                    mac_addresses_raw = device_raw.get("mac_addresses", [])
                    if mac_addresses_raw == []:
                        device.add_nic(None, ipv4_raw + ipv6_raw)
                    for mac_item in mac_addresses_raw:
                        try:
                            device.add_nic(mac_item, ipv4_raw + ipv6_raw)
                        except Exception:
                            logger.exception(f"Problem adding nice to {device_raw}")
                except Exception:
                    logger.exception(f"Problem with IP at {device_raw}")
                try:
                    os_list = device_raw.get("operating_systems")
                    if len(os_list) > 0:
                        device.figure_os(str(os_list[0]))
                except Exception:
                    logger.exception(f"Problem getting OS for {device_raw}")
                fqdns = device_raw.get("fqdns", [])
                hostnames = device_raw.get("hostnames", [])
                netbios = device_raw.get("netbios_names", [])
                if len(fqdns) > 0 and fqdns[0] != "":
                    device.hostname = fqdns[0]
                elif len(hostnames) > 0 and hostnames[0] != "":
                    device.hostname = hostnames[0]
                elif len(netbios) > 0 and netbios[0] != "":
                    device.hostname = netbios[0]
                device.plugin_and_severity = []
                vulns_info = device_raw.get("vulns_info", [])
                for vuln_raw in vulns_info:
                    try:
                        severity = vuln_raw.get("severity", "")
                        plugin_name = vuln_raw.get("plugin", {}).get("name", "")
                        if f"{plugin_name}__{severity}" not in device.plugin_and_severity:
                            device.plugin_and_severity.append(f"{plugin_name}__{severity}")
                    except Exception:
                        logger.exception(f"Problem getting vuln raw {vuln_raw}")
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception("Problem with fetching TenableIO Device")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network, AdapterProperty.Vulnerability_Assessment]
