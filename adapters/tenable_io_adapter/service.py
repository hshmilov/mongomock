import datetime
import logging
logger = logging.getLogger(f'axonius.{__name__}')
from collections import defaultdict
from axonius.adapter_base import AdapterProperty
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.utils.files import get_local_config_file
from axonius.fields import Field, ListField, JsonArrayFormat
from axonius.smart_json_class import SmartJsonClass
from axonius.clients.rest.exception import RESTException
from tenable_io_adapter.connection import TenableIoConnection
from axonius.utils.parsing import parse_date
from axonius.devices.device_adapter import DeviceAdapter
from axonius.clients.rest.connection import RESTConnection
from axonius.mixins.configurable import Configurable


class TenableVulnerability(SmartJsonClass):
    plugin = Field(str, 'plugin')
    severity = Field(str, 'severity')


class TenableSource(SmartJsonClass):
    first_seen = Field(datetime.datetime, 'First Seen')
    last_seen = Field(datetime.datetime, 'Last Seen')
    source = Field(str, 'Source')


class TenableIoAdapter(ScannerAdapterBase, Configurable):

    class MyDeviceAdapter(DeviceAdapter):
        has_agent = Field(bool, "Has Agent")
        agent_version = Field(str, 'Agent Version')
        status = Field(str, 'Status')
        plugin_and_severities = ListField(TenableVulnerability, 'Plugins and Severities',
                                          json_format=JsonArrayFormat.table)
        tenable_sources = ListField(TenableSource, 'Tenable Source',
                                    json_format=JsonArrayFormat.table)
        risk_and_name_list = ListField(str, "CSV - Vulnerability Details")

        def add_tenable_vuln(self, **kwargs):
            self.plugin_and_severities.append(TenableVulnerability(**kwargs))

        def add_tenable_source(self, **kwargs):
            self.tenable_sources.append(TenableSource(**kwargs))

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get("domain"))

    def _connect_client(self, client_config):
        try:
            connection = TenableIoConnection(domain=client_config["domain"], verify_ssl=client_config["verify_ssl"],
                                             url_base_prefix="/", headers={'Content-Type': 'application/json',
                                                                           'Accept': 'application/json'},
                                             access_key=client_config.get('access_key'),
                                             secret_key=client_config.get('secret_key'),
                                             https_proxy=client_config.get('https_proxy'))

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
            logger.info('Getting all assets')
            devices_list = client_data.get_device_list(use_cache=self.__use_cache)
            logger.info(f'Got {len(devices_list)} assets, starting agents')
            agents_list = client_data.get_agents()
            logger.info(f'Got {len(agents_list)} agents')
            return [devices_list, agents_list]
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
                {
                    "name": "https_proxy",
                    "title": "HTTPS Proxy",
                    "type": "string"
                }

            ],
            "required": [
                "domain",
                "verify_ssl",
                "access_key",
                "secret_key"
            ],
            "type": "array"
        }

    def _parse_export_device(self, device_id, device_raw):
        device = self._new_device_adapter()
        device.id = device_id
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
                    logger.exception(f"Problem adding nic to {device_raw}")
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
        plugin_and_severity = []
        vulns_info = device_raw.get("vulns_info", [])
        for vuln_raw in vulns_info:
            try:
                severity = vuln_raw.get("severity", "")
                plugin_name = vuln_raw.get("plugin", {}).get("name", "")
                if f"{plugin_name}__{severity}" not in plugin_and_severity:
                    plugin_and_severity.append(f"{plugin_name}__{severity}")
                    device.add_tenable_vuln(plugin=plugin_name, severity=severity)
            except Exception:
                logger.exception(f"Problem getting vuln raw {vuln_raw}")

        tenble_sources = device_raw.get('sources')
        if not isinstance(tenble_sources, list):
            tenble_sources = []
        for tenble_source in tenble_sources:
            try:
                last_seen = parse_date(tenble_source.get('last_seen'))
                first_seen = parse_date(tenble_source.get('first_seen'))
                source = tenble_source.get('name')
                device.add_tenable_source(source=source, first_seen=first_seen, last_seen=last_seen)
            except Exception:
                logger.exception(f'Problem adding tenable source {tenble_source}')

        # This is too much info for our poor raw deivice. It made the collection too big
        device.set_raw({})
        return device

    def _parse_raw_data(self, devices_raw_data_all):
        devices_raw_data, agents_data = devices_raw_data_all
        devices_raw_data, connection_type = devices_raw_data
        if connection_type == 'export':
            for device_id, device_raw in devices_raw_data:
                try:
                    yield self._parse_export_device(device_id, device_raw)
                except Exception:
                    logger.exception(f'Problem with parsing device {device_raw}')
        elif connection_type == 'csv':
            yield from self._parse_raw_data_csv(devices_raw_data)
        yield from self._parse_agents(agents_data)

    def _parse_agents(self, agents_data):
        try:
            for agent_raw in agents_data:
                try:
                    device = self._new_device_adapter()
                    device_id = agent_raw.get('id')
                    if not device_id:
                        logger.warning(f'Bad agent with no ID {agent_raw}')
                        continue
                    hostname = agent_raw.get('name')
                    device.id = str(device_id) + hostname or ''
                    device.hostname = hostname
                    ip = agent_raw.get('ip')
                    if ip:
                        device.add_nic(None, [ip])
                    try:
                        if agent_raw.get('last_connect'):
                            device.last_seen = datetime.datetime.fromtimestamp(agent_raw.get('last_connect'))
                    except Exception:
                        logger.exception(f'Problem getting last seen at {agent_raw}')
                    device.has_agent = True
                    device.status = agent_raw.get('status')
                    device.agent_version = agent_raw.get('core_version')
                    device.adapter_properties = [AdapterProperty.Agent.name,
                                                 AdapterProperty.Vulnerability_Assessment.name]
                    device.set_raw(agent_raw)
                    yield device
                except Exception:
                    logger.exception(f'Problem parsing {agent_raw}')
        except Exception:
            logger.exception('Problem with all agents')
        return

    def _parse_raw_data_csv(self, devices_raw_data):
        assets_dict = defaultdict(list)

        def get_csv_value_filtered(d, n):
            try:
                value = d.get(n)
                if value is not None:
                    if str(value).strip().lower() not in ["", "none", "0"]:
                        return str(value).strip()
            except Exception:
                pass

            return None

        for device_raw in devices_raw_data:
            try:
                uuid = get_csv_value_filtered(device_raw, "Asset UUID")
                host = get_csv_value_filtered(device_raw, "Host")

                # This chars are false, we get bad csv sometimes
                false_uuid = ['=', '|', ':']
                if uuid is None or host is None or any(elem in uuid for elem in false_uuid):
                    logger.warning(f"Bad asset {device_raw}, continuing")
                    continue
                assets_dict[uuid].append(device_raw)
            except Exception:
                logger.exception(f"Problem with fetching TenableIO Device {device_raw}")
        for asset_id, asset_id_values in assets_dict.items():
            try:
                device = self._new_device_adapter()
                device.id = asset_id

                first_asset = asset_id_values[0]
                try:
                    device.last_seen = parse_date(get_csv_value_filtered(first_asset, "Host End"))
                except Exception:
                    logger.exception(f"Problem getting last seen for {str(first_asset)}")
                ip_addresses = get_csv_value_filtered(first_asset, "IP Address")
                mac_addresses = get_csv_value_filtered(first_asset, "MAC Address")

                # Turn to lists
                ip_addresses = ip_addresses.split(",") if ip_addresses is not None else []
                mac_addresses = mac_addresses.split(",") if mac_addresses is not None else []

                if mac_addresses == [] and ip_addresses != []:
                    device.add_nic(None, ip_addresses)

                else:
                    for mac_address in mac_addresses:
                        while len(mac_address) > 17:
                            try:
                                mac_address_to_use = mac_address[:17]
                                mac_address = mac_address[17:]
                                device.add_nic(mac_address_to_use, ip_addresses)
                            except Exception:
                                logger.exception(f'Problem adding mac with {mac_address}')
                        try:
                            device.add_nic(mac_address, ip_addresses)
                        except Exception:
                            logger.exception(f'Problem adding mac with {mac_address}')

                fqdn = get_csv_value_filtered(first_asset, "FQDN")
                netbios = get_csv_value_filtered(first_asset, "NetBios")

                if fqdn is not None:
                    device.hostname = fqdn
                else:
                    device.hostname = netbios

                os = get_csv_value_filtered(first_asset, "OS")
                device.figure_os(os)

                risk_and_name_list = []
                for vuln_i in asset_id_values:
                    vrisk = get_csv_value_filtered(vuln_i, "Risk")
                    vname = get_csv_value_filtered(vuln_i, "Name")
                    if vrisk and vname:
                        risk_and_name_list.append(f"{vrisk} - {vname}")

                if len(risk_and_name_list) > 0:
                    device.risk_and_name_list = risk_and_name_list
                first_asset["risk_and_name_list"] = risk_and_name_list
                device.set_raw(first_asset)
                yield device
            except Exception:
                logger.exception(f"Problem with asset id {asset_id} and values {asset_id_values}")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network, AdapterProperty.Vulnerability_Assessment]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'use_cache',
                    'title': 'Use Cache',
                    'type': 'bool'
                }
            ],
            'required': [
                'use_cache'
            ],
            'pretty_name': 'TenableIO Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'use_cache': True
        }

    def _on_config_update(self, config):
        self.__use_cache = config['use_cache']
