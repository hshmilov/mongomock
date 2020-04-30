import logging
from urllib3.util.url import parse_url

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.files import get_local_config_file
from bigid_adapter.connection import BigidConnection
from bigid_adapter.client_id import get_client_id
from bigid_adapter.structures import BigidDeviceInstance, BigidField

logger = logging.getLogger(f'axonius.{__name__}')


class BigidAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(BigidDeviceInstance):
        pass

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
        connection = BigidConnection(domain=client_config['domain'],
                                     verify_ssl=client_config['verify_ssl'],
                                     https_proxy=client_config.get('https_proxy'),
                                     username=client_config['username'],
                                     password=client_config['password'])
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(e))
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
        The schema BigidAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'BigID Domain',
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

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    @staticmethod
    def _fill_bigid_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.open_access = device_raw.get('open_access')
            device.container_name = device_raw.get('containerName')
            device.object_type = device_raw.get('objectType')
            device.full_object_name = device_raw.get('fullObjectName')
            device.source = device_raw.get('source')
            device.scanner_type_group = device_raw.get('scanner_type_group')
            device.total_pii_count = device_raw.get('total_pii_count') \
                if isinstance(device_raw.get('total_pii_count'), int) else None
            device.attribute_list = device_raw.get('attribute') \
                if isinstance(device_raw.get('attribute'), list) else None
            extra_data = device_raw.get('extra_data')
            if extra_data and isinstance(extra_data, dict):
                if extra_data.get('records') and isinstance(extra_data.get('records'), list):
                    for record_raw in extra_data['records']:
                        if isinstance(record_raw, dict) and record_raw.get('data'):
                            if isinstance(record_raw.get('data'), list):
                                for field_raw in record_raw.get('data'):
                                    field_name = field_raw.get('fieldName')
                                    field_type = field_raw.get('fieldType')
                                    field_value = field_raw.get('fieldValue')
                                    if field_name in ['XXX']:
                                        device.hostname = parse_url(field_value).host
                                    device.full_fields.append(BigidField(field_name=field_name,
                                                                         field_value=field_value,
                                                                         field_type=field_type))

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('objectName') or '')
            device.name = device_raw.get('objectName')
            self._fill_bigid_device_fields(device_raw, device)

            device.set_raw(device_raw)

            return device
        except Exception:
            logger.exception(f'Problem with fetching Bigid Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching Bigid Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
