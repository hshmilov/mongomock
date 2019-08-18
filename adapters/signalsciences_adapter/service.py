import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.utils.datetime import parse_date
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from signalsciences_adapter.connection import SignalsciencesConnection
from signalsciences_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class SignalsciencesAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        instance_type = Field(str, 'Instance Type')
        last_rule_update = Field(datetime.datetime, 'Last Rule Update')
        is_active = Field(bool, 'Is Active')

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
        connection = SignalsciencesConnection(domain=client_config['domain'],
                                              verify_ssl=client_config['verify_ssl'],
                                              https_proxy=client_config.get('https_proxy'),
                                              username=client_config['email'],
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
        The schema SignalsciencesAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Signalsciences Domain',
                    'type': 'string'
                },
                {
                    'name': 'email',
                    'title': 'Email',
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
                'email',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('agent.name')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id
            device.hostname = device_id
            device.last_seen = parse_date(device_raw.get('agent.last_seen'))
            device.add_agent_version(agent=AGENT_NAMES.signalsciences,
                                     version=device_raw.get('agent.version'),
                                     status=device_raw.get('agent.status'))
            device.figure_os(device_raw.get('host.os'))
            if isinstance(device_raw.get('host.remote_addr'), str):
                device.add_nic(ips=device_raw.get('host.remote_addr').split(','))
            device.instance_type = device_raw.get('host.instance_type')
            device.last_rule_update = device_raw.get('agent.last_rule_update')
            device.is_active = bool(device_raw.get('agent.active'))
            try:
                if isinstance(device_raw.get('agent.uptime'), int):
                    device.set_boot_time(uptime=datetime.timedelta(seconds=int(device_raw.get('agent.uptime'))))
            except Exception:
                logger.exception(f'Problem with boot time for {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Signalsciences Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
