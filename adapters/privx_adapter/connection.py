import logging
from base64 import b64encode

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

from privx_adapter.consts import TOKEN_GRANT_TYPE, TOKEN_URL, DEVICES_URL, MAX_NUMBER_OF_DEVICES, \
    ENTITIES_PER_PAGE, USERS_URL

logger = logging.getLogger(f'axonius.{__name__}')


class PrivxConnection(RESTConnection):
    """ REST client for Privx adapter """

    def __init__(self, oauth_client_id, oauth_client_secret, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

        self._oauth_client_id = oauth_client_id
        self._oauth_client_secret = oauth_client_secret
        self._token = ''

    def _get_access_token(self):
        """
        Aquire access token from the server to be used in REST communications.
        :return: Access Token
        """

        # We use manual basic authentication instead of (do_basic_auth=True)
        # because we want to encode the credentials in base64 and make it compliant with PrivX requirements.

        basic_auth = b64encode(f'{self._oauth_client_id}:{self._oauth_client_secret}'
                               .encode('utf-8'))

        headers = {
            'Content-type': 'application/x-www-form-urlencoded',
            'Authorization': 'Basic {}'.format(basic_auth.decode('utf-8'))
        }

        # Request body should be in this specific format as a single line.
        request_body = f'grant_type={TOKEN_GRANT_TYPE}' \
                       f'&username={self._username}' \
                       f'&password={self._password}'

        response = self._post(TOKEN_URL,
                              do_basic_auth=False,
                              use_json_in_body=False,
                              extra_headers=headers,
                              body_params=request_body
                              )

        if not isinstance(response, dict):
            raise Exception('Incorrect response while trying to acquire access token!')

        self._token = response.get('access_token')
        logger.info('Access token acquired properly.')

    def _connect(self):
        if not all((self._username, self._password, self._oauth_client_id, self._oauth_client_secret)):
            raise RESTException('No API or oAuth credentials.')

        try:
            self._get_access_token()
            self._session_headers['Authorization'] = f'Bearer {self._token}'

            devices_response = self._get(DEVICES_URL)

            for _ in devices_response.get('items'):
                break

        except Exception as exception:
            raise ValueError(
                f'Error while connecting to PrivX: '
                f'Invalid response from server, please check domain or credentials. {str(exception)}')

    def _paginated_get(self, url):
        try:
            url_params = {
                'offset': 0,
                'limit': 1
            }
            # This request is only for getting the total devices count.
            response = self._get(url, url_params=url_params)

            if not response or not isinstance(response, dict):
                raise RESTException(f'Invalid response for url: {url}')

            count_total_results = response.get('count')  # Count of all entities.

            if count_total_results == 0:
                return []

            count_fetched_results = 0  # How many devices we already fetched.

            # Max amount of devices we want to fetch.
            max_count = min(count_total_results, MAX_NUMBER_OF_DEVICES)

            while count_fetched_results < max_count:
                url_params = {
                    'offset': count_fetched_results,
                    'limit': ENTITIES_PER_PAGE
                }

                response = self._get(url, url_params=url_params)

                if not isinstance(response, dict) and not isinstance(response.get('items'), list):
                    raise RESTException(f'Invalid response: {response}')

                count_fetched_results += len(response.get('items'))
                yield from response.get('items')

        except Exception:
            logger.exception(f'Invalid request made while paginating url: {url}')
            raise

    def get_device_list(self):
        try:
            yield from self._paginated_get(DEVICES_URL)
        except RESTException as err:
            logger.exception(str(err))
            raise

    def get_user_list(self):
        try:
            yield from self._paginated_get(USERS_URL)
        except RESTException as err:
            logger.exception(str(err))
            raise
