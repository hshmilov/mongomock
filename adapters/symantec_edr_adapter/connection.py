import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from symantec_edr_adapter.consts import DEVICES_URL, MAX_NUMBER_OF_DEVICES, TOKEN_GRANT_TYPE, TOKEN_URL, \
    DEVICE_PER_PAGE, ENTITIES_RELEASE_URL, RESOURCE_TTL, QUERY_VERB, WHITE_SPACE

logger = logging.getLogger(f'axonius.{__name__}')


class SymantecEdrConnection(RESTConnection):
    """ rest client for SymantecEdr adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._token = WHITE_SPACE

    def _get_access_token(self):
        """
        Aquire access token from the server to be used in REST communications.
        :return: Access Token
        """

        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        request_body = f'grant_type={TOKEN_GRANT_TYPE}'

        response = self._post(TOKEN_URL,
                              do_basic_auth=True,
                              use_json_in_body=False,
                              extra_headers=headers,
                              body_params=request_body
                              )

        if not isinstance(response, dict):
            raise Exception('Incorrect response while trying to acquire access token!')

        self._token = response.get('access_token')

        if not self._token:
            raise Exception('Empty access token acquired!')

        logger.info('Access token acquired properly.')

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No API credentials.')

        try:
            self._get_access_token()
            self._session_headers['Authorization'] = f'Bearer {self._token}'

            request_body = {'verb': QUERY_VERB, 'limit': 1}  # Fetch one device only for connectivity testing purpose.
            devices_response = self._post(DEVICES_URL, body_params=request_body)

            if not (devices_response and
                    isinstance(devices_response, dict) and
                    isinstance(devices_response.get('result'), list)):
                raise Exception(f'Invalid response received! , {str(devices_response)}')

            if not devices_response.get('result'):
                raise ValueError(f'No result returned')

        except Exception as exception:
            raise ValueError(
                f'Error while connecting to Symantec EDR: '
                f'Invalid response from server, please check domain or credentials. {str(exception)}')

    def _paginated_device_get(self):
        try:
            # This request is only for getting devices total count.
            request_body = {'verb': QUERY_VERB, 'limit': 1}
            response = self._post(DEVICES_URL, body_params=request_body)

            if not response or not isinstance(response, dict):
                raise RESTException(f'Invalid response while trying to get paginated devices: {response}')

            count_total_results = response.get('total')  # Count of all entities.
            count_fetched_results = 0  # How many devices we already fetched.

            if not str(count_total_results).isnumeric():
                raise ValueError(f'Total count of devices is not a number! {count_total_results}')

            if count_total_results == 0:
                return []

            # Max amount of devices we want to fetch.
            max_count = min(count_total_results, MAX_NUMBER_OF_DEVICES)
            next_resource = WHITE_SPACE     # Initialized with empty string to indicate first request.
            request_body = {
                'verb': QUERY_VERB,
                'limit': DEVICE_PER_PAGE,
                'keep_alive_secs': RESOURCE_TTL
            }

            while count_fetched_results < max_count and next_resource:
                if next_resource != WHITE_SPACE:
                    request_body['next'] = next_resource

                response = self._post(DEVICES_URL, body_params=request_body)

                if not isinstance(response, dict) and not isinstance(response.get('result'), list):
                    raise RESTException(f'Invalid response: {response}')

                count_fetched_results += len(response.get('result'))

                # Release last fetched resource
                if next_resource and next_resource != WHITE_SPACE:
                    try:
                        self._delete(f'{ENTITIES_RELEASE_URL}/{next_resource}')
                    except Exception:
                        logger.exception(f'Could not release resource: {next_resource}')

                next_resource = response.get('next')
                yield from response.get('result')
        except Exception:
            logger.exception(f'Invalid request made while paginating devices.')
            raise

    def get_device_list(self):
        try:
            yield from self._paginated_device_get()
        except RESTException as err:
            logger.exception(f'Error occurred while trying to get device list: {str(err)}')
            raise
