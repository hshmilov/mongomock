import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.parsing import is_domain_valid
from redcanary_adapter.connection import RedcanaryConnection
from redcanary_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class DetectionData(SmartJsonClass):
    headline = Field(str, 'Headline')
    confirmed_at = Field(datetime.datetime, 'Confirmed At')
    summary = Field(str, 'Summary')
    severity = Field(str, 'Severity')
    last_activity_seen_at = Field(datetime.datetime, 'Last Activity Seen At')
    superclassification = Field(str, 'Superclassification')
    subclassification = Field(str, 'Subclassification')
    time_of_occurrence = Field(datetime.datetime, 'Time Of Occurrence')
    last_acknowledged_at = Field(datetime.datetime, 'Last Acknowledged At')
    last_acknowledged_by_email = Field(str, 'Last Acknowledged By Email')
    last_acknowledged_by_name = Field(str, 'Last Acknowledged By Name')
    remediation_reason = Field(str, 'Last Remediation Reason')
    remediation_state = Field(str, 'Last Remediation State')
    last_remediated_by_email = Field(str, 'Last Remediated By Email')
    last_remediated_by_name = Field(str, 'Last Remediated By Name')
    remediation_marked_at = Field(datetime.datetime, 'Last Remediation Marked At')


class RedcanaryAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        is_decommissioned = Field(bool, 'Is Decommissioned')
        is_isolated = Field(bool, 'Is Isolated')
        monitoring_status = Field(str, 'Monitoring Status')
        detection_data = ListField(DetectionData, 'Detections Data')
        endpoint_status = Field(str, 'Endpoint Status')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = RedcanaryConnection(domain=client_config['domain'],
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
        The schema RedcanaryAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Redcanary Domain',
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

    # pylint: disable=too-many-nested-blocks,too-many-branches,too-many-statements,too-many-locals
    def _create_device(self, device_raw, detections_dict):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None or 'attributes' not in device_raw:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device_attributes = device_raw['attributes']
            device.id = str(device_id) + '_' + (device_attributes.get('hostname') or '')
            hostname = device_attributes.get('hostname')
            device.endpoint_status = device_attributes.get('endpoint_status')
            detections_list = detections_dict.get(str(device_id))
            if not isinstance(detections_list, list):
                detections_list = []
            for detection_raw in detections_list:
                try:
                    detection_attributes = detection_raw.get('attributes')
                    if not isinstance(detection_attributes, dict):
                        detection_attributes = {}
                    last_activity_seen_at = parse_date(detection_attributes.get('last_activity_seen_at'))
                    classification_raw = detection_attributes.get('classification')
                    if not isinstance(classification_raw, dict):
                        classification_raw = {}
                    time_of_occurrence = parse_date(detection_attributes.get('time_of_occurrence'))
                    last_acknowledged_at = parse_date(detection_attributes.get('last_acknowledged_at'))
                    last_acknowledged_by = detection_attributes.get('last_acknowledged_by')
                    if not isinstance(last_acknowledged_by, dict):
                        last_acknowledged_by = {}
                    last_acknowledged_by_attr = last_acknowledged_by.get('attributes')
                    if not isinstance(last_acknowledged_by_attr, dict):
                        last_acknowledged_by_attr = {}
                    last_remediated_status = detection_attributes.get('last_remediated_status')
                    if not isinstance(last_remediated_status, dict):
                        last_remediated_status = {}
                    remedication_marked_by = last_remediated_status.get('marked_by')
                    if not isinstance(remedication_marked_by, dict):
                        remedication_marked_by = {}
                    remedication_marked_by_attr = remedication_marked_by.get('attributes')
                    if not isinstance(remedication_marked_by_attr, dict):
                        remedication_marked_by_attr = {}
                    last_remediated_by_email = remedication_marked_by_attr.get('email')
                    last_remediated_by_name = remedication_marked_by_attr.get('name')
                    remediation_marked_at = parse_date(last_remediated_status.get('marked_at'))
                    detection_obj = DetectionData(headline=detection_attributes.get('headline'),
                                                  confirmed_at=parse_date(detection_attributes.get('confirmed_at')),
                                                  summary=detection_attributes.get('summary'),
                                                  severity=detection_attributes.get('severity'),
                                                  last_activity_seen_at=last_activity_seen_at,
                                                  superclassification=classification_raw.get('superclassification'),
                                                  subclassification=classification_raw.get('subclassification'),
                                                  time_of_occurrence=time_of_occurrence,
                                                  last_acknowledged_at=last_acknowledged_at,
                                                  last_acknowledged_by_email=last_acknowledged_by_attr.get('email'),
                                                  last_acknowledged_by_name=last_acknowledged_by_attr.get('name'),
                                                  remediation_reason=last_remediated_status.get('reason'),
                                                  remediation_state=last_remediated_status.get('remediation_state'),
                                                  remediation_marked_at=remediation_marked_at,
                                                  last_remediated_by_email=last_remediated_by_email,
                                                  last_remediated_by_name=last_remediated_by_name
                                                  )
                    device.detection_data.append(detection_obj)
                except Exception:
                    logger.exception(f'Problem with detection raw {detection_raw}')
            device.hostname = hostname
            if '.' in hostname:
                domain = '.'.join(hostname.split('.')[1:])
                if is_domain_valid(domain):
                    device.domain = domain
            try:
                if '\\' in hostname:
                    device.hostname = hostname.split('\\')[1]
                    device.domain = hostname.split('\\')[0]
            except Exception:
                logger.exception(f'Problem with domain parsing')
            device.monitoring_status = device_attributes.get('monitoring_status')
            try:
                device.figure_os((device_attributes.get('platform') or '') + ' ' +
                                 (device_attributes.get('operating_system') or ''))
            except Exception:
                logger.exception(f'Problem getting os for {device_raw}')
            device.is_isolated = device_attributes.get('is_isolated')
            device.is_decommissioned = device_attributes.get('is_decommissioned')
            try:
                device.last_seen = parse_date(device_attributes.get('last_checkin_time'))
            except Exception:
                logger.exception(f'Problem getting last seen for {device_raw}')
            if device_attributes.get('username'):
                device.last_used_users = [device_attributes.get('username')]
            nics = device_attributes.get('endpoint_network_addresses')
            if nics and isinstance(nics, list):
                for nic in nics:
                    mac = None
                    ips = None
                    try:
                        mac = nic['attributes']['mac_address']
                        if not mac:
                            mac = None
                        else:
                            mac = mac['attributes']['address']
                            if not mac:
                                mac = None
                    except Exception:
                        logger.exception(f'Problem getting mac in {nic}')
                    try:
                        ip = nic['attributes']['ip_address']['attributes']['ip_address']
                        if ip:
                            ips = [ip]
                    except Exception:
                        logger.exception(f'Problem getting ip in {nic}')
                    if mac or ips:
                        device.add_nic(mac, ips)
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Redcanary Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, detections_dict in devices_raw_data:
            device = self._create_device(device_raw, detections_dict)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]
