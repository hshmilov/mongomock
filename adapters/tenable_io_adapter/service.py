# pylint: disable=too-many-instance-attributes,too-many-locals,too-many-nested-blocks,
# pylint: disable=too-many-branches,too-many-statements,too-many-nested-blocks
import datetime
import logging

from axonius.adapter_base import AdapterProperty
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.utils.files import get_local_config_file
from axonius.fields import Field, ListField
from axonius.devices.device_adapter import TenableSource, TenableVulnerability, DeviceAdapterOS
from axonius.plugin_base import add_rule, return_error
from axonius.clients.rest.exception import RESTException
from axonius.utils.datetime import parse_date
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.clients.rest.connection import RESTConnection
from axonius.mixins.configurable import Configurable
from axonius.smart_json_class import SmartJsonClass
from axonius.clients.tenable_io.connection import TenableIoConnection
from axonius.clients.tenable_io.consts import AGENT_TYPE, ASSET_TYPE
from tenable_io_adapter.client_id import get_client_id


logger = logging.getLogger(f'axonius.{__name__}')


class ScanData(SmartJsonClass):
    completed_at = Field(datetime.datetime, 'Completed At')
    schedule_uuid = Field(str, 'Schedule UUID')
    started_at = Field(datetime.datetime, 'Started At')
    uuid = Field(str, 'UUID')
    scan_id = Field(str, 'Scan ID')


class TenableIoAdapter(ScannerAdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        has_agent = Field(bool, 'Has Agent')
        status = Field(str, 'Status')
        risk_and_name_list = ListField(str, 'CSV - Vulnerability Details')
        tenable_sources = ListField(TenableSource, 'Tenable Source')
        last_connect = Field(datetime.datetime, 'Last Connect')
        last_scanned = Field(datetime.datetime, 'Last Scanned')
        linked_on = Field(datetime.datetime, 'Linked On')
        last_scan_time = Field(datetime.datetime, 'Last Scan Time')
        asset_uuid = Field(str, 'Asset UUID')
        agent_uuid = Field(str, 'Agent UUID')
        risk_factor = Field(str, 'Risk Factor')
        scans_data = ListField(ScanData, 'Scans Data')
        aws_account_id = Field(str, 'AWS Account ID')
        aws_instance_id = Field(str, 'AWS Instance ID')

        def add_tenable_vuln(self, **kwargs):
            self.plugin_and_severities.append(TenableVulnerability(**kwargs))

        def add_tenable_source(self, **kwargs):
            self.tenable_sources.append(TenableSource(**kwargs))

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @add_rule('create_asset', methods=['POST'])
    def create_asset(self):
        if self.get_method() != 'POST':
            return return_error('Method not supported', 405)
        tenable_io_dict = self.get_request_data_as_object()
        success = False
        try:
            for client_id in self._clients:
                try:
                    conn = self.get_connection(self._get_client_config_by_client_id(client_id))
                    with conn:
                        result_status = conn.create_asset(tenable_io_dict)
                        success = success or result_status
                        if success is True:
                            return '', 200
                except Exception:
                    logger.exception(f'Could not connect to {client_id}')
        except Exception as e:
            logger.exception('Got exception while adding to taget group')
            return str(e), 400
        return 'Failure', 400

    @add_rule('tag_assets', methods=['POST'])
    def tag_assets(self):
        if self.get_method() != 'POST':
            return return_error('Method not supported', 405)
        tenable_io_dict = self.get_request_data_as_object()
        success = False
        try:
            for client_id in self._clients:
                try:
                    conn = self.get_connection(self._get_client_config_by_client_id(client_id))
                    with conn:
                        result_status = conn.tag_assets(tenable_io_dict)
                        success = success or result_status
                        if success is True:
                            return '', 200
                except Exception:
                    logger.exception(f'Could not connect to {client_id}')
        except Exception as e:
            logger.exception('Got exception while adding tags')
            return str(e), 400
        return 'Failure', 400

    @add_rule('add_ips_to_scans', methods=['POST'])
    def add_ips_to_scans(self):
        if self.get_method() != 'POST':
            return return_error('Method not supported', 405)
        tenable_io_dict = self.get_request_data_as_object()
        success = False
        try:
            for client_id in self._clients:
                try:
                    conn = self.get_connection(self._get_client_config_by_client_id(client_id))
                    with conn:
                        result_status = conn.add_ips_to_scans(tenable_io_dict)
                        success = success or result_status
                        if success is True:
                            return '', 200
                except Exception:
                    logger.exception(f'Could not connect to {client_id}')
        except Exception as e:
            logger.exception('Got exception while adding to taget group')
            return str(e), 400
        return 'Failure', 400

    @add_rule('add_ips_to_target_group', methods=['POST'])
    def add_ips_to_asset(self):
        if self.get_method() != 'POST':
            return return_error('Method not supported', 405)
        tenable_io_dict = self.get_request_data_as_object()
        success = False
        try:
            for client_id in self._clients:
                try:
                    conn = self.get_connection(self._get_client_config_by_client_id(client_id))
                    with conn:
                        result_status = conn.add_ips_to_target_group(tenable_io_dict)
                        success = success or result_status
                        if success is True:
                            return '', 200
                except Exception:
                    logger.exception(f'Could not connect to {client_id}')
        except Exception as e:
            logger.exception('Got exception while adding to taget group')
            return str(e), 400
        return 'Failure', 400

    @add_rule('create_target_group_with_ips', methods=['POST'])
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
                        result_status = conn.create_target_group_with_ips(tenable_sc_dict)
                        success = success or result_status
                        if success is True:
                            return '', 200
                except Exception:
                    logger.exception(f'Could not connect to {client_id}')
        except Exception as e:
            logger.exception(f'Got exception while creating a target target group')
            return str(e), 400
        return 'Failure', 400

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        return TenableIoConnection(domain=client_config['domain'],
                                   verify_ssl=client_config['verify_ssl'],
                                   access_key=client_config.get('access_key'),
                                   secret_key=client_config.get('secret_key'),
                                   https_proxy=client_config.get('https_proxy'))

    def _connect_client(self, client_config):
        try:
            connection = self.get_connection(client_config)
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    # pylint:disable=arguments-differ
    def _query_devices_by_client(self, client_name, client_data: TenableIoConnection):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            logger.info(f'Getting scans id to uuid')
            uuid_to_id_scans_dict = client_data.get_uuid_to_id_scans_dict()
            logger.info('Getting all assets')
            devices_list = client_data.get_device_list(should_cancel_old_exports_jobs=self.__cancel_old_export_jobs)
            yield devices_list, ASSET_TYPE, client_data, uuid_to_id_scans_dict
            if self.__fetch_agent_data:
                logger.info('Getting all agent')
                for device_raw in client_data.get_agents():
                    yield device_raw, AGENT_TYPE, client_data, uuid_to_id_scans_dict

    def _clients_schema(self):
        """
        The schema TenableIOAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Tenable.io Domain',
                    'type': 'string'
                },
                {
                    'name': 'access_key',
                    'title': 'Access API Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'secret_key',
                    'title': 'Secret API Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }

            ],
            'required': [
                'domain',
                'verify_ssl',
                'access_key',
                'secret_key'
            ],
            'type': 'array'
        }

    def _parse_export_device(self, device_id, device_raw, client_data, uuid_to_id_scans_dict):
        device = self._new_device_adapter()
        device.id = device_id
        device.asset_uuid = device_id
        device.has_agent = bool(device_raw.get('has_agent'))
        device.aws_account_id = device_raw.get('aws_account_id')
        aws_instance_id = device_raw.get('aws_instance_id') or device_raw.get('aws_ec2_instance_id')
        device.aws_instance_id = aws_instance_id
        if aws_instance_id:
            device.cloud_id = aws_instance_id
            device.cloud_provider = 'AWS'
        device.last_seen = parse_date(device_raw.get('last_seen'))
        device.risk_factor = device_raw.get('risk_factor')
        device.agent_uuid = device_raw.get('agent_uuid')
        last_scan_time = parse_date(device_raw.get('last_scan_time'))
        if self.__exclude_no_last_scan and not last_scan_time:
            return None
        device.last_scan_time = last_scan_time
        tags_raw = device_raw.get('tags')
        if not isinstance(tags_raw, list):
            tags_raw = []
        found_key = False
        for tag_raw in tags_raw:
            try:
                if self.__adapter_key_white_list and tag_raw.get('key') in self.__adapter_key_white_list:
                    found_key = True
                device.add_key_value_tag(tag_raw.get('key'), tag_raw.get('value'))
            except Exception:
                logger.exception(f'Problem with tag raw {tag_raw}')
        if self.__adapter_key_white_list and not found_key:
            return None
        ipv4_raw = device_raw.get('ipv4s') or []
        ipv6_raw = device_raw.get('ipv6s') or []
        mac_addresses_raw = device_raw.get('mac_addresses') or []
        try:
            device.add_ips_and_macs(mac_addresses_raw, ipv4_raw + ipv6_raw)
        except Exception:
            logger.exception(f'Failed to add ips and macs')
        try:
            os_list = device_raw.get('operating_systems')
            if len(os_list) > 0:
                device.figure_os(str(os_list[0]))
                if len(os_list) > 1:
                    try:
                        os_type = device.os.type
                        device.os = DeviceAdapterOS(type=os_type)
                    except Exception:
                        pass
        except Exception:
            logger.exception(f'Problem getting OS for {device_raw}')
        fqdns = device_raw.get('fqdns', [])
        hostnames = device_raw.get('hostnames', [])
        netbios = device_raw.get('netbios_names', [])
        if not mac_addresses_raw and not fqdns and not hostnames and not netbios and self.__drop_only_ip_devices:
            return None
        hostname = None
        if len(netbios) > 0 and netbios[0] != '':
            hostname = netbios[0]
            device.hostname = hostname
        elif len(hostnames) > 0 and hostnames[0] != '':
            hostname = hostnames[0]
            device.hostname = hostname
        if len(fqdns) > 0 and fqdns[0] != '':
            if hostname:
                device.name = fqdns[0]
                try:
                    if device.name.split('.')[0].lower() == device.hostname.split('.')[0].lower() \
                            and '.' in device.name:
                        device.hostname = device.name
                except Exception:
                    pass
            else:
                device.hostname = fqdns[0]
        try:
            installed_software = device_raw.get('installed_software')
            if not isinstance(installed_software, list):
                installed_software = []
            for sw_raw in installed_software:
                try:
                    sw_raw = sw_raw.split(':')
                    if len(sw_raw) == 5 and sw_raw[0] == 'cpe' and sw_raw[1] == '/a':
                        device.add_installed_software(vendor=sw_raw[2],
                                                      name=sw_raw[3],
                                                      version=sw_raw[4])
                except Exception:
                    logger.debug(f'Problem with sw {sw_raw}')
        except Exception:
            logger.exception(f'Problem with installed sw')
        plugin_and_severity = []
        vulns_info = device_raw.get('vulns_info', [])
        device.software_cves = []
        found_scan_id = True
        if self.__scan_id_white_list:
            found_scan_id = False
        for vuln_raw in vulns_info:
            try:
                try:
                    port_data = vuln_raw.get('port')
                    if port_data.get('port'):
                        device.add_open_port(port_id=port_data.get('port'),
                                             service_name=port_data.get('service'),
                                             protocol=port_data.get('protocol'))
                except Exception:
                    logger.exception(f'Problem adding port for {vuln_raw}')
                severity = vuln_raw.get('severity', '')
                plugin_name = vuln_raw.get('plugin', {}).get('name')
                plugin_id = vuln_raw.get('plugin', {}).get('id')
                has_patch = vuln_raw.get('plugin', {}).get('has_patch')
                last_fixed = parse_date(vuln_raw.get('last_fixed'))
                first_found = parse_date(vuln_raw.get('first_found'))
                last_found = parse_date(vuln_raw.get('last_found'))
                if not isinstance(has_patch, bool):
                    has_patch = None
                plugin_output = vuln_raw.get('output')
                scan_raw = vuln_raw.get('scan')
                vuln_state = vuln_raw.get('state')
                if vuln_state and vuln_state.upper() not in ['OPEN', 'REOPENED']:
                    continue
                if not isinstance(scan_raw, dict):
                    scan_raw = {}
                try:
                    uuid = scan_raw.get('uuid')
                    scan_id = uuid_to_id_scans_dict.get(uuid)
                    if scan_id and self.__scan_id_white_list and scan_id in self.__scan_id_white_list:
                        found_scan_id = True
                    device.scans_data.append(ScanData(uuid=uuid,
                                                      scan_id=scan_id,
                                                      schedule_uuid=scan_raw.get('schedule_uuid'),
                                                      started_at=parse_date(scan_raw.get('started_at')),
                                                      completed_at=parse_date(scan_raw.get('completed_at'))))
                except Exception:
                    logger.exception(f'Problem with scan raw {scan_raw}')
                plugin_data = []
                cpe = None
                cve = None
                cvss_base_score = None
                exploit_available = None
                synopsis = None
                see_also = None
                if plugin_id:
                    plugin_data = client_data.get_plugin_info(plugin_id)
                    if not plugin_data:
                        plugin_data = []
                try:
                    for attribute_plugin in plugin_data:
                        try:
                            if attribute_plugin.get('attribute_name') == 'cpe':
                                cpe = attribute_plugin.get('attribute_value')
                            elif attribute_plugin.get('attribute_name') == 'cve':
                                cve = attribute_plugin.get('attribute_value')
                            elif attribute_plugin.get('attribute_name') == 'cvss_base_score':
                                cvss_base_score = float(attribute_plugin.get('attribute_value'))
                            elif attribute_plugin.get('attribute_name') == 'exploit_available':
                                exploit_available = attribute_plugin.get('attribute_value').lower() == 'true'
                            elif attribute_plugin.get('attribute_name') == 'synopsis':
                                synopsis = attribute_plugin.get('attribute_value')
                            elif attribute_plugin.get('attribute_name') == 'see_also':
                                see_also = attribute_plugin.get('attribute_value')
                        except Exception:
                            logger.exception(f'Problem with attribute {attribute_plugin}')
                except Exception:
                    logger.exception(f'Problem with plugin data {plugin_data}')
                if f'{plugin_name}__{severity}' not in plugin_and_severity:
                    plugin_and_severity.append(f'{plugin_name}__{severity}')
                    device.add_tenable_vuln(plugin=plugin_name, severity=severity, cpe=cpe, cve=cve,
                                            output=plugin_output, plugin_id=plugin_id, has_patch=has_patch,
                                            cvss_base_score=cvss_base_score, exploit_available=exploit_available,
                                            synopsis=synopsis, see_also=see_also, vuln_state=vuln_state,
                                            last_fixed=last_fixed, first_found=first_found, last_found=last_found)
                    device.add_vulnerable_software(cve_id=cve)
            except Exception:
                logger.exception(f'Problem getting vuln raw {vuln_raw}')
        if not found_scan_id:
            return None
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

        try:
            device.set_raw(device_raw)
        except Exception as e:
            logger.exception('failed to set raw')

        return device

    def yield_assets(self, assets_raw):
        result = (yield from assets_raw)
        if isinstance(result, str):
            self.create_notification(f'Tenable.io Export Error', result, severity_type='error')

    def _parse_raw_data(self, devices_raw_data_all):
        agent_ids = set()
        for device_raw, device_type, client_data, uuid_to_id_scans_dict in devices_raw_data_all:
            try:
                if AGENT_TYPE == device_type:
                    if device_raw.get('id') in agent_ids:
                        continue
                    agent_ids.add(device_raw.get('id'))
                    device = self._create_agent_device(device_raw)
                    if device:
                        yield device
                elif ASSET_TYPE == device_type:
                    for device_id, device_asset_raw in self.yield_assets(device_raw):
                        try:
                            device = self._parse_export_device(device_id, device_asset_raw, client_data,
                                                               uuid_to_id_scans_dict)
                            if device:
                                yield device
                        except Exception:
                            logger.exception(f'Problem with parsing device {device_asset_raw}')
            except Exception:
                logger.exception(f'Problem with device raw {device_raw}')

    def _create_agent_device(self, agent_raw):
        try:
            device = self._new_device_adapter()
            device_id = agent_raw.get('id')
            if not device_id:
                logger.warning(f'Bad agent with no ID {agent_raw}')
                return None
            hostname = agent_raw.get('name')
            device.id = str(device_id) + hostname or ''
            device.hostname = hostname
            ip = agent_raw.get('ip')
            if ip:
                device.add_nic(None, [ip])
            device.last_seen = parse_date(agent_raw.get('last_connect'))
            device.last_connect = parse_date(agent_raw.get('last_connect'))
            device.last_scanned = parse_date(agent_raw.get('last_scanned'))
            device.linked_on = parse_date(agent_raw.get('linked_on'))

            device.has_agent = True
            device.status = agent_raw.get('status')
            device.agent_uuid = agent_raw.get('uuid')
            device.add_agent_version(agent=AGENT_NAMES.tenable_io, version=agent_raw.get('core_version'))
            device.adapter_properties = [AdapterProperty.Agent.name,
                                         AdapterProperty.Vulnerability_Assessment.name,
                                         AdapterProperty.Endpoint_Protection_Platform.name]
            device.set_raw(agent_raw)
            return device
        except Exception:
            logger.exception(f'Problem parsing {agent_raw}')
            return None

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network, AdapterProperty.Vulnerability_Assessment]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'exclude_no_last_scan',
                    'title': 'Do not fetch devices with no \'Last Scan\'',
                    'type': 'bool'
                },
                {
                    'name': 'scan_id_white_list',
                    'title': 'Scan IDs whitelist',
                    'type': 'string'
                },
                {
                    'name': 'adapter_key_white_list',
                    'title': 'Tag key whitelist',
                    'type': 'string'
                },
                {
                    'name': 'fetch_agent_data',
                    'title': 'Fetch agent data',
                    'type': 'bool'
                },
                {
                    'name': 'cancel_old_export_jobs',
                    'title': 'Cancel old export jobs',
                    'type': 'bool'
                },
                {
                    'name': 'drop_only_ip_devices',
                    'title': 'Do not fetch devices with no MAC address and no hostname',
                    'type': 'bool'
                },
            ],
            'required': [
                'exclude_no_last_scan',
                'fetch_agent_data',
                'drop_only_ip_devices',
                'cancel_old_export_jobs'
            ],
            'pretty_name': 'Tenable.io Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'exclude_no_last_scan': False,
            'drop_only_ip_devices': False,
            'scan_id_white_list': None,
            'adapter_key_white_list': None,
            'fetch_agent_data': True,
            'cancel_old_export_jobs': False
        }

    def _on_config_update(self, config):
        self.__drop_only_ip_devices = config.get('drop_only_ip_devices') or False
        self.__exclude_no_last_scan = config.get('exclude_no_last_scan')
        self.__scan_id_white_list = config['scan_id_white_list'].split(',') \
            if config.get('scan_id_white_list') else None
        self.__adapter_key_white_list = config['adapter_key_white_list'].split(',') \
            if config.get('adapter_key_white_list') else None
        self.__fetch_agent_data = config['fetch_agent_data'] if 'fetch_agent_data' in config else True
        self.__cancel_old_export_jobs = config.get('cancel_old_export_jobs')

    def outside_reason_to_live(self) -> bool:
        """
        This adapter might be called from outside, let it live
        """
        return True
