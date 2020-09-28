import logging

from axonius.utils.parsing import parse_date
from axonius.utils.files import get_local_config_file
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from vectra_adapter.client_id import get_client_id
from vectra_adapter.structures import VectraInstance, Detection
from vectra_adapter.connection import VectraConnection

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class VectraAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(VectraInstance):
        pass

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
        connection = VectraConnection(domain=client_config['domain'],
                                      token=client_config['token'],
                                      verify_ssl=client_config.get('verify_ssl') or False)
        with connection:
            pass  # check the connection credentials are valid
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
        The schema VectraAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Vectra Domain',
                    'type': 'string'
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
                    'type': 'bool',
                },
            ],
            'required': [
                'domain',
                'token'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_vectra_detection_fields(detections_raw, device_instance: MyDeviceAdapter):
        try:
            detections = []
            for detection_raw in detections_raw:
                detection = Detection()
                detection.assigned_date = parse_date(detection_raw.get('assigned_date'))
                detection.assigned_to = detection_raw.get('assigned_to')
                detection.c_score = detection_raw.get('c_score')
                detection.category = detection_raw.get('category')
                detection.certainty = detection_raw.get('certainty')
                detection.custom_detection = detection_raw.get('custom_detection')
                detection.description = detection_raw.get('description')
                detection.detection = detection_raw.get('detection')
                detection.detection_category = detection_raw.get('detection_category')
                detection.detection_type = detection_raw.get('detection_type')
                detection.detection_url = detection_raw.get('detection_url')
                detection.first_timestamp = parse_date(detection_raw.get('first_timestamp'))
                detection.id = detection_raw.get('id')
                detection.is_custom_model = detection_raw.get('is_custom_model')
                detection.is_marked_custom = detection_raw.get('is_marked_custom')
                detection.is_targeting_key_asset = detection_raw.get('is_targeting_key_asset')
                detection.last_timestamp = parse_date(detection_raw.get('last_timestamp'))
                detection.note = detection_raw.get('note')
                detection.note_modified_by = detection_raw.get('note_modified_by')
                detection.note_modified_timestamp = parse_date(detection_raw.get('note_modified_timestamp'))
                detection.src_account = detection_raw.get('src_account')
                detection.src_ip = detection_raw.get('src_ip')
                detection.t_score = detection_raw.get('t_score')
                detection.tags = detection_raw.get('tags')
                detection.targets_key_asset = detection_raw.get('targets_key_asset')
                detection.threat = detection_raw.get('threat')
                detection.triage_rule_id = detection_raw.get('triage_rule_id')
                detection.url = detection_raw.get('url')

                detections.append(detection)

            device_instance.detections = detections
        except Exception:
            logger.exception(f'Failed to parse Vectra detections info for device {detections_raw}')

    def _fill_vectra_fields(self, device_raw, device_instance: MyDeviceAdapter):
        try:
            device_instance.active_traffic = device_raw.get('active_traffic')
            device_instance.assigned_date = parse_date(device_raw.get('assigned_date'))
            device_instance.certainty_score = device_raw.get('c_score')
            device_instance.host_luid = device_raw.get('host_luid')
            device_instance.host_url = device_raw.get('host_url')
            device_instance.note = device_raw.get('note')
            device_instance.note_modified_by = device_raw.get('note_modified_by')
            device_instance.note_modified_date = parse_date(device_raw.get('note_modified_timestamp'))
            device_instance.sensor = device_raw.get('sensor')
            device_instance.sensor_name = device_raw.get('sensor_name')
            device_instance.state = device_raw.get('state')
            device_instance.threat_score = device_raw.get('t_score')
            device_instance.url = device_raw.get('url')

            try:
                device_instance.detections_ids = device_raw.get('detection_ids')
            except Exception:
                logger.debug(f'Failed parsing device detection ids: {device_raw.get("detection_ids")}')

            try:
                device_instance.host_session_luid = device_raw.get('host_session_luids')
            except Exception:
                logger.debug(f'Failed parsing device host session luid: {device_raw.get("host_session_luids")}')

            try:
                device_instance.groups = device_raw.get('groups')
            except Exception:
                logger.debug(f'Failed parsing device groups: {device_raw.get("groups")}')

            try:
                device_instance.previous_ips = device_raw.get('previous_ips')
            except Exception:
                logger.debug(f'Failed parsing device previous ips: {device_raw.get("previous_ips")}')

            try:
                device_instance.tags_list = device_raw.get('tags')
            except Exception:
                logger.debug(f'Failed parsing device tags: {device_raw.get("tags")}')

            if isinstance(device_raw.get('detections_by_id'), list):
                self._fill_vectra_detection_fields(device_raw.get('detections_by_id'), device_instance)

        except Exception:
            logger.exception(f'Failed to parse Vectra instance info for device {device_raw}')

    def _create_device(self, device_raw, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if not device_id:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')

            device.hostname = device_raw.get('name')
            device.owner = device_raw.get('owner_name')

            last_modify = parse_date(device_raw.get('last_modified'))
            last_detection = parse_date(device_raw.get('last_detection_timestamp'))
            if last_modify and last_detection:
                last_seen = max(last_detection, last_modify)
            else:
                last_seen = last_modify or last_detection
            if last_seen:
                device.last_seen = parse_date(last_seen)

            if isinstance(device_raw.get('tags'), list):
                for key in device_raw.get('tags'):
                    device.add_key_value_tag(key, None)

            ips = []
            if device_raw.get('last_source'):
                ips.append(device_raw.get('last_source'))
            if device_raw.get('ip'):
                ips.append(device_raw.get('ip'))
            device.add_ips_and_macs(ips=ips)

            self._fill_vectra_fields(device_raw, device)
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Vectra Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching Vectra Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
