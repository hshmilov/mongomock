
import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from tripwire_enterprise_adapter.client_id import get_client_id
from tripwire_enterprise_adapter.connection import TripWireEnterpriseConnection

logger = logging.getLogger(f'axonius.{__name__}')


class TripwireEnterpriseAdapter(AdapterBase):
    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        source_id = Field(str, 'Source ID')
        external_id = Field(str, 'External ID')
        has_agent = Field(bool, 'Has Agent')
        is_axon = Field(bool, 'Is Axon')
        agent_name = Field(str, 'Agent Name')
        agent_version = Field(str, 'Agent Version')
        asset_status = Field(str, 'Asset Status')
        start_time = Field(datetime.datetime, 'Start Time')
        delegate_name = Field(str, 'Delegate Name')
        delegate_agent_version = Field(str, 'Delegate Agent Version')
        current_duration_seconds = Field(float, 'Current Duration Seconds')
        average_duration_seconds = Field(float, 'Average Duration Seconds')
        standard_deviation_seconds = Field(float, 'Standard Deviation Seconds')
        rule_complete_count = Field(int, 'Rule Complete Count')
        rule_total_count = Field(int, 'Rule Total Count')
        operation_name = Field(str, 'Operation Name')
        operation_descritpion = Field(str, 'Operation Description')
        operation_type = Field(str, 'Operation Type')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _connect_client(self, client_config):
        client_id = self._get_client_id(client_config)
        try:
            connection = TripWireEnterpriseConnection(domain=client_config['domain'],
                                                      verify_ssl=client_config['verify_ssl'],
                                                      username=client_config['username'],
                                                      password=client_config['password'],
                                                      https_proxy=client_config.get('https_proxy'))
            with connection:
                pass
        except Exception as e:
            logger.error(f'Failed to connect to client {client_id}')
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, client_data):
        with client_data:
            yield from client_data.get_devices()

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Tripwire Enter Domain',
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

    def create_device(self, device_raw):
        device = self._new_device_adapter()
        name = device_raw.get('name')
        source_id = device_raw.get('sourceId')
        external_id = device_raw.get('externalId')
        if not name:
            logger.warning(f'Bad device with no name {device_raw}')
            return None
        device.id = name + '_' + (source_id or '') + '_' + (external_id or '')
        device.has_agent = device_raw.get('hasAgent')
        device.is_axon = device_raw.get('isAxon')
        device.agent_version = device_raw.get('agentVersion')
        device.asset_status = device_raw.get('status')
        device.agent_name = device_raw.get('agent')
        device.start_time = device_raw.get('startTime')
        device.delegate_name = device_raw.get('delegate')
        device.delegate_agent_version = device_raw.get('delegateAgentVersion')
        device.current_duration_seconds = device_raw.get('currentDurationSeconds')
        device.average_duration_seconds = device_raw.get('averageDurationSeconds')
        device.standard_deviation_seconds = device_raw.get('standardDeviationSeconds')
        device.rule_complete_count = device_raw.get('ruleCompleteCount')
        device.rule_total_count = device_raw.get('ruleTotalCount')
        try:
            operation = device_raw.get('operation')
            if operation and isinstance(operation, dict):
                device.operation_name = operation.get('name')
                device.operation_descritpion = operation.get('description')
                device.operation_type = operation.get('type')
        except Exception:
            logger.exception(f'Problem adding opeartion to {device_raw}')

        device.set_raw(device_raw)
        return device

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in iter(devices_raw_data):
            try:
                device = self.create_device(device_raw)
                if device:
                    yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
