import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from snipeit_adapter.connection import SnipeitConnection
from snipeit_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class SnipeitAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        asset_tag = Field(str, 'Asset Tag')
        status_label = Field(str, 'Status Label')

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
            with SnipeitConnection(domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                                   apikey=client_config['apikey'],
                                   ) as connection:
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
        The schema SnipeitAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Snipeit Domain',
                    'type': 'string'
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
                'apikey',
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
                    logger.warning(f'Bad device with no ID {device_raw}')
                    continue
                device.id = device_id + '_' + (device_raw.get('name') or '') + '_' + (device_raw.get('serial') or '')
                name = device_raw.get('name')
                if name:
                    device.name = name
                device_serial = device_raw.get('serial')
                if device_serial:
                    device.device_serial = device_serial
                device.asset_tag = device_raw.get('asset_tag')
                try:
                    device.device_model = (device_raw.get('model') or {}).get('name')
                except Exception:
                    logger.exception(f'Problem getting model for {device_raw}')
                try:
                    device.status_label = (device_raw.get('status_label') or {}).get('name')
                except Exception:
                    logger.exception(f'Problem getting status label for {device_raw}')
                try:
                    device.category = (device_raw.get('category') or {}).get('name')
                except Exception:
                    logger.exception(f'Problem getting category for {device_raw}')
                try:
                    device.device_manufacturer = (device_raw.get('manufacturer') or {}).get('name')
                except Exception:
                    logger.exception(f'Problem getting manufacturer for {device_raw}')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Snipeit Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
