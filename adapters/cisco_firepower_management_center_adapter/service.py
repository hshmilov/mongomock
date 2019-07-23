import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.smart_json_class import SmartJsonClass
from axonius.fields import Field, ListField
from cisco_firepower_management_center_adapter.connection import CiscoFirepowerManagementCenterConnection
from cisco_firepower_management_center_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class CiscoFMCHealthPolicy(SmartJsonClass):
    """
    A definition for a Cisco Firepower Management Center healthPolicy field
    """
    name = Field(str, 'Health Policy Name')
    id = Field(str, 'Health Policy ID')
    type = Field(str, 'Health Policy Type')


class CiscoFMCDeviceGroup(SmartJsonClass):
    """
    A definition for a Cisco Firepower Management Center deviceGroup field
    """
    name = Field(str, 'Device Group Name')
    description = Field(str, 'Device Group Description')
    id = Field(str, 'Device Group ID')
    type = Field(str, 'Device Group Type')
    version = Field(str, 'Device Group Version')


class CiscoFMCAccessPolicy(SmartJsonClass):
    """
    A definition for a Cisco Firepower Management Center accessPolicy field
    """
    name = Field(str, 'Access Policy Name')
    description = Field(str, 'Access Policy Description')
    type = Field(str, 'Access Policy Type')
    version = Field(str, 'Access Policy Version')
    last_user_name = Field(str, 'Access Policy Last User Name')
    last_user_id = Field(str, 'Access Policy Last User ID')
    last_user_type = Field(str, 'Access Policy Last User Type')
    domain_name = Field(str, 'Access Policy Domain Name')
    domain_id = Field(str, 'Access Policy Domain ID')
    domain_type = Field(str, 'Access Policy Domain Type')
    readonly_reason = Field(str, 'Access Policy Readonly Reason')
    readonly_state = Field(bool, 'Access Policy Readonly State')
    timestamp = Field(str, 'Access Policy Timestamp')


class CiscoFirepowerManagementCenterAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        fmc_model = Field(str, 'Model')
        fmc_model_number = Field(str, 'Model Number')
        fmc_model_id = Field(str, 'Model ID')
        fmc_model_type = Field(str, 'Model Type')
        fmc_type = Field(str, 'Type')
        fmc_version = Field(str, 'Version')
        fmc_sw_version = Field(str, 'Software Version')
        fmc_health_status = Field(str, 'Health Status')
        fmc_keep_local_events = Field(bool, 'Keep Local Events')
        fmc_prohibit_packet_transfer = Field(bool, 'Prohibit Packet Transfer')
        fmc_nat_id = Field(str, 'natID')
        fmc_reg_key = Field(str, 'regKey')
        fmc_license_caps = ListField(str, 'license_caps')
        health_policy = Field(CiscoFMCHealthPolicy, 'Health Policy')
        device_group = Field(CiscoFMCDeviceGroup, 'Device Group')
        access_policy = Field(CiscoFMCAccessPolicy, 'Access Policy')

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
        connection = CiscoFirepowerManagementCenterConnection(domain=client_config['domain'],
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
        The schema CiscoFirepowerManagementCenterAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Cisco Firepower Management Center Domain',
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

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('id') or '')
            device.name = device_raw.get('name')
            device.hostname = device_raw.get('hostName')
            device.description = device_raw.get('description')

            device.fmc_model = device_raw.get('model')
            device.fmc_model_number = device_raw.get('modelNumber')
            device.fmc_model_id = device_raw.get('modelId')
            device.fmc_model_type = device_raw.get('modelType')
            device.fmc_type = device_raw.get('type')
            device.fmc_version = device_raw.get('version')
            device.fmc_sw_version = device_raw.get('sw_version')
            device.fmc_health_status = device_raw.get('healthStatus')
            device.fmc_keep_local_events = bool(device_raw.get('keepLocalEvents'))
            device.fmc_prohibit_packet_transfer = bool(device_raw.get('prohibitPacketTransfer'))
            device.fmc_nat_id = device_raw.get('natID')
            device.fmc_reg_key = device_raw.get('regKey')
            device.fmc_license_caps = device_raw.get('license_caps')

            try:
                device.health_policy = CiscoFMCHealthPolicy(
                    name=device_raw.get('healthPolicy').get('name'),
                    id=device_raw.get('healthPolicy').get('id'),
                    type=device_raw.get('healthPolicy').get('type')
                ) if device_raw.get('healthPolicy') else None
            except BaseException:
                logger.exception(f'Problem with parsing CiscoFMCHealthPolicy for device: {device_raw}')

            try:
                device.device_group = CiscoFMCDeviceGroup(
                    name=device_raw.get('deviceGroup').get('name'),
                    description=device_raw.get('deviceGroup').get('description'),
                    id=device_raw.get('deviceGroup').get('id'),
                    type=device_raw.get('deviceGroup').get('type'),
                    version=device_raw.get('deviceGroup').get('version')
                ) if device_raw.get('deviceGroup') else None
            except BaseException:
                logger.exception(f'Problem with parsing CiscoFMCDeviceGroup for device: {device_raw}')

            try:
                device.access_policy = CiscoFMCAccessPolicy(
                    name=device_raw.get('accessPolicy').get('name'),
                    description=device_raw.get('accessPolicy').get('description'),
                    id=device_raw.get('accessPolicy').get('id'),
                    type=device_raw.get('accessPolicy').get('type'),
                    version=device_raw.get('accessPolicy').get('version'),
                    last_user_name=device_raw.get('accessPolicy').get('metadata').get('lastUser').get('name'),
                    last_user_id=device_raw.get('accessPolicy').get('metadata').get('lastUser').get('id'),
                    last_user_type=device_raw.get('accessPolicy').get('metadata').get('lastUser').get('type'),
                    domain_name=device_raw.get('accessPolicy').get('metadata').get('domain').get('name'),
                    domain_id=device_raw.get('accessPolicy').get('metadata').get('domain').get('id'),
                    domain_type=device_raw.get('accessPolicy').get('metadata').get('domain').get('type'),
                    readonly_reason=device_raw.get('accessPolicy').get('metadata').get('readOnly').get('reason'),
                    readonly_state=bool(device_raw.get('accessPolicy').get('metadata').get('readOnly').get('state')),
                    timestamp=device_raw.get('accessPolicy').get('metadata').get('timestamp')
                ) if device_raw.get('accessPolicy') else None
            except BaseException:
                logger.exception(f'Problem with parsing CiscoFMCAccessPolicy for device: {device_raw}')

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching CiscoFirepowerManagementCenter Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
