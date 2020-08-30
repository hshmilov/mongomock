import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, int_or_none
from ibm_qradar_adapter.connection import IbmQradarConnection
from ibm_qradar_adapter.client_id import get_client_id
from ibm_qradar_adapter.structures import IbmQradarDeviceInstance, IbmQradarLogSourceTypeInstance, \
    IbmQradarLogSourceGroupInstance, IbmQradarLogSourceStatus

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class IbmQradarAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(IbmQradarDeviceInstance):
        pass

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
        connection = IbmQradarConnection(domain=client_config['domain'],
                                         verify_ssl=client_config['verify_ssl'],
                                         https_proxy=client_config.get('https_proxy'),
                                         proxy_username=client_config.get('proxy_username'),
                                         proxy_password=client_config.get('proxy_password'),
                                         username=client_config.get('username'),
                                         password=client_config.get('password'),
                                         token=client_config.get('token'))
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema IbmQradarAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Host Name or IP Address',
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
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
                {
                    'name': 'proxy_username',
                    'title': 'HTTPS Proxy User Name',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS Proxy Password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                'domain',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_ibm_qradar_device_fields(device_raw: dict, log_source_types_by_id: dict, log_source_groups_by_id: dict,
                                       device: MyDeviceAdapter):
        try:
            device.protocol_type = int_or_none(device_raw.get('protocol_type_id'))
            device.gateway = parse_bool_from_raw(device_raw.get('gateway'))
            device.internal = parse_bool_from_raw(device_raw.get('internal'))
            device.credibility = int_or_none(device_raw.get('credibility'))
            device.event_collector_id = int_or_none(device_raw.get('target_event_collector_id '))
            device.extension_id = int_or_none(device_raw.get('extension_id'))
            device.language_id = int_or_none(device_raw.get('language_id'))
            device.auto_discovered = parse_bool_from_raw(device_raw.get('auto_discovered'))

            log_source_status = device_raw.get('status')
            if log_source_status and isinstance(log_source_status, dict):
                device.status = log_source_status.get('status')
                statuses = log_source_status.get('messages')
                if statuses and isinstance(statuses, list):
                    log_source_statuses = []
                    for status in statuses:
                        if isinstance(status, dict):
                            message = IbmQradarLogSourceStatus()
                            message.severity = status.get('severity')
                            message.text = status.get('text')
                            message.timestamp = parse_date(status.get('timestamp'))
                            log_source_statuses.append(message)
                    device.log_source_statuses = log_source_statuses

            type_id = device_raw.get('type_id')
            if (type_id and
                    log_source_types_by_id.get(type_id) and
                    isinstance(log_source_types_by_id.get(type_id), dict)):
                log_source_type_info = log_source_types_by_id.get(type_id)
                log_source_type = IbmQradarLogSourceTypeInstance()
                log_source_type.id = int_or_none(log_source_type_info.get('id'))
                log_source_type.name = log_source_type_info.get('name')
                log_source_type.internal = parse_bool_from_raw(log_source_type_info.get('internal'))
                log_source_type.custom = parse_bool_from_raw(log_source_type_info.get('custom'))
                log_source_type.version = log_source_type_info.get('version')

                device.log_source_type = log_source_type

            group_ids = device_raw.get('group_ids')
            if group_ids and isinstance(group_ids, list):
                device.groups_ids = group_ids
                log_source_groups = []
                for group_id in group_ids:
                    if (log_source_groups_by_id.get(group_id) and
                            isinstance(log_source_groups_by_id.get(group_id), dict)):
                        group = log_source_groups_by_id.get(group_id)
                        log_source_group = IbmQradarLogSourceGroupInstance()
                        log_source_group.id = int_or_none(group.get('id'))
                        log_source_group.name = group.get('name')
                        log_source_group.description = group.get('description')
                        log_source_group.parent_id = int_or_none(group.get('parent_id'))
                        log_source_group.owner = group.get('owner')
                        log_source_group.last_modified = parse_date(group.get('last_modified'))
                        log_source_groups.append(log_source_group)
            device.log_source_groups = log_source_groups

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, log_source_types_by_id: dict, log_source_groups_by_id: dict,
                       device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')

            hostname = device_raw.get('name')
            try:
                if isinstance(hostname, str) and '@' in hostname:
                    hostname = hostname.split('@')[-1] or hostname
                    hostname = hostname.strip()
            except Exception:
                logger.warning(f'Failed splitting hostname {hostname}, filling full hostname')
            device.hostname = hostname

            device.description = device_raw.get('description')
            enabled = parse_bool_from_raw(device_raw.get('enabled'))
            if isinstance(enabled, bool):
                device.device_disabled = not enabled
            device.first_seen = parse_date(device_raw.get('creation_date'))
            device.last_seen = parse_date(device_raw.get('last_event_time'))

            self._fill_ibm_qradar_device_fields(device_raw, log_source_types_by_id, log_source_groups_by_id, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching IbmQradar Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for device_raw, log_source_types_by_id, log_source_groups_by_id in devices_raw_data:
            if not device_raw:
                continue
            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, log_source_types_by_id, log_source_groups_by_id,
                                             self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching IbmQradar Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
