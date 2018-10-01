import ipaddress
import logging
from datetime import datetime

from axonius.adapter_base import AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.utils.files import get_local_config_file
from tenable_security_center_adapter.connection import \
    TenableSecurityScannerConnection

logger = logging.getLogger(f'axonius.{__name__}')


class TenableSecurityCenterAdapter(ScannerAdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        repository_id = Field(str, 'Repository ID')
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

    def _get_client_id(self, client_config):
        return client_config['url']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('url'))

    def _connect_client(self, client_config):
        try:
            verify_ssl = False
            if 'verify_ssl' in client_config:
                verify_ssl = bool(client_config['verify_ssl'])
            connection = TenableSecurityScannerConnection(
                domain=client_config['url'],
                username=client_config['username'], password=client_config['password'],
                url_base_prefix='/rest/', verify_ssl=verify_ssl,
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as e:
            logger.error('Failed to connect to client {0}'.format(
                self._get_client_id(client_config)))
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, client_data):
        with client_data:
            yield from client_data.get_device_list()

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
                    'title': 'Username',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
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
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def create_device(self, raw_device_data):
        device = self._new_device_adapter()

        uuid = raw_device_data.get('uuid')
        if uuid:
            device.id = uuid

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

        hostname = raw_device_data.get('dnsName', hostname_by_netbios)
        device.hostname = hostname
        uuid = raw_device_data.get('uuid')
        if uuid:
            device.id = uuid + (hostname or '')
        last_scan = raw_device_data.get('lastScan')
        if last_scan is not None and last_scan != '':
            try:
                last_scan_date = datetime.fromtimestamp(int(last_scan))
                device.last_seen = last_scan_date    # The best we have
                device.last_scan = last_scan_date
            except Exception:
                logger.error(f'Couldn\'t parse last scan {last_scan}')

        device.repository_id = raw_device_data.get('repositoryID')
        device.score = raw_device_data.get('score')
        device.total = raw_device_data.get('total')
        device.severity_info = raw_device_data.get('severityInfo')
        device.severity_low = raw_device_data.get('severityLow')
        device.severity_medium = raw_device_data.get('severityMedium')
        device.severity_high = raw_device_data.get('severityHigh')
        device.severity_critical = raw_device_data.get('severityCritical')
        device.policy_name = raw_device_data.get('policyName')
        device.mcafee_guid = raw_device_data.get('mcafeeGUID')

        last_auth_run = raw_device_data.get('lastAuthRun')
        if last_auth_run is not None and last_auth_run != '':
            try:
                device.last_auth_run = datetime.fromtimestamp(int(last_auth_run))
            except Exception:
                logger.error(f'Couldn\'t parse last auth run {last_auth_run}')

        last_unauth_run = raw_device_data.get('lastUnauthRun')
        if last_unauth_run is not None and last_unauth_run != '':
            try:
                device.last_auth_run = datetime.fromtimestamp(int(last_unauth_run))
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

        device.set_raw(raw_device_data)
        return device

    def _parse_raw_data(self, devices_raw_data):
        for raw_device_data in iter(devices_raw_data):
            try:
                device = self.create_device(raw_device_data)
                yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {raw_device_data}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network, AdapterProperty.Vulnerability_Assessment]
