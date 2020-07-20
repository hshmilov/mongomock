import ipaddress
import logging
import re
from datetime import datetime

from axonius.adapter_base import AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter, TenableVulnerability, NessusInstance
from axonius.fields import Field
from axonius.mixins.configurable import Configurable
from axonius.plugin_base import add_rule, return_error
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.clients.tenable_sc.connection import \
    TenableSecurityScannerConnection
from axonius.clients.tenable_sc.consts import OS_IDENTIFICATION_PLUGIN_ID

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class TenableSecurityCenterAdapter(ScannerAdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        repository_name = Field(str, 'Repository Name')
        score = Field(int, 'Score')
        total = Field(int, 'Total Vulnerabilities')
        severity_info = Field(int, 'Info Vulnerabilities Count')
        severity_low = Field(int, 'Low Vulnerabilities Count')
        severity_medium = Field(int, 'Medium Vulnerabilities Count')
        severity_high = Field(int, 'High Vulnerabilities Count')
        severity_critical = Field(int, 'Critical Vulnerabilities Count')
        policy_name = Field(str, 'Policy Name')
        mcafee_guid = Field(str, 'Mcafee GUID')
        last_auth_run = Field(datetime, 'Last Auth Run')
        last_unauth_run = Field(datetime, 'Last Unauth Run')
        has_passive = Field(bool, 'Has Passive')
        has_compliance = Field(bool, 'Has Compliance')
        last_scan = Field(datetime, 'Last Scan')

        def add_tenable_vuln(self, **kwargs):
            self.plugin_and_severities.append(TenableVulnerability(**kwargs))

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    @add_rule('add_ips_to_asset', methods=['POST'])
    def add_ips_to_asset(self):
        if self.get_method() != 'POST':
            return return_error('Method not supported', 405)
        tenable_sc_dict = self.get_request_data_as_object()
        success = False
        try:
            for client_id in self._clients:
                try:
                    conn = self.get_connection(self._get_client_config_by_client_id(client_id))
                    with conn:
                        result_status = conn.add_ips_to_asset(tenable_sc_dict)
                        success = success or result_status
                        if success is True:
                            return '', 200
                except Exception:
                    logger.exception(f'Could not connect to {client_id}')
        except Exception as e:
            logger.exception('Got exception while adding to asset')
            return str(e), 400
        return 'Failure', 400

    @add_rule('create_asset_with_ips', methods=['POST'])
    def create_asset_with_ips(self):
        if self.get_method() != 'POST':
            return return_error('Method not supported', 405)
        tenable_sc_dict = self.get_request_data_as_object()
        success = False
        try:
            for client_id in self._clients:
                try:
                    conn = self.get_connection(self._get_client_config_by_client_id(client_id))
                    with conn:
                        result_status = conn.create_asset_with_ips(tenable_sc_dict)
                        success = success or result_status
                        if success is True:
                            return '', 200
                except Exception:
                    logger.exception(f'Could not connect to {client_id}')
        except Exception as e:
            logger.exception(f'Got exception while creating an asset')
            return str(e), 400
        return 'Failure', 400

    def _get_client_id(self, client_config):
        return client_config['url']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('url'))

    @staticmethod
    def get_connection(client_config):
        verify_ssl = False
        if 'verify_ssl' in client_config:
            verify_ssl = bool(client_config['verify_ssl'])
        connection = TenableSecurityScannerConnection(
            domain=client_config['url'],
            username=client_config.get('username'),
            password=client_config.get('password'),
            token=client_config.get('token'),
            verify_ssl=verify_ssl)
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except Exception as e:
            logger.error('Failed to connect to client {0}'.format(
                self._get_client_id(client_config)))
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, client_data):
        with client_data:
            yield from client_data.get_device_list(drop_only_ip_devices=self.__drop_only_ip_devices,
                                                   top_n_software=self.__fetch_top_n_installed_software,
                                                   per_device_software=self.__fetch_software_per_device,
                                                   fetch_vulnerabilities=self.__fetch_vulnerabilities,
                                                   info_vulns_plugin_ids=self.__info_vulns_plugin_ids)

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': 'url',
                    'title': 'URL',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'token',
                    'title': 'API Token',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                }
            ],
            'required': [
                'url',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements
    @staticmethod
    def _get_nessus_instance(device_raw: str):
        nessus_instance = NessusInstance()

        try:
            nessus_instance.version = re.search('Nessus version : (.*)', device_raw).group(1)
        except Exception:
            logger.debug(f'Failed parsing Nessus version {device_raw}')
        try:
            nessus_instance.plugin_feed_version = re.search('Plugin feed version : (.*)', device_raw).group(1)
        except Exception:
            logger.debug(f'Failed parsing Plugin feed version {device_raw}')
        try:
            nessus_instance.scanner_edition_used = re.search('Scanner edition used : (.*)', device_raw).group(1)
        except Exception:
            logger.debug(f'Failed parsing Scanner edition used {device_raw}')
        try:
            nessus_instance.scan_type = re.search('Scan type : (.*)', device_raw).group(1)
        except Exception:
            logger.debug(f'Failed parsing Scan type {device_raw}')
        try:
            nessus_instance.scan_policy_used = re.search('Scan policy used : (.*)', device_raw).group(1)
        except Exception:
            logger.debug(f'Failed parsing Scan policy used {device_raw}')
        try:
            nessus_instance.scanner_ip = re.search('Scanner IP : (.*)', device_raw).group(1)
        except Exception:
            logger.debug(f'Failed parsing Scanner IP {device_raw}')
        try:
            port_scanner_re = r'Port scanner\(s\) : (.*)'
            nessus_instance.port_scanner = re.search(port_scanner_re, device_raw).group(1)
        except Exception:
            logger.debug(f'Failed parsing Port scanners {device_raw}')
        try:
            nessus_instance.port_range = re.search('Port range : (.*)', device_raw).group(1)
        except Exception:
            logger.debug(f'Failed parsing Port range {device_raw}')
        try:
            nessus_instance.thorough_tests = re.search('Thorough tests : (.*)', device_raw).group(1) == 'yes'
        except Exception:
            logger.debug(f'Failed parsing Thorough tests {device_raw}')
        try:
            nessus_instance.experimental_tests = re.search('Experimental tests : (.*)', device_raw).group(1) == 'yes'
        except Exception:
            logger.debug(f'Failed parsing Experimental tests {device_raw}')
        try:
            nessus_instance.paranoia_level = int(re.search('Paranoia level : (.*)', device_raw).group(1))
        except Exception:
            logger.debug(f'Failed parsing Paranoia level {device_raw}')
        try:
            nessus_instance.report_verbosity = int(re.search('Report verbosity : (.*)', device_raw).group(1))
        except Exception:
            logger.debug(f'Failed parsing Report verbosity {device_raw}')
        try:
            nessus_instance.safe_check = re.search('Safe checks : (.*)', device_raw).group(1) == 'yes'
        except Exception:
            logger.debug(f'Failed parsing Safe check {device_raw}')
        try:
            nessus_instance.credentialed_check = re.search('Credentialed checks : (.*)', device_raw).group(1)
        except Exception:
            logger.debug(f'Failed parsing Credentialed checks {device_raw}')
        try:
            nessus_instance.patch_management_checks = re.search('Patch management checks : (.*)', device_raw).group(1)
        except Exception:
            logger.debug(f'Failed parsing Patch management checks {device_raw}')
        try:
            nessus_instance.cgi_scanning = re.search('CGI scanning : (.*)', device_raw).group(1)
        except Exception:
            logger.debug(f'Failed parsing CGI scanning {device_raw}')
        try:
            nessus_instance.max_hosts = int(re.search('Max hosts : (.*)', device_raw).group(1))
        except Exception:
            logger.debug(f'Failed parsing Max hosts {device_raw}')
        try:
            nessus_instance.max_checks = int(re.search('Max checks : (.*)', device_raw).group(1))
        except Exception:
            logger.debug(f'Failed parsing Max checks {device_raw}')
        try:
            nessus_instance.receive_timeout = int(re.search('Recv timeout : (.*)', device_raw).group(1))
        except Exception:
            logger.debug(f'Failed parsing Recv timeout {device_raw}')
        try:
            nessus_instance.scan_start_date = parse_date(re.search('Scan Start Date : (.*)', device_raw).group(1))
        except Exception:
            logger.debug(f'Failed parsing Scan Start Date {device_raw}')
        try:
            nessus_instance.scan_duration = int(re.search('Scan duration : (.*)', device_raw).group(1))
        except Exception:
            logger.debug(f'Failed parsing Scan duration {device_raw}')

        return nessus_instance

    # pylint: disable=too-many-locals, too-many-branches, too-many-statements
    def create_device(self, raw_device_data):
        device = self._new_device_adapter()
        last_seen = None

        uuid = raw_device_data.get('uuid')
        if uuid:
            device.id = uuid
            device.uuid = uuid
        elif raw_device_data.get('biosGUID'):
            device.id = raw_device_data.get('biosGUID')
            device.uuid = raw_device_data.get('biosGUID')

        ip_list_raw = raw_device_data.get('ip', [])
        if isinstance(ip_list_raw, str):
            # maybe we have a couple of ip's. we don't know since we don't have it in the api docs.
            ip_list_raw = ip_list_raw.split(',')

        ips = []
        try:
            for ip in ip_list_raw:
                try:
                    assert ipaddress.ip_address(ip) is not None
                    # If we got by now (and didn't throw an exception) that's a valid ip address.
                    ips.append(ip)
                except Exception:
                    print('Got an invalid ip address {ip}, moving on')
        except Exception:
            logger.warning(f'Got an invalid ip address list: {ip_list_raw}, not inserting ips')

        for software in raw_device_data.get('software') or []:
            try:
                device.add_installed_software(name=software)
            except Exception as e:
                logger.exception(f'Failed to add installed software {software}')
        device.add_nic(mac=raw_device_data.get('macAddress'), ips=ips)

        netbios_name = raw_device_data.get('netbiosName')
        try:
            if netbios_name is not None and '\\' in netbios_name:
                hostname_by_netbios = netbios_name.split('\\')[1]
            else:
                hostname_by_netbios = netbios_name
        except Exception:
            hostname_by_netbios = None
            logger.warning(f'Couldn\'t parse hostname from netbios name {netbios_name}')

        hostname = hostname_by_netbios or raw_device_data.get('dnsName')
        if not raw_device_data.get('macAddress') and not hostname and self.__drop_only_ip_devices:
            return None
        device.hostname = hostname
        uuid = raw_device_data.get('uuid')
        if uuid:
            device.id = uuid + (hostname or '')

        last_scan = raw_device_data.get('lastScan')
        if last_scan is not None and last_scan != '':
            try:
                last_scan_date = datetime.fromtimestamp(int(last_scan))
                last_seen = last_scan_date
                device.last_seen = last_scan_date  # The best we have
                device.last_scan = last_scan_date
            except Exception:
                logger.error(f'Couldn\'t parse last scan {last_scan}')
        try:
            device.repository_name = (raw_device_data.get('repository') or {}).get('name')
        except Exception:
            logger.exception('Problem getting repository')
        device.score = raw_device_data.get('score')
        device.total = raw_device_data.get('total')
        device.severity_info = raw_device_data.get('severityInfo')
        device.severity_low = raw_device_data.get('severityLow')
        device.severity_medium = raw_device_data.get('severityMedium')
        device.severity_high = raw_device_data.get('severityHigh')
        device.severity_critical = raw_device_data.get('severityCritical')
        device.policy_name = raw_device_data.get('policyName')
        device.mcafee_guid = raw_device_data.get('mcafeeGUID')

        linux_kernel_version = None
        os_string = raw_device_data.get('os') or raw_device_data.get('osCPE') or ''
        for vulnerability in raw_device_data.get('vulnerabilities') or []:
            try:
                plugin_name = vulnerability.get('pluginName')
                cpe = vulnerability.get('cpe') or None
                cve = vulnerability.get('cve') or None
                cvss_base_score = vulnerability.get('baseScore') or None
                exploit_value = (vulnerability.get('exploitAvailable') or '').lower()
                exploit_available = None
                if exploit_value:
                    exploit_available = exploit_value == 'yes'
                synopsis = vulnerability.get('synopsis') or None
                see_also = vulnerability.get('seeAlso') or None
                severity = (vulnerability.get('severity') or {}).get('name') or None
                plugin_text = vulnerability.get('pluginText') or None
                first_seen = parse_date(vulnerability.get('firstSeen'))
                last_seen = parse_date(vulnerability.get('lastSeen'))
                last_mitigated = parse_date(vulnerability.get('lastMitigated'))
                nessus_instance = None
                if plugin_text and 'Nessus version' in plugin_text:
                    nessus_instance = self._get_nessus_instance(vulnerability.get('pluginText'))

                plugin_id = vulnerability.get('pluginID')

                # Specific Plugin (11936) in vulnerabilities include OS Identification which will help determine OS type
                if plugin_id == OS_IDENTIFICATION_PLUGIN_ID and plugin_text:
                    try:
                        os_identification = re.search('Remote operating system : (.*)', plugin_text).group(1)
                        try:
                            linux_kernel_version = re.search('linux kernel (.*) on', os_identification.lower()).group(1)
                        except Exception:
                            pass
                        os_string += ' ' + os_identification
                    except Exception:
                        logger.debug(
                            f'Failed parsing OS Identification for Plugin {OS_IDENTIFICATION_PLUGIN_ID}: {plugin_text}')

                device.add_tenable_vuln(plugin=plugin_name,
                                        severity=severity,
                                        cpe=cpe,
                                        cve=cve,
                                        cvss_base_score=cvss_base_score,
                                        exploit_available=exploit_available,
                                        synopsis=synopsis,
                                        see_also=see_also,
                                        nessus_instance=nessus_instance,
                                        plugin_text=plugin_text,
                                        plugin_id=plugin_id,
                                        first_seen=first_seen,
                                        last_seen=last_seen,
                                        last_mitigated=last_mitigated)
            except Exception:
                logger.exception(f'Problem adding tenable vuln')

            try:
                if vulnerability.get('cve'):
                    cves_list = list(filter(None, (vulnerability.get('cve') or '').split(',')))
                    for cve in cves_list:
                        try:
                            device.add_vulnerable_software(cve_id=cve)
                        except Exception:
                            logger.exception(f'Problem adding CVE {cve}')
            except Exception:
                logger.exception(f'Problem adding vulnerability {vulnerability}')

        device.figure_os(os_string)
        if linux_kernel_version:
            device.os.kernel_version = linux_kernel_version

        last_auth_run = raw_device_data.get('lastAuthRun')
        if last_auth_run is not None and last_auth_run != '':
            try:
                device.last_auth_run = datetime.fromtimestamp(int(last_auth_run))
                if not last_seen or last_seen < device.last_auth_run:
                    last_seen = device.last_auth_run
                    device.last_seen = last_seen
            except Exception:
                logger.error(f'Couldn\'t parse last auth run {last_auth_run}')

        last_unauth_run = raw_device_data.get('lastUnauthRun')
        if last_unauth_run:
            try:
                device.last_unauth_run = datetime.fromtimestamp(int(last_unauth_run))
                if not last_seen or last_seen < device.last_unauth_run:
                    last_seen = device.last_unauth_run
                    device.last_seen = last_seen
            except Exception:
                logger.error(f'Couldn\'t parse last unauth run {last_unauth_run}')
        if last_unauth_run and not last_auth_run and self.__drop_only_unauth_scans:
            return None

        has_passive = raw_device_data.get('hasPassive')
        if has_passive is not None and has_passive != '':
            if has_passive.lower() == 'yes':
                device.has_passive = True
            elif has_passive.lower() == 'no':
                device.has_passive = False
            else:
                logger.error(f'hasPassive should be yes/no but its {has_passive}')

        has_compliance = raw_device_data.get('hasCompliance')
        if has_compliance is not None and has_compliance != '':
            if has_compliance.lower() == 'yes':
                device.has_compliance = True
            elif has_compliance.lower() == 'no':
                device.has_compliance = False
            else:
                logger.error(f'hasCompliance should be yes/no but its {has_compliance}')
        try:
            test = device.id
        except Exception:
            device.id = (hostname or '') + '_' + (raw_device_data.get('macAddress') or '') + '_' + (str(ips))

        device.id = device.id + '_' + ((raw_device_data.get('repository') or {}).get('name') or '')
        device.set_raw(raw_device_data)
        return device

    def _parse_raw_data(self, devices_raw_data):
        for raw_device_data in iter(devices_raw_data):
            try:
                device = self.create_device(raw_device_data)
                if device:
                    yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network, AdapterProperty.Vulnerability_Assessment]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'drop_only_ip_devices',
                    'title': 'Do not fetch devices with no MAC address and no hostname',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_top_n_installed_software',
                    'title': 'Fetch top N installed software',
                    'type': 'integer',
                },
                {
                    'name': 'fetch_software_per_device',
                    'title': 'Fetch installed software per device',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_vulnerabilities',
                    'title': 'Fetch vulnerabilities',
                    'type': 'bool'
                },
                {
                    'name': 'drop_only_unauth_scans',
                    'title': 'Do not fetch devices with unauthenticated scans only',
                    'type': 'bool'
                },
                {
                    'name': 'info_vulns_plugin_ids',
                    'title': 'Fetch info level vulnerabilities only for listed plugin IDs',
                    'type': 'string',
                }
            ],
            'required': [
                'drop_only_ip_devices',
                'fetch_software_per_device',
                'fetch_vulnerabilities',
                'drop_only_unauth_scans'
            ],
            'pretty_name': 'Tenable.sc Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'drop_only_ip_devices': False,
            'fetch_top_n_installed_software': 0,
            'fetch_software_per_device': False,
            'fetch_vulnerabilities': False,
            'drop_only_unauth_scans': False,
            'info_vulns_plugin_ids': '',
        }

    @staticmethod
    def _parse_info_vulns_plugin_ids_config(plugin_ids: str):
        raw_plugin_ids = (plugin_ids or '').split(',')
        plugin_ids = [OS_IDENTIFICATION_PLUGIN_ID]
        for plugin_id in raw_plugin_ids:
            if plugin_id.strip():
                plugin_ids.append(plugin_id.strip())
        return plugin_ids

    def _on_config_update(self, config):
        self.__drop_only_ip_devices = config['drop_only_ip_devices']
        # pylint: disable=invalid-name
        self.__fetch_top_n_installed_software = config.get('fetch_top_n_installed_software') or 0
        self.__fetch_software_per_device = config['fetch_software_per_device']
        self.__fetch_vulnerabilities = config['fetch_vulnerabilities']
        self.__drop_only_unauth_scans = config['drop_only_unauth_scans']
        self.__info_vulns_plugin_ids = self._parse_info_vulns_plugin_ids_config(config.get('info_vulns_plugin_ids'))

    def outside_reason_to_live(self) -> bool:
        """
        This adapter might be called from outside, let it live
        """
        return True
