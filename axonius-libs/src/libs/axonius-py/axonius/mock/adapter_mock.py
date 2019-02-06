import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.adapter_exceptions import ClientConnectionException
from axonius.utils.parsing import parse_date

logger = logging.getLogger(f'axonius.{__name__}')
MOCK_SERVER = 'https://mockingbird'
ENTITIES_PER_PAGE = 1000


class AdapterMockClient(RESTConnection):
    def __init__(self, plugin_name, client_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__plugin_name = plugin_name
        self.__client_id = client_id

    def _connect(self):
        return True

    def __get_entity_list(self, entity):
        response = self._get(
            entity,
            url_params={
                'plugin_name': self.__plugin_name,
                'client_id': self.__client_id,
                'offset': 0,
                'limit': ENTITIES_PER_PAGE
            }
        )
        total_count = int(response['total_count'])
        yield from response['data']
        offset = ENTITIES_PER_PAGE

        # Now use asyncio to get all of these requests
        async_requests = []
        while offset < total_count:
            async_requests.append({
                'name':
                    f'{entity}?plugin_name={self.__plugin_name}&'
                    f'client_id={self.__client_id}&offset={offset}&limit={ENTITIES_PER_PAGE}'
            })
            offset += ENTITIES_PER_PAGE

        for response in self._async_get_only_good_response(async_requests):
            try:
                yield from response['data']
            except Exception:
                logger.exception(f'Problem getting async response {str(response)}')

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

    def transform_dates_to_datetime(self, raw):
        """
        REST API returns json output, which can not represent objects like datetime, it can only represent primitive
        types. The only non-primitive type we have is datetime, which will always be returned as a human-readable string
        from the server, e.g. "Fri, 28 Dec 2018 17:46:50 GMT". We try, very inefficiently, to identify those.

        If we would have a format of the data returned in addition (a think which is possible with some more
        development) we could do this but currently MyDeviceAdapter of adapters who include a datetime field will not
        be recognized.
        :param raw:
        :return:
        """
        if isinstance(raw, dict):
            for key, value in raw.items():
                raw[key] = self.transform_dates_to_datetime(value)
        elif isinstance(raw, list):
            for i, val in enumerate(raw):
                raw[i] = self.transform_dates_to_datetime(val)
        else:
            try:
                # Big hack, read the method intro.
                if isinstance(raw, str) and \
                        any(raw.lower().startswith(day) for day in ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']):
                    new_value = parse_date(raw)
                    if new_value:
                        return new_value
            except Exception:
                pass

        return raw

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
        for device_raw in devices_raw_data:
            device = self.__ab._new_device_adapter()
            device_raw = self.transform_dates_to_datetime(device_raw)
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
        for user_raw in users_raw_data:
            user = self.__ab._new_user_adapter()
            user_raw = self.transform_dates_to_datetime(user_raw)
            for key, value in user_raw.items():
                user._extend_names(key, value)
            user._dict = user_raw
            yield user
