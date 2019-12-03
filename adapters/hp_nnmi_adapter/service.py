import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from hp_nnmi_adapter.connection import HpNnmiConnection
from hp_nnmi_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class HpNnmiAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        modified = Field(datetime.datetime, 'Last Modified')
        update_time = Field(datetime.datetime, 'Update Time')
        discovery_analysis_updated = Field(bool, 'Discovery Analysis Updated')
        node_resent = Field(int, 'Node Resent')
        status = Field(str, 'Status')
        is_end_node = Field(bool, 'End Node')
        is_snmp_supported = Field(bool, 'SNMP Supported')
        system_name = Field(str, 'System Name')
        system_contact = Field(str, 'System Contact')
        system_description = Field(str, 'System Description')
        system_location = Field(str, 'System Location')
        system_object_id = Field(str, 'System Object ID')
        long_name = Field(str, 'Long Name')
        management_module = Field(str, 'Management Module')
        discovery_state = Field(str, 'Discovery State')
        notes = Field(str, 'Notes')
        snmp_version = Field(str, 'SNMP Version')

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
        connection = HpNnmiConnection(domain=client_config['domain'],
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
        The schema HpNnmiAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'HP NNMi Domain',
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

    @staticmethod
    def _create_device(device: MyDeviceAdapter, device_raw):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('name') or '')
            device.first_seen = parse_date(device_raw.get('created'))
            device.last_seen = parse_date(device_raw.get('modified'))
            device.device_model = device_raw.get('deviceModel')
            device.device_model_family = device_raw.get('deviceFamily')
            device.uuid = device_raw.get('uuid')
            device.status = device_raw.get('status')
            device.is_end_node = device_raw.get('isEndNode') if isinstance(device_raw.get('isEndNode'), bool) else None
            device.is_snmp_supported = device_raw.get('isSnmpSupported') \
                if isinstance(device_raw.get('isSnmpSupported'), bool) else None
            device.hostname = device_raw.get('systemName')
            device.system_contact = device_raw.get('systemContact')
            device.system_description = device_raw.get('systemDescription')
            device.system_location = device_raw.get('systemLocation')
            device.system_object_id = device_raw.get('systemObjectId')
            device.long_name = device_raw.get('longName')
            device.management_module = device_raw.get('managementMode')
            device.discovery_state = device_raw.get('discoveryState')
            device.notes = device_raw.get('notes')
            device.snmp_version = device_raw.get('snmpVersion')
            device.discovery_analysis_updated = device_raw.get('discoveryAnalysisUpdated') \
                if isinstance(device_raw.get('discoveryAnalysisUpdated'), bool) else None
            device.node_resent = device_raw.get('nodeResent') if isinstance(device_raw.get('nodeResent'), int) else None

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching HpNnmi Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(self._new_device_adapter(), device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
