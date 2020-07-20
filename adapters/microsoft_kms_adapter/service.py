import logging

from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.utils.datetime import parse_date
from axonius.mixins.configurable import Configurable
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.mssql.connection import MSSQLConnection
from axonius.adapter_exceptions import ClientConnectionException
from microsoft_kms_adapter import consts
from microsoft_kms_adapter.client_id import get_client_id
from microsoft_kms_adapter.structures import MicrosoftKmsDeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')


class MicrosoftKmsAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(MicrosoftKmsDeviceInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__))

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('server'),
                                                port=client_config.get('port'))

    def get_connection(self, client_config):
        connection = MSSQLConnection(database=client_config.get(consts.MICROSOFT_KMS_DATABASE),
                                     server=client_config[consts.MICROSOFT_KMS_HOST],
                                     port=client_config.get(consts.MICROSOFT_KMS_PORT,
                                                            consts.DEFAULT_MICROSOFT_KMS_PORT),
                                     devices_paging=self.__devices_fetched_at_a_time)
        connection.set_credentials(username=client_config[consts.USER],
                                   password=client_config[consts.PASSWORD])
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except Exception:
            message = f'Error connecting to client host: {client_config[consts.MICROSOFT_KMS_HOST]}  ' \
                      f'database: ' \
                      f'{client_config.get(consts.MICROSOFT_KMS_DATABASE)}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string())

    def _query_devices_by_client(self, client_name, client_data: MSSQLConnection):
        """
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        client_data.set_devices_paging(self.__devices_fetched_at_a_time)
        with client_data:
            yield from client_data.query(consts.MICROSOFT_KMS_QUERY)

    def _clients_schema(self):
        """
        The schema MicrosoftKmsAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': consts.MICROSOFT_KMS_HOST,
                    'title': 'MSSQL Server',
                    'type': 'string'
                },
                {
                    'name': consts.MICROSOFT_KMS_PORT,
                    'title': 'Port',
                    'type': 'integer',
                    'default': consts.DEFAULT_MICROSOFT_KMS_PORT,
                    'format': 'port'
                },
                {
                    'name': consts.MICROSOFT_KMS_DATABASE,
                    'title': 'Database',
                    'type': 'string'
                },
                {
                    'name': consts.USER,
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': consts.PASSWORD,
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                consts.MICROSOFT_KMS_HOST,
                consts.USER,
                consts.PASSWORD,
                consts.MICROSOFT_KMS_DATABASE
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_microsoft_kms_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.product_version = device_raw.get('ProductVersion')
            device.last_updated = parse_date(device_raw.get('LastUpdated'))
            device.last_action_status = device_raw.get('LastActionStatus')
            device.product_name = device_raw.get('ProductName')
            device.sku = device_raw.get('Sku')
            device.application_id = device_raw.get('ApplicationId')
            device.product_key_id = device_raw.get('ProductKeyId')
            device.product_description = device_raw.get('ProductDescription')
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('FullyQualifiedDomainName')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id
            device.hostname = device_id

            self._fill_microsoft_kms_device_fields(device_raw, device)

            device.set_raw(device_raw)

            return device
        except Exception:
            logger.exception(f'Problem with fetching MicrosoftKms Device for {device_raw}')
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
                logger.exception(f'Problem with fetching MicrosoftKms Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Manager]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'devices_fetched_at_a_time',
                    'type': 'integer',
                    'title': 'SQL pagination'
                }
            ],
            'required': ['devices_fetched_at_a_time'],
            'pretty_name': 'Microsoft KMS Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'devices_fetched_at_a_time': 1000
        }

    def _on_config_update(self, config):
        self.__devices_fetched_at_a_time = config['devices_fetched_at_a_time']
