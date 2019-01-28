import logging
import datetime

from axonius.adapter_base import AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_date
from qualys_scans_adapter import consts
from qualys_scans_adapter.connection import QualysScansConnection

logger = logging.getLogger(f'axonius.{__name__}')


class QualysVulnerability(SmartJsonClass):
    severity = Field(str, 'Severity')
    results = Field(str, 'Results')


class QualysAgentVuln(SmartJsonClass):
    qid = Field(str, 'QID')
    vuln_id = Field(str, 'Vuln ID')
    first_found = Field(datetime.datetime, 'First Found')
    last_found = Field(datetime.datetime, 'Last Found')


class QualysAgentPort(SmartJsonClass):
    port = Field(int, 'Port')
    protocol = Field(str, 'Protocol')
    service_name = Field(str, 'Service Name')


class QualysScansAdapter(ScannerAdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        qualys_agent_vulns = ListField(QualysAgentVuln, 'Vulnerabilities')
        qualys_agnet_ports = ListField(QualysAgentPort, 'Open Ports')
        agent_version = Field(str, 'Qualys agent version')
        agent_status = Field(str, 'Agent Status')
        qualys_tags = ListField(str, 'Qualys Tags')

        def add_qualys_vuln(self, **kwargs):
            self.qualys_agent_vulns.append(QualysAgentVuln(**kwargs))

        def add_qualys_port(self, **kwargs):
            self.qualys_agnet_ports.append(QualysAgentPort(**kwargs))

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config[consts.QUALYS_SCANS_DOMAIN]

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get(consts.QUALYS_SCANS_DOMAIN))

    def _connect_client(self, client_config):
        try:
            connection = QualysScansConnection(domain=client_config[consts.QUALYS_SCANS_DOMAIN],
                                               username=client_config[consts.USERNAME],
                                               password=client_config[consts.PASSWORD],
                                               verify_ssl=client_config.get('verify_ssl') or False)
            with connection:
                pass
            return connection
        except Exception as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config[consts.QUALYS_SCANS_DOMAIN], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        with client_data:
            yield from client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema QualysScansAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': consts.QUALYS_SCANS_DOMAIN,
                    'title': 'Qualys Scanner Domain',
                    'type': 'string'
                },
                {
                    'name': consts.USERNAME,
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': consts.PASSWORD,
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': consts.VERIFY_SSL,
                    'title': 'Verify SSL',
                    'type': 'bool'
                }
            ],
            'required': [
                consts.QUALYS_SCANS_DOMAIN,
                consts.USERNAME,
                consts.PASSWORD,
                consts.VERIFY_SSL
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, device_type in devices_raw_data:
            device = None
            if device_type == consts.SCAN_DEVICE:
                device = self._create_scan_device(device_raw)
            if device_type == consts.AGENT_DEVICE:
                device = self._create_agent_device(device_raw)
            if device:
                yield device

    def _create_scan_device(self, device_raw):
        try:
            last_seen = device_raw.get('LAST_VM_SCANNED_DATE', device_raw.get('LAST_VULN_SCAN_DATETIME'))
            if last_seen is None:
                # No data on the last timestamp of the device. Not inserting this device.
                logger.warning(f'Device scan with no scan time {device_raw}')
                return None

            # Parsing the timestamp.
            last_seen = parse_date(last_seen)
        except Exception:
            logger.exception(f'An Exception was raised while getting and parsing '
                             f'the last_seen field for device {device_raw}')
            return None
        try:
            device = self._new_device_adapter()
            device.hostname = device_raw.get('DNS') or device_raw.get('NETBIOS')
            device.figure_os(device_raw.get('OS'))
            device.last_seen = last_seen
            try:
                if 'IP' in device_raw:
                    device.add_nic(None, [device_raw['IP']])
            except Exception:
                logger.exception(f'Problem adding nic to {device_raw}')
            device.id = device_raw.get('ID')
            try:
                vulns_list = (device_raw.get('DETECTION_LIST') or {}).get('DETECTION') or []
                if isinstance(vulns_list, dict):
                    vulns_list = [vulns_list]
                for vuln in vulns_list:
                    severity = vuln.get('SEVERITY') or ''
                    results = vuln.get('RESULTS') or ''
                    if severity or results:
                        device.severity_results.append(QualysVulnerability(severity=severity, results=results))

            except Exception:
                logger.exception(f'Problem adding scans to {device_raw}')
            device.adapter_properties = [AdapterProperty.Vulnerability_Assessment.name, AdapterProperty.Network.name]
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with device {device_raw}')
            return None

    # pylint: disable=R0912,R0915
    def _create_agent_device(self, device_raw):
        try:
            device_raw = device_raw.get('HostAsset')
            device_id = device_raw.get('id')
            if not device_id:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device = self._new_device_adapter()
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')
            device.hostname = device_raw.get('dnsHostName') or device_raw.get('name')
            if device_raw.get('dnsHostName') and device_raw.get('name'):
                device.name = device_raw.get('name')
            try:
                device.figure_os(device_raw.get('os'))
            except Exception:
                logger.exception(f'Problem getting OS from {device_raw}')
            try:
                device.last_seen = parse_date(device_raw.get('lastVulnScan'))
            except Exception:
                logger.exception(f'Problem getting last seen for {device_raw}')
            device.agent_version = (device_raw.get('agentInfo') or {}).get('agentVersion')
            device.physical_location = (device_raw.get('agentInfo') or {}).get('location')
            device.boot_time = parse_date(str(device_raw.get('lastSystemBoot')))
            device.agent_status = (device_raw.get('agentInfo') or {}).get('status')
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
                        device.qualys_tags.append(tag_raw.get('TagSimple') or {}).get('name')
                    except Exception:
                        logger.exception(f'Problem with tag {tag_raw}')
            except Exception:
                logger.exception(f'Problem with adding tags to Qualys agent {device_raw}')

            try:
                for user_raw in (device_raw.get('account') or {}).get('list') or []:
                    try:
                        device.last_used_users.append(user_raw.get('HostAssetAccount') or {}).get('username')
                    except Exception:
                        logger.exception(f'Problem with user {user_raw}')
            except Exception:
                logger.exception(f'Problem with adding users to Qualys agent {device_raw}')

            try:
                for software_raw in (device_raw.get('software') or {}).get('list') or []:
                    try:
                        device.add_installed_software(name=(software_raw.get('HostAssetSoftware')
                                                            or {}).get('name'),
                                                      version=(software_raw.get('HostAssetSoftware')
                                                               or {}).get('version'))
                    except Exception:
                        logger.exception(f'Problem with software {software_raw}')
            except Exception:
                logger.exception(f'Problem with adding software to Qualys agent {device_raw}')
            try:
                for vuln_raw in (device_raw.get('vuln') or {}).get('list') or []:
                    try:
                        device.add_qualys_vuln(vuln_id=(vuln_raw.get('HostAssetVuln') or {}).get('hostInstanceVulnId'),
                                               last_found=parse_date((vuln_raw.get('HostAssetVuln') or
                                                                      {}).get('lastFound')),
                                               qid=(vuln_raw.get('HostAssetVuln') or {}).get('qid'),
                                               first_found=parse_date((vuln_raw.get('HostAssetVuln') or
                                                                       {}).get('firstFound')))
                    except Exception:
                        logger.exception(f'Problem with vuln {vuln_raw}')
            except Exception:
                logger.exception(f'Problem with adding software to Qualys agent {device_raw}')

            try:
                for port_raw in (device_raw.get('openPort') or {}).get('list') or []:
                    try:
                        device.add_qualys_port(port=(port_raw.get('HostAssetOpenPort') or {}).get('port'),
                                               protocol=(port_raw.get('HostAssetOpenPort') or {}).get('protocol'),
                                               service_name=(port_raw.get('HostAssetOpenPort') or
                                                             {}).get('serviceName'),
                                               )
                    except Exception:
                        logger.exception(f'Problem with port {port_raw}')
            except Exception:
                logger.exception(f'Problem with adding software to Qualys agent {device_raw}')

            device.adapter_properties = [AdapterProperty.Vulnerability_Assessment.name]
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with device {device_raw}')
            return None

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network, AdapterProperty.Vulnerability_Assessment]
