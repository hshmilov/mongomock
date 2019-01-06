import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.adapter_exceptions import ClientConnectionException

logger = logging.getLogger(f'axonius.{__name__}')
MOCK_SERVER = 'http://mockingbird'
ENTITIES_PER_PAGE = 1000


class AdapterMockClient(RESTConnection):
    def __init__(self, plugin_name, client_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__plugin_name = plugin_name
        self.__client_id = client_id

    def _connect(self):
        return True

    def __get_entity_list(self, entity):
        def get_response(_offset):
            return self._get(
                entity,
                url_params={
                    'plugin_name': self.__plugin_name,
                    'client_id': self.__client_id,
                    'offset': _offset,
                    'limit': ENTITIES_PER_PAGE
                }
            )

        response = get_response(0)
        total_count = int(response['total_count'])
        yield from response['data']
        offset = ENTITIES_PER_PAGE

        while offset < total_count:
            response = get_response(offset)
            yield from response['data']
            offset += ENTITIES_PER_PAGE

    def get_device_list(self):
        yield from self.__get_entity_list('devices')

    def get_user_list(self):
        yield from self.__get_entity_list('users')


# pylint: disable=protected-access
class AdapterMock:
    """
    A mock for adapters that uses our mock infrastructure.
    """

    def __init__(self, adapter_base_object):
        # This could be an inheritance but i choose not to, because there is a risk someone will inherit a method from
        # AdapterBase, which could cause serious harm.

        self.__ab = adapter_base_object
        self.__number_of_clients = 0

    @staticmethod
    def mock_test_reachability():
        return RESTConnection.test_reachability(MOCK_SERVER)

    def mock_connect_client(self):
        client_id = f'client_{self.__number_of_clients}'
        self.__number_of_clients += 1

        try:
            return AdapterMockClient(
                self.__ab.plugin_name,
                client_id,
                domain=MOCK_SERVER,
                url_base_prefix='api',
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'},
            )
        except Exception as e:
            logger.error(f'Failed to connect to client {client_id}')
            raise ClientConnectionException(str(e))

    @staticmethod
    def mock_query_devices_by_client(client_name, client_data: AdapterMockClient):
        """
        Uses the mock infrastructure to query devices by client.
        """
        logger.info(f'Mock: querying devices of client {client_name}')
        with client_data:
            yield from client_data.get_device_list()

    def mock_parse_raw_data(self, devices_raw_data):
        """
        Uses the mock infrastructure to parse devices data.
        """
        try:
            self.__ab._new_device_adapter()
        except Exception:
            logger.exception(f'Exception: Mock: MyDeviceAdapter is not configured for {self.__ab.plugin_name}')
            return

        for device_raw in devices_raw_data:
            device = self.__ab._new_device_adapter()
            for key, value in device_raw.items():
                device._extend_names(key, value)
                device._dict = device_raw
            yield device

    @staticmethod
    def mock_query_users_by_client(client_name, client_data: AdapterMockClient):
        """
        Uses the mock infrastructure to query users by client.
        """
        logger.info(f'Mock: querying users of user {client_name}')
        with client_data:
            yield from client_data.get_user_list()

    def mock_parse_users_raw_data(self, users_raw_data):
        """
        Uses the mock infrastructure to parse devices data.
        """
        try:
            self.__ab._new_user_adapter()
        except Exception:
            logger.exception(f'Exception: Mock: MyUserAdapter is not configured for {self.__ab.plugin_name}')
            return

        for user_raw in users_raw_data:
            user = self.__ab._new_user_adapter()
            for key, value in user_raw.items():
                user._extend_names(key, value)
            user._dict = user_raw
            yield user
