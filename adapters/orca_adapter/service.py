import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.parsing import figure_out_cloud
from axonius.smart_json_class import SmartJsonClass
from axonius.fields import Field, ListField
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from orca_adapter.connection import OrcaConnection
from orca_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class AlertState(SmartJsonClass):
    alert_status = Field(str, 'Status')
    alert_status_time = Field(datetime.datetime, 'Status Time')
    alert_created_at = Field(datetime.datetime, 'Created At')
    alert_severity = Field(str, 'Severity')
    alert_last_seen = Field(datetime.datetime, 'Last Seen')
    alert_score = Field(str, 'Score')
    alert_low_reason = Field(str, 'Low Reason')
    alert_low_since = Field(datetime.datetime, 'low_since')
    alert_high_since = Field(datetime.datetime, 'high_since')


class AlertData(SmartJsonClass):
    alert_id = Field(str, 'Alert Id')
    score = Field(int, 'Score')
    alert_type = Field(str, 'Alert Type')
    description = Field(str, 'Description')
    details = Field(str, 'Details')
    recommendation = Field(str, 'Recommendation')
    alert_labels = ListField(str, 'Alert Labels')
    alert_state = Field(AlertState, 'Alert State')
    alert_source = Field(str, 'Alert Source')


class MalwareData(SmartJsonClass):
    virus_names = ListField(str, 'Virus Names')
    file = Field(str, 'File')
    md5 = Field(str, 'MD5')
    sha1 = Field(str, 'SHA1')
    sha256 = Field(str, 'SHA256')
    modification_time = Field(datetime.datetime, 'Modification Time')


class AffectedServices(SmartJsonClass):
    services = ListField(str, 'Services')
    is_public = Field(bool, 'Is Public')


class LoginData(SmartJsonClass):
    log_time = Field(datetime.datetime, 'Login Time')
    logout_time = Field(datetime.datetime, 'Logout Time')
    source_ipv4 = Field(str, 'Source IPv4')
    username = Field(str, 'Username')


class ComplianceData(SmartJsonClass):
    category = Field(str, 'Category')
    description = Field(str, 'Description')
    os = Field(str, 'OS')
    result = Field(str, 'Result')
    scored = Field(bool, 'Scored')
    subcategory = Field(str, 'Subcategory')
    test_name = Field(str, 'Test Name')
    version = Field(str, 'Version')


class OrcaGitRepo(SmartJsonClass):
    local_name = Field(str, 'Local Name')
    path = Field(str, 'Path')
    size = Field(int, 'Size')
    url = Field(str, 'URL')


class OrcaDb(SmartJsonClass):
    db_path = Field(str, 'DB Path')
    db_size = Field(int, 'DB Size')
    last_accessed_time = Field(datetime.datetime, 'Last Accessed Time')
    last_modified_time = Field(datetime.datetime, 'Last Modified Time')
    type = Field(str, 'Type')


class OrcaAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        asset_type = Field(str, 'Asset Type')
        asset_state = Field(str, 'Asset State')
        asset_labels = ListField(str, 'Asset Labels')
        asset_score = Field(int, 'Asset Score')
        asset_severity = Field(str, 'Asset Severity')
        asset_status = Field(str, 'Asset Status')
        status_time = Field(datetime.datetime, 'Status Time')
        region = Field(str, 'Region')
        alerts_data = ListField(AlertData, 'Alerts Data')
        malware_data = ListField(MalwareData, 'Malware Data')
        affected_services = ListField(AffectedServices, 'Affected Services')
        failed_logins = ListField(LoginData, 'Failed Logins')
        successful_logins = ListField(LoginData, 'Successful Logins')
        compliance_information = ListField(ComplianceData, 'Compliance Infomation')
        git_repos = ListField(OrcaGitRepo, 'Git Repositories')
        orca_dbs = ListField(OrcaDb, 'Databases')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def get_connection(client_config):
        connection = OrcaConnection(domain=client_config['domain'],
                                    verify_ssl=client_config['verify_ssl'],
                                    https_proxy=client_config.get('https_proxy'),
                                    apikey=client_config['apikey'])
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema OrcaAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Orca Domain',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
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
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _create_device(self, device_raw, devices_alerst_dict, device_inventory_dict,
                       devices_logs_dict, devices_compliance_dict):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('asset_unique_id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('asset_name') or '')
            device.name = device_raw.get('asset_name')
            device.cloud_provider = figure_out_cloud(device_raw.get('cloud_provider'))
            device.cloud_id = device_raw.get('vm_id')
            try:
                logs_data = devices_logs_dict.get(device_id)
                if not isinstance(logs_data, list):
                    logs_data = []
                for log_raw in logs_data:
                    try:
                        if log_raw.get('login_failed'):
                            login_raw = log_raw.get('login_failed')
                            log_time = parse_date(login_raw.get('log_time'))
                            source_ipv4 = login_raw.get('source_ipv4')
                            username = login_raw.get('username')
                            device.failed_logins.append(LoginData(log_time=log_time,
                                                                  source_ipv4=source_ipv4,
                                                                  username=username))
                        elif log_raw.get('login_successful'):
                            login_raw = log_raw.get('login_successful')
                            log_time = parse_date(login_raw.get('log_time'))
                            source_ipv4 = login_raw.get('source_ipv4')
                            username = login_raw.get('username')
                            logout_time = parse_date(login_raw.get('logout_time'))
                            device.successful_logins.append(LoginData(log_time=log_time,
                                                                      source_ipv4=source_ipv4,
                                                                      logout_time=logout_time,
                                                                      username=username))
                    except Exception:
                        logger.exception(f'Problem with log_raw {log_raw}')
            except Exception:
                logger.exception(f'Problem getting inventory')
            try:
                compliance_data = devices_compliance_dict.get(device_id)
                if not isinstance(compliance_data, list):
                    compliance_data = []
                for compliance_raw in compliance_data:
                    try:
                        cis_raw = compliance_raw.get('cis_os') or {}
                        category = cis_raw.get('category')
                        description = cis_raw.get('description')
                        os = cis_raw.get('os')
                        result = cis_raw.get('result')
                        subcategory = cis_raw.get('subcategory')
                        test_name = cis_raw.get('test_name')
                        version = cis_raw.get('version')
                        scored = cis_raw.get('scored') \
                            if isinstance(cis_raw.get('scored'), bool) else None
                        device.compliance_information.append(ComplianceData(category=category,
                                                                            description=description,
                                                                            os=os,
                                                                            result=result,
                                                                            subcategory=subcategory,
                                                                            test_name=test_name,
                                                                            version=version,
                                                                            scored=scored))
                    except Exception:
                        logger.exception(f'Problem with compliance_raw {compliance_raw}')
            except Exception:
                logger.exception(f'Problem getting inventory')
            try:
                inventory_data = device_inventory_dict.get(device_id)
                if not isinstance(inventory_data, list):
                    inventory_data = []
                for inventory_raw in inventory_data:
                    if inventory_raw.get('package'):
                        try:
                            device.add_installed_software(name=(inventory_raw.get('package') or {}).get('name'),
                                                          version=(inventory_raw.get('package') or {}).get('version'))
                        except Exception:
                            logger.exception(f'Problem with inventory {inventory_raw}')
                    if inventory_raw.get('git_repository'):
                        git_repository = inventory_raw.get('git_repository')
                        if not isinstance(git_repository, dict):
                            git_repository = {}
                        git_size = git_repository.get('size') if isinstance(git_repository.get('size'), int) else None
                        device.git_repos.append(OrcaGitRepo(local_name=git_repository.get('local_name'),
                                                            path=git_repository.get('path'),
                                                            size=git_size,
                                                            url=git_repository.get('url')))
                    if inventory_raw.get('database'):
                        orca_db = inventory_raw.get('database')
                        if not isinstance(orca_db, dict):
                            orca_db = {}
                        db_size = orca_db.get('db_size') if isinstance(orca_db.get('db_size'), int) else None
                        last_accessed_time = parse_date(orca_db.get('last_accessed_time'))
                        last_modified_time = parse_date(orca_db.get('last_modified_time'))

                        device.orca_dbs.append(OrcaDb(db_path=orca_db.get('db_path'),
                                                      db_size=db_size,
                                                      last_accessed_time=last_accessed_time,
                                                      last_modified_time=last_modified_time,
                                                      type=orca_db.get('type')))
            except Exception:
                logger.exception(f'Problem getting inventory')
            try:
                alerts_data = devices_alerst_dict.get(device_id)
                if not isinstance(alerts_data, list):
                    alerts_data = []
                for alert_raw in alerts_data:
                    try:
                        alert_id = alert_raw.get('alert_id')
                        score = alert_raw.get('score') if isinstance(alert_raw.get('score'), int) else None
                        alert_type = alert_raw.get('type_string')
                        description = alert_raw.get('description')
                        details = alert_raw.get('details')
                        recommendation = alert_raw.get('recommendation')
                        alert_labels = alert_raw.get('alert_labels')\
                            if isinstance(alert_raw.get('alert_labels'), list) else None
                        alert_state_obj = None
                        alert_state = alert_raw.get('state')
                        if isinstance(alert_state, dict):
                            alert_status = alert_state.get('status')
                            alert_status_time = parse_date(alert_state.get('status_time'))
                            alert_created_at = parse_date(alert_state.get('created_at'))
                            alert_severity = alert_state.get('severity')
                            alert_last_seen = parse_date(alert_state.get('last_seen'))
                            alert_score = alert_state.get('score')
                            alert_low_reason = alert_state.get('low_reason')
                            alert_low_since = parse_date(alert_state.get('low_since'))
                            alert_high_since = parse_date(alert_state.get('high_since'))
                            alert_state_obj = AlertState(alert_status=alert_status,
                                                         alert_status_time=alert_status_time,
                                                         alert_created_at=alert_created_at,
                                                         alert_severity=alert_severity,
                                                         alert_last_seen=alert_last_seen,
                                                         alert_score=alert_score,
                                                         alert_low_reason=alert_low_reason,
                                                         alert_low_since=alert_low_since,
                                                         alert_high_since=alert_high_since)

                        alert_source = alert_raw.get('source')
                        finding_raw = alert_raw.get('findings')
                        if not isinstance(finding_raw, dict):
                            finding_raw = {}
                        cves_raw = finding_raw.get('cve')
                        if not isinstance(cves_raw, list):
                            cves_raw = []
                        try:
                            for cve_raw in cves_raw:
                                device.add_vulnerable_software(cve_id=cve_raw.get('cve_id'))
                        except Exception:
                            logger.exception(f'Problem with getting cve data in {device_raw}')
                        affected_services_raw = finding_raw.get('affected_services')
                        try:
                            if not isinstance(affected_services_raw, list):
                                affected_services_raw = []
                            for affected_service_raw in affected_services_raw:
                                device.affected_services.append(
                                    AffectedServices(is_public=affected_service_raw.get('is_public'),
                                                     services=affected_service_raw.get('services')))
                        except Exception:
                            logger.exception(f'Problem with getting affected_services data in {device_raw}')
                        malwares_raw = finding_raw.get('malware')
                        try:
                            if not isinstance(malwares_raw, list):
                                malwares_raw = []
                            for malware_raw in malwares_raw:
                                modification_time = parse_date(malware_raw.get('modification_time'))
                                device.malware_data.append(MalwareData(file=malware_raw.get('file'),
                                                                       md5=malware_raw.get('md5'),
                                                                       sha1=malware_raw.get('sha1'),
                                                                       sha256=malware_raw.get('sha256'),
                                                                       virus_names=malware_raw.get('virus_names'),
                                                                       modification_time=modification_time))
                        except Exception:
                            logger.exception(f'Problem with getting malware data in {device_raw}')

                        device.alerts_data.append(AlertData(alert_id=alert_id,
                                                            score=score,
                                                            alert_type=alert_type,
                                                            description=description,
                                                            details=details,
                                                            recommendation=recommendation,
                                                            alert_labels=alert_labels,
                                                            alert_state=alert_state_obj,
                                                            alert_source=alert_source))
                    except Exception:
                        logger.exception(f'Problem with alert {alert_raw}')
            except Exception:
                logger.exception(f'Problem getting alerts for {device_raw}')
            if isinstance(device_raw.get('asset_labels'), list):
                device.asset_labels = device_raw.get('asset_labels')
            device.asset_state = device_raw.get('asset_state')
            device.asset_score = device_raw.get('asset_score') \
                if isinstance(device_raw.get('asset_score'), int) else None
            device.owner = device_raw.get('owner')
            device.region = device_raw.get('region')
            if isinstance(device_raw.get('tags'), dict):
                try:
                    for tag_name, tag_value in device_raw.get('tags').items():
                        device.add_key_value_tag(tag_name, tag_value)
                except Exception:
                    logger.exception(f'Could not get tags')
            if isinstance(device_raw.get('tags_list'), list):
                for tag_list_raw in device_raw.get('tags_list'):
                    if isinstance(tag_list_raw, dict) and tag_list_raw.get('key'):
                        device.add_key_value_tag(key=tag_list_raw.get('key'), value=tag_list_raw.get('value'))
            device.asset_type = device_raw.get('asset_type')
            if isinstance(device_raw.get('private_ips'), list):
                device.add_nic(ips=device_raw.get('private_ips'))
            if isinstance(device_raw.get('public_ips'), list):
                device.add_nic(ips=device_raw.get('public_ips'))
                for public_ip in device_raw.get('public_ips'):
                    device.add_public_ip(ip=public_ip)
            device.first_seen = parse_date(device_raw.get('create_time'))

            state_raw = device_raw.get('state')
            if isinstance(state_raw, dict):
                device.first_seen = parse_date(state_raw.get('created_at'))
                device.last_seen = parse_date(state_raw.get('last_seen'))
                device.asset_score = state_raw.get('score') if isinstance(state_raw.get('score'), int) else None
                device.asset_severity = state_raw.get('severity')
                device.asset_status = state_raw.get('status')
                device.status_time = parse_date(state_raw.get('status_time'))
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Orca Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, devices_alerst_dict, device_inventory_dict, \
                devices_logs_dict, devices_compliance_dict in devices_raw_data:
            device = self._create_device(device_raw, devices_alerst_dict, device_inventory_dict,
                                         devices_logs_dict, devices_compliance_dict)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Vulnerability_Assessment]
