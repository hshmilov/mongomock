import datetime
import logging
logger = logging.getLogger(f'axonius.{__name__}')
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.utils.files import get_local_config_file
from axonius.clients.rest.exception import RESTException
from fireeye_hx_adapter.connection import FireeyeHxConnection
from fireeye_hx_adapter import consts
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.clients.rest.connection import RESTConnection


class FireeyeHxAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        excluded_from_containment = Field(bool, 'Excluded From Containment')
        reported_clone = Field(bool, 'Reported Clone')
        fips = Field(str, 'FIPS')
        bios_date = Field(datetime.datetime, 'Bios Date')
        bios_type = Field(str, 'Bios Type')
        build_number = Field(int, 'Build Number')
        clock_skew = Field(str, 'Clock Skew')
        availphysical = Field(int, 'Available Physical')
        last_poll_ip = Field(str, 'Last Poll IP')
        last_poll_timestamp = Field(datetime.datetime, 'Last Poll Timestamp')
        app_created = Field(datetime.datetime, 'App Created')
        app_started = Field(datetime.datetime, 'App Started')
        install_date = Field(datetime.datetime, 'Install Date')
        kernel_services_status = Field(str, 'Kernel Services Status')
        alerting_conditions = Field(int, 'Alerting Conditions')
        acqs = Field(int, 'Acqs')
        stats_alerts = Field(int, 'Stats Alerts')
        execution_hits_count = Field(int, 'Execution Hits Count')
        exploit_alerts = Field(int, 'Exploit Alerts')
        exploit_blocks = Field(int, 'Exploit Blocks')
        false_positive_alerts = Field(int, 'False Positive Alerts')
        generic_alerts = Field(int, 'Generic Alerts')
        has_execution_hits = Field(bool, 'Has Execution Hits')
        has_presence_hits = Field(bool, 'Has Presence Hits')
        last_hit = Field(datetime.datetime, 'Last Hit')
        malware_alerts = Field(int, 'Malware Alerts')
        malware_cleaned_count = Field(int, 'Malware Cleaned Count')
        malware_false_positive_alerts = Field(int, 'Malware False Positive Alerts')
        malware_quarantined_count = Field(int, 'Malware Quarantined Count')
        presence_hits_count = Field(int, 'Presence Hits Count')
        containment_state = Field(str, 'Containment State')
        recent_triage_action = Field(str, 'Recent Triage Action')
        recent_triage_id = Field(str, 'Recent Triage Id')
        recent_triage_state = Field(str, 'Recent Triage State')
        intel_version = Field(str, 'Intel Version')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get("domain"), client_config.get("port"))

    def _connect_client(self, client_config):
        try:
            connection = FireeyeHxConnection(domain=client_config["domain"], verify_ssl=client_config["verify_ssl"],
                                             username=client_config["username"], password=client_config["password"],
                                             url_base_prefix="hx/api/v3", https_proxy=client_config.get('https_proxy'),
                                             port=client_config.get("port") or consts.DEFAULT_PORT,
                                             headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
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
        The schema FireeyeHxAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "domain",
                    "title": "FireEye Endpoint Security Domain",
                    "type": "string"
                },
                {
                    "name": "port",
                    "title": "Port",
                    "type": "integer",
                    "format": "port",
                    'default': consts.DEFAULT_PORT
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
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            "required": [
                "domain",
                "username",
                "password",
                "verify_ssl"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device.id = device_raw.get("_id", "")
                if device.id == "":
                    continue
                try:
                    ip_address = device_raw.get("primary_ip_address") or ""
                    mac_address = device_raw.get("primary_mac")
                    device.add_nic(mac_address, ip_address.split(","))
                except Exception:
                    logger.exception(f"Problem getting nic for {device_raw}")
                try:
                    device.last_seen = parse_date(str(device_raw.get("last_audit_timestamp")))
                except Exception:
                    logger.exception(f"Problem getting last seen for {device_raw}")
                if isinstance(device_raw.get('KernelServices'), dict):
                    device.kernel_services_status = device_raw.get('KernelServices').get('Status')
                try:
                    os_raw = device_raw.get("os")
                    device.figure_os((os_raw.get("product_name") or "") + " " + (os_raw.get("bitness") or ""))
                except Exception:
                    logger.exception(f"Problem getting os for {device_raw}")
                device.add_agent_version(agent=AGENT_NAMES.fireeye_hx, version=device_raw.get('agent_version'),
                                         status=device_raw.get('stateAgentStatus'))
                try:
                    hostname = device_raw.get("hostname")
                    device.hostname = hostname
                    domain = device_raw.get("domain")
                    if domain is not None and domain != "" and str(domain).lower()\
                            not in ["workgroup", "local", "n/a"] and domain.lower() != hostname.lower():
                        device.domain = domain
                except Exception:
                    logger.exception(f"Problem getting hostname {device_raw}")
                device.first_seen = parse_date(device_raw.get('initial_agent_checkin'))
                device.last_poll_ip = device_raw.get('last_poll_ip')
                device.excluded_from_containment = bool(device_raw.get('excluded_from_containment'))
                device.time_zone = device_raw.get("timezone")
                device.reported_clone = bool(device_raw.get('reported_clone'))
                device.last_poll_timestamp = parse_date(device_raw.get('last_poll_timestamp'))
                try:
                    uptime = device_raw.get('uptime')
                    if uptime:
                        uptime = str(uptime).strip('PT').strip('S')
                        device.set_boot_time(uptime=datetime.timedelta(seconds=int(uptime)))
                except Exception:
                    pass
                try:
                    sys_info = device_raw.get('sysinfo')
                    if isinstance(sys_info, dict):
                        device.fips = sys_info.get('FIPS')
                        device.intel_version = sys_info.get('intelVersion')
                        device.clock_skew = sys_info.get('clockSkew')
                        try:
                            bios_info = sys_info.get('biosInfo')
                            if isinstance(bios_info, dict):
                                device.bios_type = sys_info.get('biosType')
                                device.bios_version = sys_info.get('biosVersion')
                                device.bios_date = parse_date(sys_info.get('biosDate'))
                        except Exception:
                            logger.exception(f'Problem with bios data')
                        device.app_created = parse_date(sys_info.get('appCreated'))
                        device.app_started = parse_date(sys_info.get('appStarted'))
                        device.install_date = parse_date(sys_info.get('installDate'))
                        try:
                            device.availphysical = int(sys_info.get('availphysical'))
                        except Exception:
                            pass
                        try:
                            device.build_number = int(sys_info.get('buildNumber'))
                        except Exception:
                            pass

                except Exception:
                    logger.exception(f'Problem getting sys info')
                device.containment_state = device_raw.get('containment_state')
                try:
                    triages = device_raw.get('triages')
                    if isinstance(triages, dict):
                        device.recent_triage_action = triages.get('recent_triage_action')
                        device.recent_triage_id = triages.get('recent_triage_id')
                        device.recent_triage_state = triages.get('recent_triage_state')
                except Exception:
                    logger.exception('Problem with triages')
                try:
                    device_stats = device_raw.get('stats')
                    if not isinstance(device_stats, dict):
                        device_stats = {}
                    device.acqs = device_stats.get('acqs')
                    device.alerting_conditions = device_stats.get('alerting_conditions')
                    device.stats_alerts = device_stats.get('alerts')
                    device.execution_hits_count = device_stats.get('execution_hits_count')
                    device.exploit_alerts = device_stats.get('exploit_alerts')
                    device.exploit_blocks = device_stats.get('exploit_blocks')
                    device.false_positive_alerts = device_stats.get('false_positive_alerts')
                    device.generic_alerts = device_stats.get('generic_alerts')
                    device.has_execution_hits = device_stats.get('has_execution_hits')
                    device.has_presence_hits = device_stats.get('has_presence_hits')
                    device.last_hit = parse_date(device_stats.get('last_hit'))
                    device.malware_alerts = device_stats.get('malware_alerts')
                    device.malware_cleaned_count = device_stats.get('malware_cleaned_count')
                    device.malware_false_positive_alerts = device_stats.get('malware_false_positive_alerts')
                    device.malware_quarantined_count = device_stats.get('malware_quarantined_count')
                    device.presence_hits_count = device_stats.get('presence_hits_count')

                except Exception:
                    logger.exception(f'Problem adding stats {device_raw}')

                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f"Problem with fetching FireeyeHx Device {device_raw}")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
