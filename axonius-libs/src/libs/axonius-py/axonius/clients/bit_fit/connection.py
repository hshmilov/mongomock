import logging
import datetime

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.bit_fit.consts import OBJECTS_PER_PAGE, MAX_NUMBER_OF_OBJECTS, API_URL_TOKEN_SUFFIX, \
    DEFAULT_TOKEN_TYPE, DEFAULT_TOKEN_TIMEOUT_SEC, API_URL_ASSETS_SUFFIX, API_URL_USERS_SUFFIX, ASSET_TYPE, \
    USERS_TYPE, TOKEN_EXPIRES_GAP_SEC
from axonius.utils.parsing import int_or_none

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class BitFitConnection(RESTConnection):
    """ rest client for BitFit adapter """

    def __init__(self, *args, client_id: str, client_secret: str, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._client_id = client_id
        self._client_secret = client_secret
        self._session_refresh = None
        self._session_refresh_token = None

    def _refresh_token(self):
        if self._session_refresh_token and self._session_refresh > datetime.datetime.now():
            return

        body_params = {
            'grant_type': 'refresh_token',
            'client_id': self._client_id,
            'client_secret': self._client_secret,
            'refresh_token': self._session_refresh_token
        }
        self._get_token(body_params=body_params)

    def _get_token(self, body_params: dict=None):
        try:
            if not body_params:
                body_params = {
                    'grant_type': 'password',
                    'client_id': self._client_id,
                    'client_secret': self._client_secret,
                    'username': self._username,
                    'password': self._password
                }
            response = self._post(API_URL_TOKEN_SUFFIX, body_params=body_params)
            if not (isinstance(response, dict) and response.get('access_token')):
                raise RESTException(f'Failed getting token, received invalid response: {response}')

            token_expires = int_or_none(response.get('expires')) or DEFAULT_TOKEN_TIMEOUT_SEC
            sec = token_expires - TOKEN_EXPIRES_GAP_SEC
            self._session_refresh = datetime.datetime.now() + datetime.timedelta(seconds=sec)

            token_type = response.get('token_type') or DEFAULT_TOKEN_TYPE
            self._token = response.get('access_token')
            self._session_refresh_token = response.get('refresh_token')
            self._session_headers['Authorization'] = f'{token_type} {self._token}'

        except Exception as e:
            raise RESTException(f'Error: Failed getting token, invalid request was made. {str(e)}')

    def _connect(self):
        if not (self._username and self._password):
            raise RESTException('No username or password')
        if not (self._client_id and self._client_secret):
            raise RESTException('No client id or client secret')

        try:
            self._get_token()

            url_params = {
                'limit': 1,
                'offset': 0
            }
            self._get(API_URL_ASSETS_SUFFIX, url_params=url_params)
        except Exception as e:
            raise RESTException(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def get_device_list(self):
        try:
            yield from self._paginated_object_get(API_URL_ASSETS_SUFFIX, ASSET_TYPE)
        except Exception as err:
            logger.exception(f'Invalid request made while paginating {ASSET_TYPE} {str(err)}')
            raise

    def _paginated_user_get(self):
        try:
            yield from self._paginated_object_get(API_URL_USERS_SUFFIX, USERS_TYPE)
        except Exception as err:
            logger.exception(f'Invalid request made while paginating {USERS_TYPE} {str(err)}')
            raise

    def _paginated_object_get(self, api_suffix: str, object_type: str):
        try:
            total_fetched_objects = 0

            url_params = {
                'limit': OBJECTS_PER_PAGE,
                'offset': 0
            }

            while url_params['offset'] <= MAX_NUMBER_OF_OBJECTS:
                response = self._get(api_suffix, url_params=url_params)
                if not (isinstance(response, dict) and
                        isinstance(response.get('items'), list)):
                    logger.warning(f'Received invalid response for {object_type}: {response}')
                    continue

                for object_raw in response.get('items'):
                    if not isinstance(object_raw, dict):
                        continue
                    yield object_raw
                    total_fetched_objects += 1

                if len(response.get('items')) < OBJECTS_PER_PAGE:
                    logger.info(f'Done {object_type} pagination, got {len(response.get("items"))} / {OBJECTS_PER_PAGE}')
                    break

                if total_fetched_objects > MAX_NUMBER_OF_OBJECTS:
                    logger.warning(f'Exceeded max number of {object_type} {MAX_NUMBER_OF_OBJECTS}')
                    break

                url_params['offset'] += OBJECTS_PER_PAGE

            logger.info(f'Got total of {total_fetched_objects} {object_type}')
        except Exception as err:
            logger.exception(f'Invalid request made while paginating {object_type}, {str(err)}')
            raise

    def get_user_list(self):
        try:
            yield from self._paginated_user_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
