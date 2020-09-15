import datetime
import logging
import csv
import io
import re
from typing import Optional
from ipaddress import ip_address

from axonius.adapter_base import AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.qualys.consts import INVENTORY_TYPE, UNSCANNED_IP_TYPE, ASSET_GROUP_MASTER_PREFIX
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES, QualysAgentVuln, DeviceOpenPort
from axonius.fields import Field, ListField
from axonius.mixins.configurable import Configurable
from axonius.plugin_base import return_error, add_rule
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, int_or_none
from axonius.clients.qualys import consts
from axonius.clients.qualys.connection import QualysScansConnection
from qualys_scans_adapter.structures import InventoryInstance, InventoryContainer, InventoryAgent, InventorySensor, \
    InventoryActivation

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class QualysVulnerability(SmartJsonClass):
    severity = Field(str, 'Severity')
    results = Field(str, 'Results')


class QualysAgentPort(SmartJsonClass):
    port = Field(int, 'Port')
    protocol = Field(str, 'Protocol')
    service_name = Field(str, 'Service Name')


# pylint: disable=too-many-instance-attributes
class QualysReport(SmartJsonClass):
    asset_groups = Field(str, 'Asset Groups')
    technology = Field(str, 'Technology')
    instance = Field(str, 'Instance')
    host_ip = Field(str, 'Host IP')
    dns_hostname = Field(str, 'DNS Hostname')
    netbios_hostname = Field(str, 'NETBios Hostname')
    tracking_method = Field(str, 'Tracking Method')
    status = Field(str, 'Status')
    failure_reason = Field(str, 'Failure Reason')
    os = Field(str, 'OS')
    last_auth = Field(datetime.datetime, 'Last Authentication')
    last_success = Field(datetime.datetime, 'Last Success')


# pylint: disable=too-many-instance-attributes
class QualysTicket(SmartJsonClass):
    number = Field(int, 'Number')
    creation_datetime = Field(datetime.datetime, 'Creation Date')
    current_state = Field(str, 'Current State')
    invalid = Field(bool, 'Invalid')
    assignee_name = Field(str, 'Assignee Name')
    assignee_mail = Field(str, 'Assignee Email')
    assignee_login = Field(str, 'Assignee Login')
    ip = Field(str, 'IP')
    dns_name = Field(str, 'DNS Name')
    service = Field(str, 'Service')
    first_found = Field(datetime.datetime, 'First Found')
    last_found = Field(datetime.datetime, 'Last Found')
    last_scan = Field(datetime.datetime, 'Last Scan')
    title = Field(str, 'Vulnerability Title')
    ticket_type = Field(str, 'Vulnerability Type')
    qid = Field(int, 'Vulnerability QID')
    severity = Field(int, 'Vulnerability Severity')
    cve_id_list = ListField(str, 'Vulnerability CVE IDs')


class QualysAssetGroup(SmartJsonClass):
    id = Field(str, 'ID')
    title = Field(str, 'Title')
    owner_user_id = Field(str, 'Owner User ID')
    owner_username = Field(str, 'Owner User Name')
    owner_unit_id = Field(str, 'Owner Unit ID')
    network_ids = ListField(str, 'Network IDs')
    last_update = Field(str, 'Last Update')
    business_impact = Field(str, 'Business Impact')
    cvss_enviro_cdp = Field(str, 'CVSS Enviro CDP')
    cvss_enviro_td = Field(str, 'CVSS Enviro TD')
    cvss_enviro_cr = Field(str, 'CVSS Enviro CR')
    cvss_enviro_ir = Field(str, 'CVSS Enviro IR')
    cvss_enviro_ar = Field(str, 'CVSS Enviro AR')
    default_appliance_id = Field(str, 'Default Appliance ID')
    appliance_ids = ListField(str, 'Appliance IDs')
    ip_set = ListField(str, 'IP Set')
    domain_list = ListField(str, 'Domain List')
    dns_list = ListField(str, 'Dns List')
    netbios_list = ListField(str, 'NetBios List')
    ec2_ids = ListField(str, 'EC2 IDs')
    assigned_user_ids = ListField(str, 'Assigned User IDs')
    assigned_unit_ids = ListField(str, 'Assigned Unit IDs')
    comments = ListField(str, 'Comments')


class QualysHost(SmartJsonClass):
    last_vm_scan_duration = Field(int, 'Last VM Scan Duration (sec)')
    last_vm_auth_scanned_date = Field(datetime.datetime, 'Last VM Auth Scanned Date')
    last_vm_auth_scanned_duration = Field(int, 'Last VM Auth Scanned Duration (sec)')
    last_vm_scan_date = Field(datetime.datetime, 'Last VM Scan Date')
    last_vulm_scan_datetime = Field(datetime.datetime, 'Last Vuln Scan Date')
    last_compliance_scan_date = Field(datetime.datetime, 'Last Compliance Scan Date')
    last_scap_scan_date = Field(datetime.datetime, 'Last Scap Scan Date')
    asset_groups = ListField(QualysAssetGroup, 'Asset Groups')
    asset_groups_ids = ListField(str, 'Asset Groups IDS')


class QualysScansAdapter(ScannerAdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        qualys_id = Field(str, 'Qualys ID')
        qualys_agnet_ports = ListField(QualysAgentPort, 'Qualys Open Ports')
        qualys_tags = ListField(str, 'Qualys Tags')
        last_vuln_scan = Field(datetime.datetime, 'Last Vuln Scan')
        agent_last_seen = Field(datetime.datetime, 'Agent Last Seen')
        qweb_host_id = Field(int, 'Qweb Host ID')
        tracking_method = Field(str, 'Tracking Method')
        inventory_instance = Field(InventoryInstance, 'Inventory Asset')
        hosts = ListField(QualysHost, 'Hosts')
        tickets = ListField(QualysTicket, 'Tickets')
        report = Field(QualysReport, 'Report')
        unscanned_device = Field(bool, 'Unscanned Device')
        qualys_asset_groups = ListField(str, 'Asset Groups')

        def add_qualys_vuln(self, **kwargs):
            self.qualys_agent_vulns.append(QualysAgentVuln(**kwargs))

        def add_qualys_port(self, **kwargs):
            self.qualys_agnet_ports.append(QualysAgentPort(**kwargs))

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)
        self._qid_info = self.parse_qid_info()

    @staticmethod
    def _parse_qid_info_field(field, value):
        list_fields = ['Sub Category', 'Vendor Reference', 'CVE ID', 'Bugtraq ID']
        time_fields = ['Modified', 'Published']

        result = None
        if not isinstance(value, str):
            raise TypeError(f'Unexpected value {value}')

        result = value.strip()

        if not result:
            result = None

        if result in ['-', '\'-']:
            result = None

        if isinstance(result, str) and field in list_fields:
            result = list(set(r.strip() for r in result.split(',')))

        if isinstance(result, str) and field in time_fields:
            result = datetime.datetime.strptime(result, '%m/%d/%Y at %H:%M:%S (GMT%z)')
        return result

    @staticmethod
    def _get_client_id(client_config):
        return client_config[consts.QUALYS_SCANS_DOMAIN] + '_' + client_config[consts.USERNAME]

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get(consts.QUALYS_SCANS_DOMAIN),
                                                https_proxy=client_config.get('https_proxy'))

    # pylint: disable=too-many-function-args

    def get_connection(self, client_config):
        date_filter = None

        if self._last_seen_timedelta:
            now = datetime.datetime.now(datetime.timezone.utc)
            date_filter = (now - self._last_seen_timedelta).replace(microsecond=0).isoformat()
            date_filter = date_filter.replace('+00:00', '') + 'Z'

        connection = QualysScansConnection(
            domain=client_config[consts.QUALYS_SCANS_DOMAIN],
            username=client_config[consts.USERNAME],
            password=client_config[consts.PASSWORD],
            verify_ssl=client_config.get('verify_ssl') or False,
            date_filter=date_filter,
            request_timeout=self.__request_timeout,
            chunk_size=self.__async_chunk_size,
            max_retries=self.__max_retries,
            retry_sleep_time=self.__retry_sleep_time,
            devices_per_page=self.__devices_per_page,
            https_proxy=client_config.get('https_proxy'),
            fetch_from_inventory=self.__fetch_from_inventory,
            fetch_report=self.__fetch_report,
            fetch_tickets=self.__fetch_tickets,
            fetch_unscanned_ips=self.__fetch_unscanned_ips
        )
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            qualys_tags_white_list = \
                list(set(  # To avoid duplicated
                    client_config.get(consts.QUALYS_TAGS_WHITELIST).split(','))) \
                if client_config.get(consts.QUALYS_TAGS_WHITELIST) \
                else None
            return (self.get_connection(client_config), qualys_tags_white_list)
        except Exception as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config[consts.QUALYS_SCANS_DOMAIN], str(e)
            )
            logger.exception(message)
            raise ClientConnectionException(message)

    # pylint: enable=too-many-function-args

    def _query_devices_by_client(self, client_name, client_data):
        client_data, qualys_tags_white_list = client_data
        with client_data:
            for device_raw in client_data.get_device_list(fetch_asset_groups=self.__fetch_asset_groups,
                                                          fetch_pci_flag=self.__fetch_pci_flag):
                yield (device_raw, qualys_tags_white_list)

    @staticmethod
    def _clients_schema():
        """
        The schema QualysScansAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {'name': consts.QUALYS_SCANS_DOMAIN, 'title': 'Qualys Cloud Platform Domain', 'type': 'string'},
                {'name': consts.USERNAME, 'title': 'User Name', 'type': 'string'},
                {'name': consts.PASSWORD, 'title': 'Password', 'type': 'string', 'format': 'password'},
                {'name': consts.QUALYS_TAGS_WHITELIST, 'title': 'Qualys Tags Whitelist', 'type': 'string'},
                {'name': consts.VERIFY_SSL, 'title': 'Verify SSL', 'type': 'bool'},
                {'name': 'https_proxy', 'title': 'HTTPS Proxy', 'type': 'string'}
            ],
            'required': [consts.QUALYS_SCANS_DOMAIN, consts.USERNAME, consts.PASSWORD, consts.VERIFY_SSL],
            'type': 'array',
        }

    def _refetch_device(self, client_id, client_data, device_id):
        client_data, qualys_tags_white_list = client_data
        with client_data:
            device_raw = client_data.get_device_id_data(device_id)
        return self._create_agent_device(device_raw, qualys_tags_white_list)

    @classmethod
    def parse_qid_info(cls, csv_path=consts.QUALYS_QID_TO_CVE_CSV):
        logger.info('Parsing QID to CVE from csv file')
        qid_info = {}
        try:
            with open(csv_path, 'r') as f:
                entire_csv_file = f.readlines()
                # The first few lines of the file may be data about the download (i.e. street address
                # of the account holder) which will mess up what is interpreted as the csv headers
                # so we find the line with headers and parse from then on
                header_line_number = None
                for i, line in enumerate(entire_csv_file):
                    if 'QID' in line:
                        header_line_number = i
                        break
                if not header_line_number:
                    logger.exception('Could not find CSV headers, stopping parsing')
                    return qid_info

                cleaned_csv_data = entire_csv_file[header_line_number:]
                csv_dict = csv.DictReader(io.StringIO(''.join(cleaned_csv_data)))
                for entry in csv_dict:
                    try:
                        qid = entry.get('QID')
                        if not qid:
                            continue

                        for key, value in entry.items():
                            entry[key] = cls._parse_qid_info_field(key, value)

                        qid_info[qid] = entry
                    except Exception:
                        logger.exception(f'Problem mapping entry {entry}')
                logger.info(f'{len(qid_info)} QIDs mapped')
                return qid_info
        except Exception:
            logger.exception('Problem opening vulnerabilities csv file')
            return qid_info

    @staticmethod
    def _fill_inventory_agent_instance(device_raw: dict, device: InventoryInstance):
        try:
            inventory_agent = InventoryAgent()

            inventory_agent.version = device_raw.get('version')
            inventory_agent.configurable_profile = device_raw.get('configurationProfile')
            inventory_agent.connected_from = device_raw.get('connectedFrom')
            inventory_agent.last_activity = parse_date(device_raw.get('lastActivity'))
            inventory_agent.last_checked_in = parse_date(device_raw.get('lastCheckedIn'))
            inventory_agent.last_inventory = parse_date(device_raw.get('lastInventory'))

            activations = []
            if isinstance(device_raw.get('activations'), list):
                for activation in device_raw.get('activations'):
                    if isinstance(activation, dict):
                        inventory_activation = InventoryActivation()
                        inventory_activation.key = activation.get('key')
                        inventory_activation.status = activation.get('status')
                        activations.append(inventory_activation)
            inventory_agent.activations = activations

            device.inventory_agent = inventory_agent
        except Exception:
            logger.exception(f'Failed creating agent for inventory device {device_raw}')

    @staticmethod
    def _fill_inventory_sensor_instance(device_raw: dict, device: InventoryInstance):
        try:
            sensor = InventorySensor()

            sensor.activated_modules = device_raw.get('activatedForModules')
            sensor.pending_activation_modules = device_raw.get('pendingActivationForModules')
            sensor.last_vm_scan = parse_date(device_raw.get('lastVMScan'))
            sensor.last_compliance_scan = parse_date(device_raw.get('lastComplianceScan'))
            sensor.last_full_scan = parse_date(device_raw.get('lastFullScan'))
            sensor.error_status = device_raw.get('errorStatus')

            device.sensor = sensor
        except Exception:
            logger.exception(f'Failed creating sensor for inventory device {device_raw}')

    @staticmethod
    def _fill_inventory_container_instance(device_raw: dict, device: InventoryInstance):
        try:
            container = InventoryContainer()

            container.product = device_raw.get('product')
            container.version = device_raw.get('version')
            container.num_of_images = device_raw.get('noOfImages')
            container.num_of_container = device_raw.get('noOfContainers')

            device.container = container
        except Exception:
            logger.exception(f'Failed creating container for inventory device {device_raw}')

    def _fill_inventory_asset_instance(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            inventory_instance = InventoryInstance()

            inventory_instance.host_id = device_raw.get('hostId')
            inventory_instance.agent_id = device_raw.get('agentId')
            inventory_instance.create_date = parse_date(device_raw.get('createDate'))
            inventory_instance.sensor_last_update_date = parse_date(device_raw.get('sensorLastUpdatedDate'))
            inventory_instance.asset_type = device_raw.get('assetType')
            inventory_instance.most_frequent_user = device_raw.get('mostFrequentUser')
            inventory_instance.is_container_host = device_raw.get('isContainerHost')
            inventory_instance.is_hypervisor = device_raw.get('isHypervisor')

            if isinstance(device_raw.get('sensor'), dict):
                self._fill_inventory_sensor_instance(device_raw.get('sensor'), inventory_instance)

            if isinstance(device_raw.get('container'), dict):
                self._fill_inventory_container_instance(device_raw.get('container'), inventory_instance)

            if isinstance(device_raw.get('agent'), dict):
                self._fill_inventory_agent_instance(device_raw.get('agent'), inventory_instance)

            device.inventory_instance = inventory_instance
        except Exception:
            logger.exception(f'Failed creating inventory device {device_raw}')

    # pylint: disable=R0912,R0915
    # pylint: disable=too-many-locals
    def _create_inventory_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('assetId')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id
            device.uuid = device_raw.get('hostUUID')
            hostname = device_raw.get('netbiosName') or device_raw.get('dnsName') or device_raw.get('assetName')
            device.hostname = hostname
            device.name = device_raw.get('assetName')
            device.time_zone = device_raw.get('timeZone')
            device.total_physical_memory = device_raw.get('totalMemory')
            device.total_number_of_cores = device_raw.get('cpuCount')
            device.bios_serial = device_raw.get('biosSerialNumber')
            device.virtual_host = device_raw.get('isVirtualMachine')

            last_logged_user = device_raw.get('lastLoggedOnUser') or []
            if isinstance(last_logged_user, str):
                last_logged_user = [last_logged_user]
            device.last_used_users = last_logged_user

            dns_servers = device_raw.get('dnsName') or []
            if isinstance(dns_servers, str):
                dns_servers = [dns_servers]
            device.dns_servers = dns_servers

            mac = device_raw.get('hwSerialNumber')
            ips = device_raw.get('address') or []
            if isinstance(ips, str):
                ips = [ips]
            device.add_nic(mac=mac, ips=ips)

            if device_raw.get('operatingSystem'):
                os = device_raw.get('operatingSystem')
                os_string = (os.get('osName') or '') + ' ' + (os.get('fullName') or '') + ' ' + \
                            (os.get('category') or '') + ' ' + (os.get('productName') or '')
                device.figure_os(os_string=os_string)

            if isinstance(device_raw.get('hardware'), dict):
                hardware = device_raw.get('hardware')
                device.add_connected_hardware(name=hardware.get('fullName'),
                                              manufacturer=hardware.get('manufacturer'),
                                              hw_id=hardware.get('model'))

            open_ports_data = device_raw.get('openPortListData')
            if isinstance(open_ports_data, dict) and isinstance(open_ports_data.get('openPort'), list):
                open_ports = []
                for open_port in open_ports_data.get('openPort'):
                    if isinstance(open_port, dict):
                        open_ports.append(DeviceOpenPort(protocol=open_port.get('protocol'),
                                                         port_id=open_port.get('port'),
                                                         service_name=open_port.get('detectedService')))
                device.open_ports = open_ports
            got_mac = False
            nics_data = device_raw.get('networkInterfaceListData')
            if isinstance(nics_data, dict) and isinstance(nics_data.get('networkInterface'), list):
                for network_interface in nics_data.get('networkInterface'):
                    if not isinstance(network_interface, dict):
                        continue
                    ips = network_interface.get('addressIpV4') or []
                    if isinstance(ips, str):
                        ips = [ips]
                    if isinstance(network_interface.get('addresses'), str) and network_interface.get('addresses'):
                        ips.extend(network_interface.get('addresses').split(','))
                    if network_interface.get('macAddress'):
                        got_mac = True
                    device.add_nic(mac=network_interface.get('macAddress'),
                                   ips=ips,
                                   name=network_interface.get('interfaceName'),
                                   gateway=network_interface.get('gatewayAddress'))

            softwares_data = device_raw.get('softwareListData')
            if isinstance(softwares_data, dict) and isinstance(softwares_data.get('software'), list):
                for software in softwares_data.get('software'):
                    device.add_installed_software(name=software.get('fullName'),
                                                  version=software.get('version'),
                                                  publisher=software.get('publisher'))

            tag_list = device_raw.get('tagList')
            if isinstance(tag_list, dict) and isinstance(tag_list.get('tag'), list):
                for tag_data in tag_list.get('tag'):
                    if isinstance(tag_data, dict):
                        for key, value in tag_data.items():
                            device.add_key_value_tag(key=key, value=value)

            service_list = device_raw.get('serviceList')
            if isinstance(service_list, dict) and isinstance(service_list.get('service'), list):
                for service in service_list.get('service'):
                    if isinstance(service, dict):
                        device.add_service(name=service.get('name'),
                                           display_name=service.get('description'),
                                           status=service.get('status'))

            self._fill_inventory_asset_instance(device_raw, device)

            device.set_raw(device_raw)
            if self.__drop_only_ip_devices and not hostname and not got_mac:
                return None
            return device

        except Exception:
            logger.exception(f'Problem with fetching Inventory Device for {device_raw}')
            return None

    @staticmethod
    def _create_unscanned_ips(device_raw: str, device: MyDeviceAdapter):
        try:
            if device_raw is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            # Verify its an IP
            try:
                ip_address(device_raw)
            except Exception:
                logger.warning(f'Incorrect IP format received for unscanned ip {device_raw}')
                return None
            device.id = device_raw
            device.unscanned_device = True

            device.add_ips_and_macs(ips=[device_raw])

            device.set_raw({'ip': device_raw})
            return device

        except Exception:
            logger.exception(f'Problem with fetching unscanned ips Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for (device_raw_data, qualys_tags_white_list) in devices_raw_data:
            if len(device_raw_data) == 2:
                device_raw, device_type = device_raw_data
            else:
                logger.error(f'Got bad device raw data. Expected 2-tuple, got instead: {device_raw_data}')
                continue
            if device_type == UNSCANNED_IP_TYPE and self.__fetch_unscanned_ips:
                device = self._create_unscanned_ips(device_raw, self._new_device_adapter())
            elif device_type == INVENTORY_TYPE and self.__fetch_from_inventory:
                # noinspection PyTypeChecker
                device = self._create_inventory_device(device_raw, self._new_device_adapter())
            else:
                device = self._create_agent_device(device_raw, qualys_tags_white_list)

            if device:
                yield device

    # pylint: disable=R0912,R0915,too-many-nested-blocks
    # pylint: disable=too-many-locals
    def _create_agent_device(self, device_raw, qualys_tags_white_list=None):
        tags_ok = False
        if not qualys_tags_white_list or not isinstance(qualys_tags_white_list, list):
            qualys_tags_white_list = []
            tags_ok = True
        try:
            device_raw = device_raw.get('HostAsset')
            device_id = device_raw.get('id')
            if not device_id:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device = self._new_device_adapter()
            got_hostname = False
            got_mac = False
            device.qualys_id = device_id
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')
            hostname = (device_raw.get('netbiosName') or device_raw.get('dnsHostName')) or device_raw.get('name')
            if device_raw.get('netbiosName') and device_raw.get('dnsHostName') and \
                    device_raw.get('dnsHostName').split('.')[0].lower() == \
                    device_raw.get('netbiosName').split('.')[0].lower():
                hostname = device_raw.get('dnsHostName')
            if hostname != device_raw.get('address'):
                if hostname:
                    got_hostname = True
                device.hostname = hostname
                try:
                    if hostname and device_raw.get('fqdn') \
                            and hostname.lower().split('.')[0] == device_raw.get('fqdn').lower().split('.')[0]:
                        device.hostname = device_raw.get('fqdn')
                except Exception:
                    pass
            if device_raw.get('dnsHostName') and device_raw.get('name'):
                device.name = device_raw.get('name')
            try:
                device.figure_os(device_raw.get('os'))
            except Exception:
                logger.exception(f'Problem getting OS from {device_raw}')
            try:
                last_vuln_scan = parse_date(device_raw.get('lastVulnScan'))
                device.last_vuln_scan = last_vuln_scan
                agent_last_seen = parse_date((device_raw.get('agentInfo') or {}).get('lastCheckedIn'))
                device.agent_last_seen = agent_last_seen
                if agent_last_seen and last_vuln_scan:
                    device.last_seen = max(last_vuln_scan, agent_last_seen)
                elif agent_last_seen or last_vuln_scan:
                    device.last_seen = agent_last_seen or last_vuln_scan
            except Exception:
                logger.exception(f'Problem getting last seen for {device_raw}')
            device.add_agent_version(agent=AGENT_NAMES.qualys_scans,
                                     version=(device_raw.get('agentInfo') or {}).get('agentVersion'),
                                     status=(device_raw.get('agentInfo') or {}).get('status'))
            device.physical_location = (device_raw.get('agentInfo') or {}).get('location')
            if device_raw.get('lastSystemBoot'):
                device.set_boot_time(boot_time=parse_date(str(device_raw.get('lastSystemBoot'))))
            try:
                if not device_raw.get('networkInterface') and device_raw.get('address'):
                    device.add_nic(ips=[device_raw.get('address')])
                for asset_interface in (device_raw.get('networkInterface') or {}).get('list') or []:
                    try:
                        if self.__use_dns_host_as_hostname:
                            if (asset_interface.get('HostAssetInterface') or {}).get('hostname'):
                                got_hostname = True
                                device.hostname = (asset_interface.get('HostAssetInterface') or {}).get('hostname')
                        mac = (asset_interface.get('HostAssetInterface') or {}).get('macAddress')
                        if not mac:
                            mac = None
                        else:
                            got_mac = True
                        ip = (asset_interface.get('HostAssetInterface') or {}).get('address')
                        if not ip:
                            ips = None
                        else:
                            ips = [ip]
                        if mac or ips:
                            device.add_nic(mac=mac, ips=ips)
                    except Exception:
                        logger.exception(f'Problem with interface {asset_interface}')
            except Exception:
                logger.exception(f'Problem with adding nics to Qualys agent {device_raw}')

            try:
                for tag_raw in (device_raw.get('tags') or {}).get('list') or []:
                    if not isinstance(tag_raw, dict):
                        logger.warning(f'Invalid tag found {tag_raw}')
                        continue
                    tag_name: Optional[str] = (tag_raw.get('TagSimple') or {}).get('name')
                    if not (tag_name and isinstance(tag_name, str)):
                        logger.warning(f'Tag with no/invalid name: {tag_raw}')
                        continue
                    try:
                        if tag_name in qualys_tags_white_list:
                            tags_ok = True
                        device.qualys_tags.append(tag_name)
                    except Exception:
                        logger.exception(f'Problem with tag {tag_raw}')
                    try:
                        if tag_name.startswith(ASSET_GROUP_MASTER_PREFIX):
                            asset_group = tag_name[len(ASSET_GROUP_MASTER_PREFIX):]
                            if asset_group:
                                device.qualys_asset_groups.append(asset_group)
                            else:
                                logger.warning(f'empty asset_group {tag_raw}')
                    except Exception:
                        logger.exception(f'Problem with asset_group from tag {tag_raw}')
            except Exception:
                logger.exception(f'Problem with adding tags to Qualys agent {device_raw}')

            try:
                for user_raw in (device_raw.get('account') or {}).get('list') or []:
                    try:
                        if (user_raw.get('HostAssetAccount') or {}).get('username'):
                            device.last_used_users.append((user_raw.get('HostAssetAccount') or {}).get('username'))
                    except Exception:
                        logger.exception(f'Problem with user {user_raw}')
            except Exception:
                logger.exception(f'Problem with adding users to Qualys agent {device_raw}')

            try:
                for software_raw in (device_raw.get('software') or {}).get('list') or []:
                    try:
                        device.add_installed_software(
                            name=(software_raw.get('HostAssetSoftware') or {}).get('name'),
                            version=(software_raw.get('HostAssetSoftware') or {}).get('version'),
                        )
                    except Exception:
                        logger.exception(f'Problem with software {software_raw}')
            except Exception:
                logger.exception(f'Problem with adding software to Qualys agent {device_raw}')
            try:
                vulns_raw = (device_raw.get('vuln') or {}).get('list') or []
                if self.__fetch_vulnerabilities_data is False:
                    vulns_raw = []
                for vuln_raw in vulns_raw:
                    try:

                        qid = str((vuln_raw.get('HostAssetVuln') or {}).get('qid'))
                        qid_info_entry = self._qid_info.get(qid) or {}
                        vuln_type = None
                        severity = None
                        if qid_info_entry:
                            vuln_raw['QidInfo'] = qid_info_entry
                            match = re.match(r'(.*) - level (\d*)', qid_info_entry.get('Severity') or '')
                            if match:
                                vuln_type, severity = match.groups()
                                vuln_type = vuln_type.strip()
                                severity = severity.strip()

                        if vuln_type == 'Vulnerability':
                            vuln_type = 'Confirmed Vulnerability'

                        device.add_qualys_vuln(
                            vuln_id=(vuln_raw.get('HostAssetVuln') or {}).get('hostInstanceVulnId'),
                            last_found=parse_date((vuln_raw.get('HostAssetVuln') or {}).get('lastFound')),
                            first_found=parse_date((vuln_raw.get('HostAssetVuln') or {}).get('firstFound')),
                            qid=qid,
                            severity=severity,
                            vuln_type=vuln_type,
                            title=qid_info_entry.get('Title'),
                            category=qid_info_entry.get('Category'),
                            sub_category=qid_info_entry.get('Sub Category'),
                            vendor_reference=qid_info_entry.get('Vendor Reference'),
                            qualys_cve_id=qid_info_entry.get('CVE ID'),
                            cvss_base=qid_info_entry.get('CVSS Base'),
                            cvss3_base=qid_info_entry.get('CVSS3 Base'),
                            cvss_temporal_score=qid_info_entry.get('CVSS Temporal Score'),
                            cvss3_temporal_score=qid_info_entry.get('CVSS3 Temporal Score'),
                            cvss_access_vector=qid_info_entry.get('CVSS Access Vector'),
                            bugtraq_id=qid_info_entry.get('Bugtraq ID'),
                            modified=qid_info_entry.get('Modified'),
                            published=qid_info_entry.get('Published'),
                            pci_flag=parse_bool_from_raw((vuln_raw.get('HostAssetVuln') or {}).get('extra_pci_flag'))
                        )
                    except Exception:
                        logger.exception(f'Problem with vuln {vuln_raw}')
                    try:
                        qid = str((vuln_raw.get('HostAssetVuln') or {}).get('qid')) or ''
                        if qid:
                            for cve in qid_info_entry.get('CVE ID') or []:
                                device.add_vulnerable_software(cve_id=cve)
                    except Exception:
                        logger.exception(f'Problem with adding vuln software for {vuln_raw}')
            except Exception:
                logger.exception(f'Problem with adding software to Qualys agent {device_raw}')

            try:
                for port_raw in (device_raw.get('openPort') or {}).get('list') or []:
                    try:
                        device.add_qualys_port(
                            port=(port_raw.get('HostAssetOpenPort') or {}).get('port'),
                            protocol=(port_raw.get('HostAssetOpenPort') or {}).get('protocol'),
                            service_name=(port_raw.get('HostAssetOpenPort') or {}).get('serviceName'),
                        )
                    except Exception:
                        logger.exception(f'Problem with port {port_raw}')
                    try:
                        device.add_open_port(
                            protocol=(port_raw.get('HostAssetOpenPort') or {}).get('protocol'),
                            port_id=(port_raw.get('HostAssetOpenPort') or {}).get('port'),
                            service_name=(port_raw.get('HostAssetOpenPort') or {}).get('serviceName')
                        )
                    except Exception:
                        logger.exception(f'Failed to add open port {port_raw}')
            except Exception:
                logger.exception(f'Problem with adding software to Qualys agent {device_raw}')

            try:
                extra_hosts = device_raw.get('extra_host')

                if isinstance(extra_hosts, list):
                    hosts = []
                    for extra_host in extra_hosts:
                        if isinstance(extra_host, dict):
                            host = QualysHost()

                            host.last_vm_scan_duration = int_or_none(extra_host.get('LAST_VM_SCANNED_DURATION'))
                            host.last_vm_auth_scanned_date = parse_date(extra_host.get('LAST_VM_AUTH_SCANNED_DATE'))
                            host.last_vm_auth_scanned_duration = int_or_none(
                                extra_host.get('LAST_VM_AUTH_SCANNED_DURATION'))
                            host.last_vm_scan_date = parse_date(extra_host.get('LAST_VM_SCANNED_DATE'))
                            host.last_vulm_scan_datetime = parse_date(extra_host.get('LAST_VULN_SCAN_DATETIME'))
                            host.last_compliance_scan_date = parse_date(extra_host.get('LAST_COMPLIANCE_SCAN_DATETIME'))
                            host.last_scap_scan_date = parse_date(extra_host.get('LAST_SCAP_SCAN_DATETIME'))
                            if isinstance(extra_host.get('ASSET_GROUP_IDS'), str):
                                host.asset_groups_ids = [extra_host.get('ASSET_GROUP_IDS')]
                            elif isinstance(extra_host.get('ASSET_GROUP_IDS'), list):
                                host.asset_groups_ids = extra_host.get('ASSET_GROUP_IDS')

                            asset_groups = extra_host.get('extra_asset_groups')
                            host.asset_groups = []
                            if isinstance(extra_host.get('extra_asset_groups'), list):
                                for asset_group_raw in asset_groups:
                                    asset_group = QualysAssetGroup()
                                    asset_group.id = asset_group_raw.get('ID')
                                    asset_group.title = asset_group_raw.get('TITLE')
                                    asset_group.owner_user_id = asset_group_raw.get('OWNER_USER_ID')
                                    asset_group.owner_unit_id = asset_group_raw.get('OWNER_UNIT_ID')
                                    asset_group.last_update = asset_group_raw.get('LAST_UPDATE')
                                    asset_group.business_impact = asset_group_raw.get('BUSINESS_IMPACT')
                                    asset_group.cvss_enviro_cdp = asset_group_raw.get('CVSS_ENVIRO_CDP')
                                    asset_group.cvss_enviro_td = asset_group_raw.get('CVSS_ENVIRO_TD')
                                    asset_group.cvss_enviro_cr = asset_group_raw.get('CVSS_ENVIRO_CR')
                                    asset_group.cvss_enviro_ir = asset_group_raw.get('CVSS_ENVIRO_IR')
                                    asset_group.cvss_enviro_ar = asset_group_raw.get('CVSS_ENVIRO_AR')
                                    asset_group.default_appliance_id = asset_group_raw.get('DEFAULT_APPLIANCE_ID')
                                    asset_group.owner_username = asset_group_raw.get('OWNER_USER_NAME')

                                    if isinstance(asset_group_raw.get('APPLIANCE_IDS'), list):
                                        asset_group.appliance_ids = asset_group_raw.get('APPLIANCE_IDS')
                                    elif isinstance(asset_group_raw.get('APPLIANCE_IDS'), str):
                                        asset_group.appliance_ids = [asset_group_raw.get('APPLIANCE_IDS')]

                                    asset_group.ip_set = []
                                    if isinstance(asset_group_raw.get('IP_SET'), dict):
                                        if isinstance(asset_group_raw.get('IP_SET').get('IP'), list):
                                            asset_group.ip_set.extend(asset_group_raw.get('IP_SET').get('IP'))
                                        if isinstance(asset_group_raw.get('IP_SET').get('IP'), str):
                                            asset_group.ip_set.append(asset_group_raw.get('IP_SET').get('IP'))

                                        if isinstance(asset_group_raw.get('IP_SET').get('IP_RANGE'), list):
                                            asset_group.ip_set.extend(asset_group_raw.get('IP_SET').get('IP_RANGE'))
                                        if isinstance(asset_group_raw.get('IP_SET').get('IP_RANGE'), str):
                                            asset_group.ip_set.append(asset_group_raw.get('IP_SET').get('IP_RANGE'))

                                    if isinstance(asset_group_raw.get('DOMAIN_LIST'), list):
                                        asset_group.domain_list = asset_group_raw.get('DOMAIN_LIST')
                                    elif isinstance(asset_group_raw.get('DOMAIN_LIST'), str):
                                        asset_group.domain_list = [asset_group_raw.get('DOMAIN_LIST')]

                                    if isinstance(asset_group_raw.get('DNS_LIST'), dict):
                                        if isinstance(asset_group_raw.get('DNS_LIST').get('DNS'), list):
                                            asset_group.dns_list = asset_group_raw.get('DNS_LIST').get('DNS')
                                        elif isinstance(asset_group_raw.get('DNS_LIST').get('DNS'), str):
                                            asset_group.dns_list = [asset_group_raw.get('DNS_LIST').get('DNS')]

                                    if isinstance(asset_group_raw.get('NETBIOS_LIST'), dict):
                                        if isinstance(asset_group_raw.get('NETBIOS_LIST').get('NETBIOS'), list):
                                            asset_group.netbios_list = asset_group_raw.get(
                                                'NETBIOS_LIST').get('NETBIOS')
                                        elif isinstance(asset_group_raw.get('NETBIOS_LIST').get('NETBIOS'), str):
                                            asset_group.netbios_list = [
                                                asset_group_raw.get('NETBIOS_LIST').get('NETBIOS')]

                                    if isinstance(asset_group_raw.get('EC2_IDS'), list):
                                        asset_group.ec2_ids = asset_group_raw.get('EC2_IDS')
                                    elif isinstance(asset_group_raw.get('EC2_IDS'), str):
                                        asset_group.ec2_ids = [asset_group_raw.get('EC2_IDS')]

                                    if isinstance(asset_group_raw.get('ASSIGNED_USER_IDS'), list):
                                        asset_group.assigned_user_ids = asset_group_raw.get('ASSIGNED_USER_IDS')
                                    elif isinstance(asset_group_raw.get('ASSIGNED_USER_IDS'), str):
                                        asset_group.assigned_user_ids = [asset_group_raw.get('ASSIGNED_USER_IDS')]

                                    if isinstance(asset_group_raw.get('ASSIGNED_UNIT_IDS'), list):
                                        asset_group.assigned_unit_ids = asset_group_raw.get('ASSIGNED_UNIT_IDS')
                                    elif isinstance(asset_group_raw.get('ASSIGNED_UNIT_IDS'), str):
                                        asset_group.assigned_unit_ids = [asset_group_raw.get('ASSIGNED_UNIT_IDS')]

                                    if isinstance(asset_group_raw.get('COMMENTS'), list):
                                        asset_group.comments = asset_group_raw.get('COMMENTS')
                                    if isinstance(asset_group_raw.get('COMMENTS'), str):
                                        asset_group.comments = [asset_group_raw.get('COMMENTS')]

                                    if isinstance(asset_group_raw.get('NETWORK_IDS'), list):
                                        asset_group.network_ids = asset_group_raw.get('NETWORK_ID')
                                    elif isinstance(asset_group_raw.get('NETWORK_ID'), str):
                                        asset_group.network_ids = [asset_group_raw.get('NETWORK_IDS')]
                                    host.asset_groups.append(asset_group)
                            hosts.append(host)
                    device.hosts = hosts
            except Exception as e:
                logger.warning(f'Failed parsing device hosts information: {extra_hosts} - {str(e)}', exc_info=True)

            extra_report = device_raw.get('extra_report')
            if isinstance(extra_report, dict) and extra_report:
                report_ticket = QualysReport()

                report_ticket.asset_groups = extra_report.get('Asset Groups')
                report_ticket.technology = extra_report.get('Technology')
                report_ticket.instance = extra_report.get('Instance')
                report_ticket.host_ip = extra_report.get('Host IP')
                report_ticket.dns_hostname = extra_report.get('DNS Hostname')
                report_ticket.netbios_hostname = extra_report.get('NetBIOS Hostnam')
                report_ticket.tracking_method = extra_report.get('Tracking Method')
                report_ticket.status = extra_report.get('Status')
                report_ticket.failure_reason = extra_report.get('Failure Reason')
                # pylint: disable=invalid-name
                report_ticket.os = extra_report.get('OS')
                try:
                    report_ticket.last_auth = parse_date(extra_report.get('Last Auth'))
                except Exception:
                    pass
                try:
                    report_ticket.last_success = parse_date(extra_report.get('Last Success'))
                except Exception:
                    pass

                device.report = report_ticket

            try:
                extra_tickets = device_raw.get('extra_tickets')
                if isinstance(extra_tickets, list):
                    tickets = []
                    for extra_ticket in extra_tickets:
                        if isinstance(extra_ticket, dict):
                            ticket = QualysTicket()

                            ticket.number = int_or_none(extra_ticket.get('NUMBER'))
                            ticket.creation_datetime = parse_date(extra_ticket.get('CREATION_DATETIME'))
                            ticket.current_state = extra_ticket.get('CURRENT_STATE')
                            ticket.invalid = parse_bool_from_raw(extra_ticket.get('INVALID'))
                            assignee = extra_ticket.get('ASSIGNEE')
                            if isinstance(assignee, dict):
                                ticket.assignee_name = assignee.get('NAME')
                                ticket.assignee_mail = assignee.get('EMAIL')
                                ticket.assignee_login = assignee.get('LOGIN')
                            detection = extra_ticket.get('DETECTION')
                            if isinstance(detection, dict):
                                ticket.ip = detection.get('IP')
                                ticket.dns_name = detection.get('DNSNAME')
                                ticket.service = detection.get('SERVICE')
                            stats = extra_ticket.get('STATS')
                            if isinstance(stats, dict):
                                ticket.first_found = parse_date(stats.get('FIRST_FOUND_DATETIME'))
                                ticket.last_found = parse_date(stats.get('LAST_FOUND_DATETIME'))
                                ticket.last_scan = parse_date(stats.get('LAST_SCAN_DATETIME'))
                            vuln = extra_ticket.get('VULN')
                            if isinstance(vuln, dict):
                                ticket.title = vuln.get('TITLE')
                                ticket.ticket_type = vuln.get('TYPE')
                                ticket.qid = int_or_none(vuln.get('QID'))
                                ticket.severity = int_or_none(vuln.get('SEVERITY'))
                                if isinstance(vuln.get('CVE_ID_LIST'), list):
                                    ticket.cve_id_list = vuln.get('CVE_ID_LIST')

                            tickets.append(ticket)
                    device.tickets = tickets
            except Exception as e:
                logger.warning(f'Failed parsing device ticket information: {extra_tickets} - {str(e)}')

            device.adapter_properties = [AdapterProperty.Vulnerability_Assessment.name]
            device.qweb_host_id = device_raw.get('qwebHostId') \
                if isinstance(device_raw.get('qwebHostId'), int) else None
            device.tracking_method = device_raw.get('trackingMethod')
            if self.__fetch_vulnerabilities_data is False:
                device_raw.pop('vuln', None)
            device.set_raw(device_raw)
            if not tags_ok:
                return None
            if self.__drop_only_ip_devices and not got_mac and not got_hostname:
                return None
            return device
        except Exception:
            logger.exception(f'Problem with device {device_raw}')
            return None

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'request_timeout',
                    'title': 'Request timeout',
                    'type': 'integer'
                },
                {
                    'name': 'async_chunk_size',
                    'title': 'Chunk size',
                    'type': 'integer',
                },
                {
                    'name': 'devices_per_page',
                    'title': 'Devices per page',
                    'type': 'integer',
                },
                {
                    'name': 'retry_sleep_time',
                    'title': 'Intervals between retries (seconds)',
                    'type': 'integer',
                },
                {
                    'name': 'max_retries',
                    'title': 'Number of retries',
                    'type': 'integer',
                },
                {
                    'name': 'fetch_vulnerabilities_data',
                    'type': 'bool',
                    'title': 'Fetch vulnerabilities data'
                },
                {
                    'name': 'fetch_from_inventory',
                    'type': 'bool',
                    'title': 'Use Inventory API'
                },
                {
                    'name': 'fetch_report',
                    'type': 'bool',
                    'title': 'Fetch authentication report'
                },
                {
                    'name': 'fetch_tickets',
                    'type': 'bool',
                    'title': 'Fetch tickets'
                },
                {
                    'name': 'use_dns_host_as_hostname',
                    'type': 'bool',
                    'title': 'Use DNS name as hostname even if NetBIOS name exists'
                },
                {
                    'name': 'fetch_unscanned_ips',
                    'type': 'bool',
                    'title': 'Fetch unscanned IP addresses'
                },
                {
                    'name': 'fetch_asset_groups',
                    'type': 'bool',
                    'title': 'Fetch Asset Groups'
                },
                {
                    'name': 'drop_only_ip_devices',
                    'title': 'Do not fetch devices with no MAC address and no hostname',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_pci_flag',
                    'type': 'bool',
                    'title': 'Fetch PCI Flag'
                }
            ],
            'required': [
                'request_timeout',
                'async_chunk_size',
                'fetch_vulnerabilities_data',
                'max_retries',
                'retry_sleep_time',
                'drop_only_ip_devices',
                'devices_per_page',
                'fetch_from_inventory', 'use_dns_host_as_hostname',
                'fetch_report',
                'fetch_tickets',
                'fetch_unscanned_ips',
                'fetch_asset_groups',
                'fetch_pci_flag'
            ],
            'pretty_name': 'Qualys Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'request_timeout': consts.DEFAULT_REQUEST_TIMEOUT,
            'async_chunk_size': consts.DEFAULT_CHUNK_SIZE,
            'retry_sleep_time': consts.RETRY_SLEEP_TIME,
            'max_retries': consts.MAX_RETRIES,
            'devices_per_page': consts.DEVICES_PER_PAGE,
            'fetch_vulnerabilities_data': True,
            'fetch_from_inventory': False,
            'use_dns_host_as_hostname': False,
            'fetch_unscanned_ips': False,
            'fetch_report': False,
            'fetch_tickets': False,
            'drop_only_ip_devices': False,
            'fetch_asset_groups': False,
            'fetch_pci_flag': False
        }

    @add_rule('add_tag_to_ids', methods=['POST'])
    def add_tag_to_ids(self):
        if self.get_method() != 'POST':
            return return_error('Method not supported', 405)
        tag_action_dict = self.get_request_data_as_object()
        success = False
        error_message = 'Failure'
        for client_id in self._clients:
            try:
                conn = self.get_connection(self._get_client_config_by_client_id(client_id))
                with conn:
                    result_status, error_message = conn.add_tags_to_qualys_ids(tag_action_dict)
                    success = success or result_status
                    if success is True:
                        return '', 200
                    logger.warning(f'client_id "{client_id}" failed adding tags. error: {error_message}')
            except Exception:
                logger.exception(f'Could not connect to {client_id}')
        return error_message, 400

    def _on_config_update(self, config):
        self.__request_timeout = config['request_timeout']
        self.__async_chunk_size = config['async_chunk_size']
        self.__fetch_vulnerabilities_data = config['fetch_vulnerabilities_data'] \
            if 'fetch_vulnerabilities_data' in config else True
        self.__max_retries = config.get('max_retries', consts.MAX_RETRIES)
        self.__retry_sleep_time = config.get('max_retries', consts.RETRY_SLEEP_TIME)
        self.__devices_per_page = config.get('devices_per_page', consts.DEVICES_PER_PAGE)
        self.__fetch_from_inventory = config.get('fetch_from_inventory', False)
        self.__use_dns_host_as_hostname = config.get('use_dns_host_as_hostname', False)
        self.__fetch_report = config.get('fetch_report', False)
        self.__fetch_tickets = config.get('fetch_tickets', False)
        self.__fetch_unscanned_ips = config.get('fetch_unscanned_ips', False)
        self.__fetch_asset_groups = parse_bool_from_raw(config.get('fetch_asset_groups')) or False
        self.__drop_only_ip_devices = parse_bool_from_raw(config.get('drop_only_ip_devices')) or False
        self.__fetch_pci_flag = parse_bool_from_raw(config.get('fetch_pci_flag')) or False

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network, AdapterProperty.Vulnerability_Assessment]
