import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from next_think_adapter.consts import URL_API_PREFIX, QUERY_API_PREFIX, \
    DEVICE_TABLE, USER_TABLE, MAX_NUMBER_OF_DEVICES, MAX_NUMBER_OF_USERS, DEVICE_PER_PAGE, USER_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class NextThinkConnection(RESTConnection):
    """ rest client for NextThink adapter """

    def __init__(self, *args, last_fetch_data: int, **kwargs):
        super().__init__(*args, url_base_prefix=URL_API_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

        self._last_fetch_data = last_fetch_data

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        try:
            url_params = {
                'query': f'(select (name) (from {DEVICE_TABLE}) (limit 1))',
                'format': 'json'
            }
            self._get(QUERY_API_PREFIX, url_params=url_params, do_basic_auth=True)

        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _paginated_device_get(self):
        try:
            total_fetched_devices = 0

            url_params = {
                'query': f'(select (*) (from {DEVICE_TABLE}) (limit {DEVICE_PER_PAGE}) (order_by name asc))',
                'format': 'json'
            }
            response = self._get(QUERY_API_PREFIX, url_params=url_params, do_basic_auth=True)
            if not isinstance(response, list):
                logger.warning(f'Received invalid response while getting devices {response}')
                return

            for device in response:
                if isinstance(device, dict) and device.get('id') and device.get('name'):
                    yield device
                    total_fetched_devices += 1
                    last_name = device.get('name')

            while len(response) == DEVICE_PER_PAGE:
                if not last_name:
                    logger.warning(f'Received invalid device with no name')
                    return
                url_params = {
                    'query': f'(select (*) (from {DEVICE_TABLE} '
                             f'(where {DEVICE_TABLE} (gt name (string "{last_name}"))))'
                             f' (limit {DEVICE_PER_PAGE}) (order_by name asc))',
                    'format': 'json'
                }

                response = self._get(QUERY_API_PREFIX, url_params=url_params, do_basic_auth=True)
                if not isinstance(response, list):
                    logger.warning(f'Received invalid response while paginating devices {response}')
                    return

                for device in response:
                    if isinstance(device, dict) and device.get('id') and device.get('name'):
                        yield device
                        total_fetched_devices += 1
                        last_name = device.get('name')

                if total_fetched_devices >= MAX_NUMBER_OF_DEVICES:
                    break

            logger.info(f'Got total of {total_fetched_devices} devices')
        except Exception:
            logger.exception(f'Invalid request made while paginating devices')
            raise

    def get_device_list(self):
        try:
            yield from self._paginated_device_get()
        except RESTException as err:
            logger.exception(str(err))
            raise

    def _paginated_user_get(self):
        try:
            total_fetched_users = 0

            url_params = {
                'query': f'(select (*) (from {USER_TABLE}) (limit {USER_PER_PAGE}) (order_by name asc))',
                'format': 'json'
            }
            response = self._get(QUERY_API_PREFIX, url_params=url_params, do_basic_auth=True)
            if not isinstance(response, list):
                logger.warning(f'Received invalid response while getting users {response}')
                return

            for user in response:
                if isinstance(user, dict) and user.get('id') and user.get('name'):
                    yield user
                    total_fetched_users += 1
                    last_name = user.get('name')

            while len(response) == USER_PER_PAGE:
                if not last_name:
                    logger.warning(f'Received invalid user with no name')
                    return
                url_params = {
                    'query': f'(select (*) (from {USER_TABLE} '
                             f'(where {USER_TABLE} (gt name (string "{last_name}"))))'
                             f' (limit {USER_PER_PAGE}) (order_by name asc))',
                    'format': 'json'
                }

                response = self._get(QUERY_API_PREFIX, url_params=url_params, do_basic_auth=True)
                if not isinstance(response, list):
                    logger.warning(f'Received invalid response while paginating users {response}')
                    return

                for user in response:
                    if isinstance(user, dict) and user.get('id') and user.get('name'):
                        yield user
                        total_fetched_users += 1
                        last_name = user.get('name')

                if total_fetched_users >= MAX_NUMBER_OF_USERS:
                    break

            logger.info(f'Got total of {total_fetched_users} users')
        except Exception:
            logger.exception(f'Invalid request made while paginating users')
            raise

    def get_user_list(self):
        try:
            yield from self._paginated_user_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
