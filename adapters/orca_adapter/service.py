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


class AlertData(SmartJsonClass):
    alert_id = Field(str, 'Alert Id')
    score = Field(int, 'Score')
    alert_type = Field(str, 'Alert Type')
    description = Field(str, 'Description')
    details = Field(str, 'Details')
    recommendation = Field(str, 'Recommendation')
    alert_labels = ListField(str, 'Alert Labels')
    alert_state = Field(str, 'Alert State')
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


class OrcaAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        asset_type = Field(str, 'Asset Type')
        asset_state = Field(str, 'Asset State')
        asset_labels = ListField(str, 'Asset Labels')
        asset_score = Field(int, 'Asset Score')
        owner = Field(str, 'Owner')
        region = Field(str, 'Region')
        alerts_data = ListField(AlertData, 'Alerts Data')
        malware_data = ListField(MalwareData, 'Malware Data')
        affected_services = ListField(AffectedServices, 'Affected Services')

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
    def _create_device(self, device_raw, devices_alerst_dict, device_inventory_dict):
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
                inventory_data = device_inventory_dict.get(device_id)
                if not isinstance(inventory_data, list):
                    inventory_data = []
                device_raw['inventory_data'] = inventory_data
                for inventory_raw in inventory_data:
                    try:
                        device.add_installed_software(name=(inventory_raw.get('package') or {}).get('name'),
                                                      version=(inventory_raw.get('package') or {}).get('version'))
                    except Exception:
                        logger.exception(f'Problem with inventory {inventory_raw}')
            except Exception:
                logger.exception(f'Problem getting inventory')
            try:
                alerts_data = devices_alerst_dict.get(device_id)
                if not isinstance(alerts_data, list):
                    alerts_data = []
                device_raw['alerts_data'] = alerts_data
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
                        alert_state = alert_raw.get('state')
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
                                                            alert_state=alert_state,
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
            device.asset_type = device_raw.get('asset_type')
            if isinstance(device_raw.get('private_ips'), list):
                device.add_nic(ips=device_raw.get('private_ips'))
            if isinstance(device_raw.get('public_ips'), list):
                device.add_nic(ips=device_raw.get('public_ips'))
                for public_ip in device_raw.get('public_ips'):
                    device.add_public_ip(ip=public_ip)
            device.first_seen = parse_date(device_raw.get('create_time'))
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Orca Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, devices_alerst_dict, device_inventory_dict in devices_raw_data:
            device = self._create_device(device_raw, devices_alerst_dict, device_inventory_dict)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Vulnerability_Assessment]
