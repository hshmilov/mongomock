import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.utils.datetime import parse_date
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.files import get_local_config_file
from endgame_adapter.connection import EndgameConnection
from endgame_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class DeviceSensor(SmartJsonClass):
    sensor_status = Field(str, 'Status')
    sensor_version = Field(str, 'Version')
    sensor_type = Field(str, 'Type')
    sensor_id = Field(str, 'Id')
    policy_id = Field(str, 'Policy Id')
    policy_name = Field(str, 'Policy Name')
    policy_status = Field(str, 'Policy Status')


class EndgameAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        machine_id = Field(str, 'Machine Id')
        agent_status = Field(str, 'Agent Status')
        device_tags = ListField(str, 'Device Tags')
        device_groups = ListField(str, 'Device Groups')
        investigation_count = Field(int, 'Investigation Count')
        alert_count = Field(str, 'Alert Count')
        device_error = Field(str, 'Device Error')
        sensors = ListField(DeviceSensor, 'Sensors')
        created_at = Field(datetime.datetime, 'Created At')
        updated_at = Field(datetime.datetime, 'Updated At')
        status_changed_at = Field(datetime.datetime, 'Status Changed At')
        is_isolated = Field(bool, 'Is Isolated')
        endgame_domain = Field(str, 'Endgame Domain')

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
        connection = EndgameConnection(domain=client_config['domain'],
                                       verify_ssl=client_config['verify_ssl'],
                                       https_proxy=client_config.get('https_proxy'),
                                       username=client_config['username'],
                                       password=client_config['password'])
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
        The schema EndgameAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Endgame Domain',
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
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('machine_id') or '')
            device.machine_id = device_raw.get('machine_id')
            domain = device_raw.get('domain')
            device.endgame_domain = domain
            device.name = device_raw.get('name')
            device.hostname = device_raw.get('hostname')
            if isinstance(device_raw.get('investigation_count'), int):
                device.investigation_count = device_raw.get('investigation_count')
            try:
                if isinstance(device_raw.get('tags'), list):
                    for tag_raw in device_raw.get('tags'):
                        if tag_raw.get('name'):
                            device.device_tags.append(tag_raw.get('name'))
            except Exception:
                logger.exception(f'Problem adding tags to {device_raw}')
            try:
                if isinstance(device_raw.get('groups'), list):
                    for group_raw in device_raw.get('groups'):
                        if group_raw.get('name'):
                            device.device_groups.append(group_raw.get('name'))
            except Exception:
                logger.exception(f'Problem adding groups to {device_raw}')
            device.alert_count = device_raw.get('alert_count')
            device.figure_os(device_raw.get('display_operating_system'))
            device.agent_status = device_raw.get('status')
            device.is_isolated = bool(device_raw.get('is_isolated'))
            try:
                macs = device_raw.get('mac_address').split(',') if device_raw.get('mac_address') else None
                ips = device_raw.get('ip_address').split(',') if device_raw.get('ip_address') else None
                device.add_ips_and_macs(macs=macs, ips=ips)
            except Exception:
                logger.exception(f'Problem adding nic to {device_raw}')
            device.device_error = device_raw.get('error')
            if isinstance(device_raw.get('sensors'), list):
                for sensor_raw in device_raw.get('sensors'):
                    try:
                        device.sensors.append(DeviceSensor(sensor_status=sensor_raw.get('status'),
                                                           sensor_version=sensor_raw.get('sensor_version'),
                                                           sensor_type=sensor_raw.get('sensor_type'),
                                                           sensor_id=sensor_raw.get('id'),
                                                           policy_id=sensor_raw.get('policy_id'),
                                                           policy_name=sensor_raw.get('policy_name'),
                                                           policy_status=sensor_raw.get('policy_status')))
                    except Exception:
                        logger.exception(f'Problem adding sensor raw {sensor_raw}')
            device.created_at = parse_date(device_raw.get('created_at'))
            device.updated_at = parse_date(device_raw.get('updated_at'))
            device.status_changed_at = parse_date(device_raw.get('status_changed_at'))
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Endgame Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]
