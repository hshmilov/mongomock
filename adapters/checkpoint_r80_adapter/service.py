import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from checkpoint_r80_adapter.connection import CheckpointR80Connection
from checkpoint_r80_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class CheckpointR80Adapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        cp_type = Field(str, 'CheckPoint Device Type')
        cp_domain = Field(str, 'CheckPoint Domain')

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
            with CheckpointR80Connection(domain=client_config['domain'],
                                         verify_ssl=client_config['verify_ssl'],
                                         username=client_config['username'],
                                         password=client_config['password'],
                                         cp_domain=client_config.get('cp_domain')) as connection:
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
        The schema CheckpointR80Adapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'CheckpointR80 Host URL',
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
                    'name': 'cp_domain',
                    'title': 'CheckPoint Domain',
                    'type': 'string'
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
                device_id = device_raw.get('uid')
                if not device_id:
                    logger.warning(f'Bad device with not ID {device_raw}')
                    continue
                device.id = device_id + '_' + (device_raw.get('name') or '')
                device.name = device_raw.get('name')
                device.cp_type = device_raw.get('type')
                try:
                    ips = [device_raw.get('ipv4-address')] if device_raw.get('ipv4-address') else None
                    ips6 = [device_raw.get('ipv4-address')] if device_raw.get('ipv4-address') else None
                    if ips and ips6:
                        ips.extend(ips6)
                    elif ips or ips6:
                        ips = ips or ips6
                    if ips:
                        device.add_nic(None, ips)
                except Exception:
                    logger.exception(f'Problem adding nic to {device_raw}')
                try:
                    domain = device_raw.get('domain')
                    if domain and isinstance(domain, dict):
                        device.cp_domain = domain.get('name')
                except Exception:
                    logger.exception(f'Problem getting domain to {device_raw}')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching CheckpointR80 Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
