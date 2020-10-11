import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.netiq.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES, \
    API_URL_LOGON_SUFFIX, API_URL_ENDPOINTS_ID_SUFFIX, LOGIN_METHODS, API_DEFAULT_EVENT

logger = logging.getLogger(f'axonius.{__name__}')

# pylint:disable=logging-format-interpolation


class NetiqConnection(RESTConnection):
    """ rest client for Netiq adapter """

    def __init__(self, *args, login_method: str, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._login_method = LOGIN_METHODS[login_method]

    def _get_token(self):
        try:
            body_params = {
                'method_id': f'{self._login_method}:1',
                'event': API_DEFAULT_EVENT,
                'user_name': self._username,
                'data': {
                    'password': self._password
                }
            }

            self._session_headers['X-Requested-With'] = 'XMLHttpRequest'

            # Token is saved in the cookie session
            response = self._post(API_URL_LOGON_SUFFIX, body_params=body_params, use_json_in_response=False,
                                  return_response_raw=True)
            if not response.headers.get('Set-Cookie'):
                raise RESTException(f'Failed getting token, received invalid response: {str(response.content)}')

            self._session_headers['Cookie'] = response.headers.get('Set-Cookie')
        except Exception as e:
            raise RESTException(f'Error: Unable to fetch cookie token. {str(e)}')

    def _connect(self):
        if not (self._username and self._password):
            raise RESTException('No username or password')

        try:
            self._get_token()
            url_params = {
                'offset': 0,
                'limit': 1
            }
            self._get(API_URL_ENDPOINTS_ID_SUFFIX, url_params=url_params)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _paginated_endpoints_get(self):
        try:
            total_fetched_endpoints = 0

            url_params = {
                'offset': 0,
                'limit': DEVICE_PER_PAGE
            }
            while url_params['offset'] < MAX_NUMBER_OF_DEVICES:
                response = self._get(API_URL_ENDPOINTS_ID_SUFFIX, url_params=url_params)
                if not (isinstance(response, dict) and isinstance(response.get('endpoints'), list)):
                    logger.warning(f'Received invalid response for endpoints: {response}')
                    break

                for endpoint in response.get('endpoints'):
                    if isinstance(endpoint, dict):
                        yield endpoint
                        total_fetched_endpoints += 1

                if total_fetched_endpoints >= MAX_NUMBER_OF_DEVICES:
                    logger.info(f'Exceeded max number of Endpoints '
                                f'{total_fetched_endpoints} / {len(response.get("count"))}')
                    break

                if url_params['limit'] < len(response.get('endpoints')):
                    logger.info(f'Done Endpoints pagination, got {len(response.get("endpoints"))} / {DEVICE_PER_PAGE}')
                    break

                url_params['offset'] += len(response.get('endpoints'))

            logger.info(f'Got total of {total_fetched_endpoints} endpoints id')
        except Exception:
            logger.exception(f'Invalid request made while paginating Endpoints')
            raise

    def get_device_list(self):
        try:
            yield from self._paginated_endpoints_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
