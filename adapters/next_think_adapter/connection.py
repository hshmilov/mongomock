import logging
from collections import defaultdict

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from next_think_adapter.consts import URL_API_PREFIX, QUERY_API_PREFIX, EXTRA_APPLICATIONS, EXTRA_SERVICES, \
    DEVICE_TABLE, USER_TABLE, MAX_NUMBER_OF_DEVICES, MAX_NUMBER_OF_USERS

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
                'format': 'json',
                'hr': False
            }
            self._get(QUERY_API_PREFIX, url_params=url_params, do_basic_auth=True)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _get_unique_table_id_to_device(self, object_name: str):
        """ Mapping between object_id key to device_id value (may be many to one) """
        try:
            unique_table_id_to_device_id = {}

            # Create unique tuples of device_id and object_id
            # Query example of unique tuples under "Selecting two objects" in the link below
            # https://doc.nexthink.com/Documentation/Nexthink/latest/APIAndIntegrations/NXQLlanguagedefinition
            query = f'(select (({DEVICE_TABLE} (id)) ({object_name} (id))) ' \
                    f'(from ({DEVICE_TABLE} {object_name}) (between midnight-1d now)))'
            url_params = {
                'query': query,
                'format': 'json',
                'hr': False
            }
            response = self._get(QUERY_API_PREFIX, url_params=url_params, do_basic_auth=True)
            if not isinstance(response, list):
                logger.warning(f'Received invalid response while getting unique {object_name} ids {response}')
                return {}

            for result in response:
                if not isinstance(result, dict):
                    logger.warning(f'Received invalid response while iterating results {response}')
                    return {}
                device_id = result.get(DEVICE_TABLE).get('id')
                unique_table_id = result.get(object_name).get('id')
                unique_table_id_to_device_id[unique_table_id] = device_id

            for day_number in range(1, self._last_fetch_data):
                query = f'(select (({DEVICE_TABLE} (id)) ({object_name} (id))) ' \
                        f'(from ({DEVICE_TABLE} {object_name}) ' \
                        f'(between midnight-{day_number + 1}d midnight-{day_number}d)))'
                url_params = {
                    'query': query,
                    'format': 'json',
                    'hr': False
                }
                response = self._get(QUERY_API_PREFIX, url_params=url_params, do_basic_auth=True)
                if not isinstance(response, list):
                    logger.warning(f'Received invalid response while getting unique {object_name} ids {response}')
                    return unique_table_id_to_device_id

                for result in response:
                    if not isinstance(result, dict):
                        logger.warning(f'Received invalid response while paginating {object_name} results {response}')
                        return {}
                    device_id = result.get(DEVICE_TABLE).get('id')
                    unique_table_id = result.get(object_name).get('id')
                    unique_table_id_to_device_id[unique_table_id] = device_id

            return unique_table_id_to_device_id
        except Exception as e:
            logger.warning(f'Failed fetching applications {str(e)}')
            return {}

    def _get_object_ordered_by_device_id(self, object_name: str):
        try:
            device_id_to_objects = defaultdict(list)
            object_id_to_device = self._get_unique_table_id_to_device(object_name)

            url_params = {
                'query': f'(select (*) (from {object_name} (between midnight-1d now)))',
                'format': 'json',
                'hr': False
            }
            response = self._get(QUERY_API_PREFIX, url_params=url_params, do_basic_auth=True)
            if not isinstance(response, list):
                logger.warning(f'Received invalid response while getting {object_name}. {response}')
                return {}

            for single_object in response:
                if not isinstance(single_object, dict):
                    logger.warning(f'Received invalid response while iterating {object_name} {response}')
                    return {}
                device_id = object_id_to_device.get(single_object.get('id'))
                if device_id:
                    device_id_to_objects[device_id].append(single_object)

            for day_number in range(1, self._last_fetch_data):
                query = f'(select (*) (from {object_name} (between midnight-{day_number + 1}d midnight-{day_number}d)))'
                url_params = {
                    'query': query,
                    'format': 'json',
                    'hr': False
                }
                response = self._get(QUERY_API_PREFIX, url_params=url_params, do_basic_auth=True)
                if not isinstance(response, list):
                    logger.warning(f'Received invalid response while getting {object_name} {response}')
                    return device_id_to_objects

                for single_object in response:
                    if not isinstance(single_object, dict):
                        logger.warning(f'Received invalid response while paginating {object_name} {response}')
                        return device_id_to_objects
                    device_id = object_id_to_device.get(single_object.get('id'))
                    if device_id:
                        device_id_to_objects[device_id].append(single_object)

            return device_id_to_objects
        except Exception as e:
            logger.warning(f'Failed getting {object_name}. {str(e)}')
            return {}

    def _paginated_device_get(self):
        applications = self._get_object_ordered_by_device_id('application')
        services = self._get_object_ordered_by_device_id('service')

        try:
            total_fetched_devices = 0
            url_params = {
                'query': f'(select (*) (from {DEVICE_TABLE} (between midnight-1d now)))',
                'format': 'json',
                'hr': False
            }
            response = self._get(QUERY_API_PREFIX, url_params=url_params, do_basic_auth=True)
            if not isinstance(response, list):
                logger.warning(f'Received invalid response while getting devices {response}')
                return

            for device in response:
                if isinstance(device, dict) and device.get('id'):
                    device[EXTRA_APPLICATIONS] = applications.get(device.get('id'))
                    device[EXTRA_SERVICES] = services.get(device.get('id'))
                yield device
                total_fetched_devices += 1

                if total_fetched_devices >= MAX_NUMBER_OF_DEVICES:
                    return

            for day_number in range(1, self._last_fetch_data):
                url_params = {
                    'query': f'(select (*) (from {DEVICE_TABLE} '
                             f'(between midnight-{day_number + 1}d midnight-{day_number}d)))',
                    'format': 'json',
                    'hr': False
                }
                response = self._get(QUERY_API_PREFIX, url_params=url_params, do_basic_auth=True)
                if not isinstance(response, list):
                    logger.warning(f'Received invalid response while getting devices {response}')
                    break

                for device in response:
                    if isinstance(device, dict) and device.get('id'):
                        device[EXTRA_APPLICATIONS] = applications.get(device.get('id'))
                        device[EXTRA_SERVICES] = services.get(device.get('id'))
                    yield device
                    total_fetched_devices += 1

                    if total_fetched_devices >= MAX_NUMBER_OF_DEVICES:
                        return

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
                'query': f'(select (*) (from {USER_TABLE} (between midnight-1d now)))',
                'format': 'json',
                'hr': False
            }
            response = self._get(QUERY_API_PREFIX, url_params=url_params, do_basic_auth=True)
            if not isinstance(response, list):
                logger.warning(f'Received invalid response while getting users {response}')
                return

            for user in response:
                yield user
                total_fetched_users += 1

                if total_fetched_users >= MAX_NUMBER_OF_USERS:
                    return

            for day_number in range(1, self._last_fetch_data):
                url_params = {
                    'query': f'(select (*) (from {USER_TABLE} '
                             f'(between midnight-{day_number + 1}d midnight-{day_number}d)))',
                    'format': 'json',
                    'hr': False
                }
                response = self._get(QUERY_API_PREFIX, url_params=url_params, do_basic_auth=True)
                if not isinstance(response, list):
                    logger.warning(f'Received invalid response while getting users {response}')
                    break

                for user in response:
                    yield user
                    total_fetched_users += 1

                    if total_fetched_users >= MAX_NUMBER_OF_USERS:
                        return

        except Exception:
            logger.exception(f'Invalid request made while paginating users')
            raise

    def get_user_list(self):
        try:
            yield from self._paginated_user_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
