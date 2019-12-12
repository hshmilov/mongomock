import datetime
import logging
import csv
import io
import re

from axonius.adapter_base import AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.fields import Field, ListField
from axonius.mixins.configurable import Configurable
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from qualys_scans_adapter import consts
from qualys_scans_adapter.connection import QualysScansConnection

logger = logging.getLogger(f'axonius.{__name__}')


class QualysVulnerability(SmartJsonClass):
    severity = Field(str, 'Severity')
    results = Field(str, 'Results')


QUALYS_SUB_CATEGORIES = ['Authenticated Discovery',
                         'Malware Associated',
                         'Unix Authenticated Discovery',
                         'Remote Discovery',
                         'Patch Available',
                         'PANOS Authenticated Discovery',
                         'MongoDB Authenticated Discovery',
                         'MARIADB Authenticated Discovery',
                         'Not exploitable due to configuration',
                         'Exploit Available',
                         'SNMP Authenticated Discovery',
                         'Non-running services',
                         'Windows Authenticated Discovery',
                         'VMware Authenticated Discovery',
                         'MySQL Authenticated Discovery',
                         'Oracle Authenticated Discovery',
                         'Remote DiscoveryAuthenticated Discovery',
                         'DB2 Authenticated Discovery']

QUALYS_CATEGORIES = ['Debian',
                     'HP-UX',
                     'Amazon Linux',
                     'Hardware',
                     'Fedora',
                     'RPC',
                     'Finger',
                     'SUSE',
                     'Database',
                     'Web server',
                     'VMware',
                     'Firewall',
                     'File Transfer Protocol',
                     'News Server',
                     'NFS',
                     'CGI',
                     'Solaris',
                     'Oracle VM Server',
                     'RedHat',
                     'Windows',
                     'Proxy',
                     'Web Application Firewall',
                     'Brute Force Attack',
                     'General remote services',
                     'Security Policy',
                     'DNS and BIND',
                     'Mail services',
                     'Ubuntu',
                     'Forensics',
                     'Web Application',
                     'SMB / NETBIOS',
                     'X-Window',
                     'OEL',
                     'Cisco',
                     'AIX',
                     'CentOS',
                     'Local',
                     'Office Application',
                     'Backdoors and trojan horses',
                     'Internet Explorer',
                     'E-Commerce',
                     'SNMP',
                     'Information gathering',
                     'TCP/IP']

QUALYS_VULN_TYPES = [
    'Potential Vulnerability',
    'Confirmed Vulnerability',
    'Information Gathered'
]


class QualysAgentVuln(SmartJsonClass):
    vuln_id = Field(str, 'Vuln ID')
    first_found = Field(datetime.datetime, 'First Found')
    last_found = Field(datetime.datetime, 'Last Found')
    qid = Field(str, 'QID')
    title = Field(str, 'Title')
    category = Field(str, 'Category', enum=QUALYS_CATEGORIES)
    sub_category = ListField(str, 'Sub Category', enum=QUALYS_SUB_CATEGORIES)
    severity = Field(int, 'Severity')
    vendor_reference = ListField(str, 'Vendor Reference')
    qualys_cve_id = ListField(str, 'CVE ID')
    cvss_base = Field(float, 'CVSS Base')
    cvss3_base = Field(float, 'CVSS3 Base')
    cvss_temporal_score = Field(float, 'CVSS Temporal Score')
    cvss3_temporal_score = Field(float, 'CVSS3 Temporal Score')
    cvss_access_vector = Field(float, 'CVSS Access Vector')
    bugtraq_id = ListField(str, 'Bugtraq ID')
    modified = Field(datetime.datetime, 'Modified')
    published = Field(datetime.datetime, 'Published')
    vuln_type = Field(str, 'Vulnerability Type', enum=QUALYS_VULN_TYPES)


class QualysAgentPort(SmartJsonClass):
    port = Field(int, 'Port')
    protocol = Field(str, 'Protocol')
    service_name = Field(str, 'Service Name')


class QualysScansAdapter(ScannerAdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        qualys_agent_vulns = ListField(QualysAgentVuln, 'Vulnerabilities')
        qualys_agnet_ports = ListField(QualysAgentPort, 'Qualys Open Ports')
        qualys_tags = ListField(str, 'Qualys Tags')
        last_vuln_scan = Field(datetime.datetime, 'Last Vuln Scan')
        agent_last_seen = Field(datetime.datetime, 'Agent Last Seen')

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
        return client_config[consts.QUALYS_SCANS_DOMAIN]

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get(consts.QUALYS_SCANS_DOMAIN))
    # pylint: disable=too-many-function-args

    def _connect_client(self, client_config):
        try:
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
                https_proxy=client_config.get('https_proxy')
            )
            with connection:
                pass
            return connection
        except Exception as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config[consts.QUALYS_SCANS_DOMAIN], str(e)
            )
            logger.exception(message)
            raise ClientConnectionException(message)
    # pylint: enable=too-many-function-args

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema QualysScansAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {'name': consts.QUALYS_SCANS_DOMAIN, 'title': 'Qualys Scanner Domain', 'type': 'string'},
                {'name': consts.USERNAME, 'title': 'User Name', 'type': 'string'},
                {'name': consts.PASSWORD, 'title': 'Password', 'type': 'string', 'format': 'password'},
                {'name': consts.VERIFY_SSL, 'title': 'Verify SSL', 'type': 'bool'},
                {'name': 'https_proxy', 'title': 'HTTPS Proxy', 'type': 'string'}
            ],
            'required': [consts.QUALYS_SCANS_DOMAIN, consts.USERNAME, consts.PASSWORD, consts.VERIFY_SSL],
            'type': 'array',
        }

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

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_agent_device(device_raw, self.__qualys_tags_white_list)
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
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')
            hostname = (device_raw.get('netbiosName') or device_raw.get('dnsHostName')) or device_raw.get('name')
            if device_raw.get('netbiosName') and device_raw.get('dnsHostName') and \
                    device_raw.get('dnsHostName').split('.')[0].lower() ==\
                    device_raw.get('netbiosName').split('.')[0].lower():
                hostname = device_raw.get('dnsHostName')
            if hostname != device_raw.get('address'):
                device.hostname = hostname
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
                for asset_interface in (device_raw.get('networkInterface') or {}).get('list') or []:
                    try:
                        mac = (asset_interface.get('HostAssetInterface') or {}).get('macAddress')
                        if not mac:
                            mac = None
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
                    try:
                        if (tag_raw.get('TagSimple') or {}).get('name') in qualys_tags_white_list:
                            tags_ok = True
                        device.qualys_tags.append((tag_raw.get('TagSimple') or {}).get('name'))
                    except Exception:
                        logger.exception(f'Problem with tag {tag_raw}')
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
                for vuln_raw in (device_raw.get('vuln') or {}).get('list') or []:
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
                            qid=qid_info_entry.get('QID'),
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

            device.adapter_properties = [AdapterProperty.Vulnerability_Assessment.name]
            device.set_raw(device_raw)
            if not tags_ok:
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
                    'title': 'Request Timeout',
                    'type': 'integer'
                },
                {
                    'name': 'async_chunk_size',
                    'title': 'Chunk Size',
                    'type': 'integer',
                },
                {
                    'name': 'devices_per_page',
                    'title': 'Devices Per Page',
                    'type': 'integer',
                },
                {
                    'name': 'retry_sleep_time',
                    'title': 'Intervals between Retries in Seconds',
                    'type': 'integer',
                },
                {
                    'name': 'max_retries',
                    'title': 'Number of Retries',
                    'type': 'integer',
                },
                {
                    'name': 'qualys_tags_white_list',
                    'type': 'string',
                    'title': 'Qualys Tags Whitelist'
                }
            ],
            'required': [
                'request_timeout',
                'async_chunk_size',
            ],
            'pretty_name': 'Qualys Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'request_timeout': 200,
            'async_chunk_size': 50,
            'retry_sleep_time': consts.RETRY_SLEEP_TIME,
            'max_retries': consts.MAX_RETRIES,
            'devices_per_page': consts.DEVICES_PER_PAGE,
            'qualys_tags_white_list': None
        }

    def _on_config_update(self, config):
        self.__request_timeout = config['request_timeout']
        self.__async_chunk_size = config['async_chunk_size']
        self.__max_retries = config.get('max_retries', consts.MAX_RETRIES)
        self.__retry_sleep_time = config.get('max_retries', consts.RETRY_SLEEP_TIME)
        self.__devices_per_page = config.get('devices_per_page', consts.DEVICES_PER_PAGE)
        self.__qualys_tags_white_list = config.get('qualys_tags_white_list').split(',') \
            if config.get('qualys_tags_white_list') else None

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network, AdapterProperty.Vulnerability_Assessment]
