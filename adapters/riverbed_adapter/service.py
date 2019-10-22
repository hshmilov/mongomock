import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from riverbed_adapter.connection import RiverbedConnection
from riverbed_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class RiverbedAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        health = Field(str, 'Health')
        address = Field(str, 'Address')
        device_version = Field(str, 'Device version')

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
            with RiverbedConnection(domain=client_config['domain'],
                                    verify_ssl=client_config['verify_ssl'],
                                    username=client_config.get('username'),
                                    password=client_config.get('password'),
                                    apikey=client_config.get('apikey')) as connection:
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
        The schema RiverbedAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Riverbed Domain',
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
                    'name': 'apikey',
                    'title': 'API Key',
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
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('id')
                if not device_id:
                    logger.warning(f'Bad device with no id {device_raw}')
                    continue
                device.id = device_id + '_' + (device_raw.get('uuid') or '') + '_' + (device_raw.get('serial') or '')
                device.uuid = device_raw.get('uuid')
                device.device_serial = device_raw.get('serial')
                device.device_model = device_raw.get('model')
                device.device_version = device_raw.get('version')
                device.hostname = device_raw.get('hostname')
                device.address = device_raw.get('address')
                device.health = device_raw.get('health')
                try:
                    if isinstance(device_raw.get('interfaces'), list):
                        ips = [nic.get('ip_addr') for nic in device_raw.get('interfaces') if nic.get('ip_addr')]
                        if ips:
                            device.add_nic(None, ips)
                except Exception:
                    logger.exception(f'Problem adding nic to {device_raw}')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Riverbed Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
