import ipaddress
import logging
from datetime import datetime

from axonius.adapter_base import AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.mixins.configurable import Configurable
from axonius.plugin_base import add_rule, return_error
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.utils.files import get_local_config_file
from axonius.clients.tenable_sc.connection import \
    TenableSecurityScannerConnection

logger = logging.getLogger(f'axonius.{__name__}')


class TenableSecurityCenterAdapter(ScannerAdapterBase, Configurable):
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
                conn = self.get_connection(self._get_client_config_by_client_id(client_id))
                with conn:
                    result_status = conn.add_ips_to_asset(tenable_sc_dict)
                    success = success or result_status
                    if success is True:
                        return '', 200
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
                conn = self.get_connection(self._get_client_config_by_client_id(client_id))
                with conn:
                    result_status = conn.create_asset_with_ips(tenable_sc_dict)
                    success = success or result_status
                    if success is True:
                        return '', 200
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
                                                   fetch_vulnerabilities=self.__fetch_vulnerabilities)

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

        # Parse all raw data
        device.figure_os(raw_device_data.get('os'))
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

        hostname = raw_device_data.get('dnsName') or hostname_by_netbios
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
                device.last_seen = last_scan_date    # The best we have
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

        for vulnerability in raw_device_data.get('vulnerabilities') or []:
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
        device.set_raw(raw_device_data)
        return device

    def _parse_raw_data(self, devices_raw_data):
        for raw_device_data in iter(devices_raw_data):
            try:
                device = self.create_device(raw_device_data)
                if device:
                    yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {raw_device_data}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network, AdapterProperty.Vulnerability_Assessment]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            "items": [
                {
                    'name': 'drop_only_ip_devices',
                    'title': 'Drop Devices With Only IP',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_top_n_installed_software',
                    'title': 'Fetch Top N Installed Software',
                    'type': 'integer',
                },
                {
                    'name': 'fetch_software_per_device',
                    'title': 'Fetch Software Per Device',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_vulnerabilities',
                    'title': 'Fetch Vulnerabilities',
                    'type': 'bool'
                }
            ],
            "required": [
                'drop_only_ip_devices',
                'fetch_software_per_device',
                'fetch_vulnerabilities'
            ],
            "pretty_name": "Tenable.sc Configuration",
            "type": "array"
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'drop_only_ip_devices': False,
            'fetch_top_n_installed_software': 0,
            'fetch_software_per_device': False,
            'fetch_vulnerabilities': False
        }

    def _on_config_update(self, config):
        self.__drop_only_ip_devices = config['drop_only_ip_devices']
        self.__fetch_top_n_installed_software = config.get('fetch_top_n_installed_software') or 0
        self.__fetch_software_per_device = config['fetch_software_per_device']
        self.__fetch_vulnerabilities = config['fetch_vulnerabilities']
