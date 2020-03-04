import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from contrast_security_adapter.connection import ContrastSecurityConnection
from contrast_security_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class ContrastSecurityAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        contrast_server_id = Field(int, 'Server ID')
        server_name = Field(str, 'Server Name')
        server_type = Field(str, 'Server Type')
        environment = Field(str, 'Server Environment')  # enum=['DEVELOPMENT','QA','PRODUCTION']
        container = Field(str, 'Container')
        server_path = Field(str, 'Server Path')
        server_status = Field(str, 'Server Status')  # enum=[ONLINE,OFFLINE]
        is_assess = Field(bool, 'Is Server Assess')
        is_assess_pending = Field(bool, 'Assess Pending', description='Is Assess changing on restart')
        assess_last_updated = Field(datetime.datetime, 'Assess Last Updated')
        asses_sensors_active = Field(bool, 'Are Assess Sensors Active')
        is_defend = Field(bool, 'Is Server Defend')
        is_defend_pending = Field(bool, 'Defend Pending', description='Is Defend changing on restart')
        defend_sensors_active = Field(bool, 'Are Defend Sensors Active')
        defend_last_updated = Field(datetime.datetime, 'Defend Last Updated')
        agent_language = Field(str, 'Agent Language')
        agent_version = Field(str, 'Agent Version')
        is_agent_out_of_date = Field(bool, 'Is Agent Out Of Date')
        latest_available_agent_version = Field(str, 'Latest Agent Version Available')
        organization_uuid = Field(str, 'Organization ID')

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
        connection = ContrastSecurityConnection(domain=client_config['domain'],
                                                service_key=client_config['service_key'],
                                                verify_ssl=client_config['verify_ssl'],
                                                https_proxy=client_config.get('https_proxy'),
                                                username=client_config['username'],
                                                apikey=client_config['api_key'],
                                                org_uuids=client_config.get('org_uuids'))
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
        The schema ContrastSecurityAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Contrast URL',
                    'type': 'string',
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'api_key',
                    'title': 'Api Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'service_key',
                    'title': 'Service Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'org_uuids',
                    'title': 'Organization IDs',
                    'type': 'array',
                    'items': {'type': 'string'},
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
                'api_key',
                'service_key',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _parse_specific_fields(device, device_raw):
        device.contrast_server_id = device_raw.get('server_id')
        device.server_name = device_raw.get('name')
        device.server_type = device_raw.get('type')
        device.environment = device_raw.get('environment')
        device.container = device_raw.get('container')
        device.server_path = device_raw.get('path')
        device.server_status = device_raw.get('status')
        device.is_assess = device_raw.get('assess')
        device.assess_last_updated = parse_date(device_raw.get('assess_last_update'))
        device.asses_sensors_active = device_raw.get('assess_sensors')
        device.is_defend = device_raw.get('defend')
        device.is_defend_pending = device_raw.get('defendPending')
        device.defend_sensors_active = device_raw.get('defend_sensors')
        device.defend_last_updated = parse_date(device_raw.get('defense_last_updated'))
        device.agent_language = device_raw.get('language')
        device.agent_version = device_raw.get('agent_version')
        device.is_agent_out_of_date = device_raw.get('out_of_date')
        device.latest_available_agent_version = device_raw.get('latest_agent_version')

    @staticmethod
    def _parse_generic_fields(device, device_raw):
        device.name = device_raw.get('name')
        device.hostname = device_raw.get('hostname')
        device.boot_time = parse_date(device_raw.get('last_startup'))
        device.last_seen = parse_date(device_raw.get('last_activity'))

        agent_status = None
        if device_raw.get('out_of_date'):
            agent_status = 'Out of date'
            if device_raw.get('latest_agent_version'):
                agent_status += f', latest version: {device_raw.get("latest_agent_version")}'
        device.add_agent_version(agent=AGENT_NAMES.contrast,
                                 version=device_raw.get('agent_version'),
                                 status=agent_status)

    def _create_device(self, device_raw):
        try:
            org_uuid, device_raw = device_raw
            device = self._new_device_adapter()
            device_id = device_raw.get('server_id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = f'contrast_{device_id}'
            self._parse_generic_fields(device, device_raw)
            self._parse_specific_fields(device, device_raw)
            device.organization_uuid = org_uuid
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching ContrastSecurity Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        # AUTOADAPTER - check if you need to add other properties'
        return [AdapterProperty.Assets, AdapterProperty.Agent]
