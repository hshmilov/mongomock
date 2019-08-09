import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.fields import Field
from code42_adapter.connection import Code42Connection
from code42_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class Code42Adapter(AdapterBase):
    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        product_version = Field(str, 'Product Version')
        device_service = Field(str, 'Device Service')
        java_version = Field(str, 'Java Version')
        device_status = Field(str, 'Device Status')
        device_type = Field(str, 'Device Type')
        user_id = Field(str, 'User ID')
        address = Field(str, 'Address')
        remote_address = Field(str, 'Remote Address')
        active_state = Field(bool, 'Active State')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def _connect_client(client_config):
        try:
            with Code42Connection(domain=client_config['domain'],
                                  verify_ssl=client_config['verify_ssl'],
                                  username=client_config['username'],
                                  password=client_config['password'],
                                  https_proxy=client_config.get('https_proxy')) as connection:
                return connection
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
        The schema Code42Adapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Code42 Domain',
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

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('guid')
                if not device_id:
                    logger.warning(f'Bad device with no guid {device_raw}')
                    continue
                device.id = device_id + '_' + (device_raw.get('name') or '')
                device.hostname = device_raw.get('name')
                try:
                    device.last_seen = parse_date(device_raw.get('lastConnected'))
                except Exception:
                    logger.exception(f'Problem getting last seen for {device_raw}')
                try:
                    device.figure_os((device_raw.get('osName') or '') + ' ' + (device_raw.get('osVersion') or ''))
                except Exception:
                    logger.exception(f'Problem getting os for {device_raw}')
                device.product_version = device_raw.get('productVersion')
                device.device_service = device_raw.get('service')
                device.java_version = device_raw.get('javaVersion')
                agent_version = str(device_raw.get('version')) if device_raw.get('version') else None
                device.add_agent_version(agent=AGENT_NAMES.code42, version=agent_version)
                device.device_status = device_raw.get('status')
                device.device_type = device_raw.get('type')
                device.user_id = str(device_raw.get('userId')) if device_raw.get('userId') else None
                device.address = device_raw.get('address')
                device.remote_address = device_raw.get('remoteAddress')
                device.active_state = device_raw.get('active')

                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Code42 Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
