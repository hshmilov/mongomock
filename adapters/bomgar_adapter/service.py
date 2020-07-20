import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file

from bomgar_adapter.client import BomgarConnection
from bomgar_adapter.exceptions import BomgarException

logger = logging.getLogger(f'axonius.{__name__}')


class BomgarAdapter(AdapterBase):

    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        device_type = Field(str, 'Bomgar Device Type')
        public_display_name = Field(str, 'Bomgar public display name')
        user_id = Field(int, 'Bomgar User ID')
        username = Field(str, 'Bomgar User Name')
        created_timestamp = Field(datetime.datetime, 'Created Timestamp')
        last_session_representative_username = Field(str, 'Bomgar Last Session Representative User Name')
        last_session_start = Field(datetime.datetime, 'Last Session Start Timestamp')
        last_session_start_method = Field(str, 'Last Session Start Method')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain'] + ':' + client_config['client_id']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _connect_client(self, client_config):
        try:
            connection = BomgarConnection(client_config['domain'], client_config['client_id'],
                                          client_config['client_secret'],
                                          https_proxy=client_config.get('https_proxy'),
                                          proxy_username=client_config.get('proxy_username'),
                                          proxy_password=client_config.get('proxy_password'),
                                          )
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except BomgarException as e:
            message = f'Error connecting to client {self._get_client_id(client_config)}, reason: {str(e)}'
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        assert isinstance(client_data, BomgarConnection)
        with client_data:
            return client_data.get_clients_history()

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Domain',
                    'type': 'string'
                },
                {
                    'name': 'client_id',
                    'title': 'Client ID',
                    'type': 'string'
                },
                {
                    'name': 'client_secret',
                    'title': 'Client Secret',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
                {
                    'name': 'proxy_username',
                    'title': 'HTTPS Proxy User Name',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS Proxy Password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                'domain',
                'client_id',
                'client_secret'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for hostname, device_raw in devices_raw_data.items():
            try:
                device = self._new_device_adapter()
                device.hostname = device_raw.get('hostname')
                device_id = device_raw.get('hostname')
                if not device_id:
                    logger.warning('Hostname was empty or None')
                    continue
                device.id = device_id
                device.figure_os(device_raw.get('operating_system'))
                try:
                    device.created_timestamp = datetime.datetime.fromtimestamp(int(device_raw.get('created_timestamp')))
                except Exception:
                    logger.exception(f'The device {device_raw} did not have a timestamp')
                device.device_type = device_raw.get('device_type')
                try:
                    device.last_seen = datetime.datetime.fromtimestamp(int(device_raw.get('last_seen')))
                except Exception:
                    logger.exception(f'The device {device_raw} did not have a last seen timestamp')

                if device_raw.get('device_type') == 'representative':
                    device.public_display_name = device_raw.get('public_display_name')
                    device.user_id = device_raw.get('user_id')
                    device.username = device_raw.get('username')
                else:
                    try:
                        # pylint: disable=C0103
                        device.last_session_representative_username = device_raw.get(
                            'last_session_representative_username')
                        if device_raw.get('last_session_start'):
                            device.last_session_start = datetime.datetime.fromtimestamp(
                                int(device_raw.get('last_session_start')))
                        device.last_session_start_method = device_raw.get('last_session_start_method')
                    except Exception:
                        logger.exception(f'Problem at adding start time for {device_raw}')

                possible_private_ip = device_raw.get('private_ip')
                if possible_private_ip and possible_private_ip != 'localhost':
                    device.add_nic(None, [possible_private_ip])

                possible_public_ip = device_raw.get('public_ip')
                if possible_public_ip and possible_public_ip != 'localhost':
                    device.add_nic(None, [possible_public_ip])
                    device.add_public_ip(possible_public_ip)

                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with device {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
