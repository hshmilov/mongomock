import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.fields import Field
from tanium_adapter import consts
from tanium_adapter.connection import TaniumConnection

logger = logging.getLogger(f'axonius.{__name__}')


class TaniumAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, 'Agent Version')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'), client_config.get('port'))

    def _connect_client(self, client_config):
        try:
            connection = TaniumConnection(domain=client_config['domain'],
                                          verify_ssl=client_config['verify_ssl'],
                                          username=client_config['username'],
                                          password=client_config['password'],
                                          port=(client_config.get('port') or consts.DEFAULT_TANIUM_PORT))
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Tanium domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Tanium connection

        :return: A json with all the attributes returned from the Tanium Server
        """
        with client_data:
            yield from client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema TaniumAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Tanium Domain',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'Port',
                    'type': 'integer',
                    'format': 'port'
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

    def _parse_raw_data(self, devices_raw_data):

        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('computer_id')
                if not device_id:
                    logger.warning(f'Bad device with no ID {device_raw}')
                device.id = device_id
                hostname = device_raw.get('host_name')
                if hostname and hostname.endswith('(none)'):
                    hostname = hostname[:-len('(none)')]
                device.hostname = hostname
                device.agent_version = device_raw.get('full_version')
                device.last_seen = parse_date(device_raw.get('last_registration'))
                ip_address = device_raw.get('ipaddress_client')
                if ip_address:
                    device.add_nic(None, ip_address.split(','))
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Tanium Device {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        """
        To be implemented by inheritors, otherwise leave empty.
        :type correlation_cmd_result: str
        :param correlation_cmd_result: result of running cmd on a machine
        :type os_type: str
        :param os_type: the type of machine ran upon
        :return:
        """
        raise NotImplementedError()
