import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES, DeviceRunningState
from axonius.fields import Field, ListField
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from guardicore_adapter.connection import GuardicoreConnection
from guardicore_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class GuardicoreAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        risk_level = Field(int, 'Risk Level')
        full_name = Field(str, 'Full Name')
        comments = Field(str, 'Comments')
        is_active = Field(bool, 'Is Active')
        supported_features = ListField(str, 'Supported Features')

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
        connection = GuardicoreConnection(domain=client_config['domain'],
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
        The schema GuardicoreAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Guardicore Domain',
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
            device.id = device_id + '_' + (device_raw.get('name') or '')
            device.name = device_raw.get('name')
            device.uuid = device_raw.get('hw_uuid')
            is_on = device_raw.get('is_on')
            device.power_state = {
                True: DeviceRunningState.TurnedOn,
                False: DeviceRunningState.TurnedOff
            }.get(is_on)
            device.last_seen = parse_date(device_raw.get('last_seen'))
            device.risk_level = device_raw.get('risk_level') if isinstance(device_raw.get('risk_level'), int) else None
            nics = device_raw.get('nics')
            if not isinstance(nics, list):
                nics = []
            for nic_raw in nics:
                try:
                    ips = nic_raw.get('ip_addresses')
                    if not ips or not isinstance(ips, list):
                        ips = None
                    mac = nic_raw.get('mac_address')
                    if not mac:
                        mac = None
                    if mac or ips:
                        device.add_nic(mac=mac, ips=ips, name=nic_raw.get('network_name'))
                except Exception:
                    logger.exception(f'Problem with nic {nic_raw}')
            device.first_seen = parse_date(device_raw.get('first_seen'))
            device.full_name = device_raw.get('full_name')
            device.comments = device_raw.get('comments')
            device.is_active = device_raw.get('active')

            guest_agent_details = device_raw.get('guest_agent_details')
            if not isinstance(guest_agent_details, dict):
                guest_agent_details = {}
            device.hostname = guest_agent_details.get('hostname')
            device.figure_os((guest_agent_details.get('os_details') or {}).get('os_version_name'))
            if isinstance(guest_agent_details.get('supported_features'), list):
                device.supported_features = guest_agent_details.get('supported_features')
            device.add_agent_version(agent=AGENT_NAMES.guardicore,
                                     version=guest_agent_details.get('agent_version'))
            agent_hw = guest_agent_details.get('hardware')
            if not isinstance(agent_hw, dict):
                agent_hw = {}
            device.device_serial = agent_hw.get('serial')
            device.device_manufacturer = agent_hw.get('vendor')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Guardicore Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
