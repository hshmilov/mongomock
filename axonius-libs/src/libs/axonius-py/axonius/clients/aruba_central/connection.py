import logging
import datetime

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.aruba_central.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES, \
    DEFAULT_TOKEN_EXPIRE_TIME_SEC, API_URL_LOGIN_SUFFIX, API_URL_AUTHENTICATION_SUFFIX, API_URL_TOKEN_SUFFIX, \
    API_URL_ACCESS_POINT_SUFFIX, API_URL_SWITCH_SUFFIX, ACCESS_POINT_TYPE, ACCESS_POINT_API_FIELD, SWITCH_TYPE, \
    SWITCH_API_FIELD
from axonius.utils.parsing import int_or_none

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class ArubaCentralConnection(RESTConnection):
    """ rest client for ArubaCentral adapter """

    def __init__(self, *args, customer_id: str, client_id: str, client_secret: str, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._customer_id = customer_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._renew_token = None
        self._session_refresh = None

    def _refresh_token(self):
        if self._session_refresh and self._session_refresh > datetime.datetime.now():
            return

        url_params = {
            'client_id': self._client_id,
            'client_secret': self._client_secret,
            'refresh_token': self._renew_token,
            'grant_type': 'refresh_token'
        }

        response = self._post(API_URL_TOKEN_SUFFIX, url_params=url_params)
        if not (isinstance(response, dict) and response.get('refresh_token') and response.get('access_token')):
            raise RESTException(f'Refresh token failed, received invalid response: {response}')

        token_expires = int_or_none(response.get('expires_in')) or DEFAULT_TOKEN_EXPIRE_TIME_SEC
        self._session_refresh = datetime.datetime.now() + datetime.timedelta(seconds=token_expires - 100)
        self._session_headers['Authorization'] = f'Bearer {response.get("access_token")}'
        self._renew_token = response.get('refresh_token')

    def _get_token(self):
        try:
            url_params = {
                'client_id': self._client_id
            }
            body_params = {
                'username': self._username,
                'password': self._password
            }
            # Create Session and get store cookies
            # Get X-CSRF-TOKEN from cookie.csrftoken
            # Get Cookie from cookie.session
            self._post(API_URL_LOGIN_SUFFIX, url_params=url_params, body_params=body_params)

            url_params['response_type'] = 'code'
            url_params['scope'] = 'all'
            body_params = {
                'customer_id': self._customer_id
            }
            response = self._post(API_URL_AUTHENTICATION_SUFFIX, url_params=url_params, body_params=body_params)
            if not (isinstance(response, dict) and response.get('auth_code')):
                raise RESTException(
                    f'Failed getting authentication code, received invalid response: {str(response.content)}')

            url_params = {
                'client_id': self._client_id,
                'grant_type': 'authorization_code',
                'client_secret': self._client_secret,
                'code': response.get('auth_code')}
            response = self._post(API_URL_TOKEN_SUFFIX, url_params=url_params)
            if not (isinstance(response, dict) and response.get('refresh_token') and response.get('access_token')):
                raise RESTException(f'Failed getting token, received invalid response: {str(response.content)}')

            token_expires = int_or_none(response.get('expires_in')) or DEFAULT_TOKEN_EXPIRE_TIME_SEC
            self._session_refresh = datetime.datetime.now() + datetime.timedelta(seconds=token_expires - 100)
            self._session_headers['Authorization'] = f'Bearer {response.get("access_token")}'
            self._renew_token = response.get('refresh_token')
        except Exception as e:
            raise RESTException(f'Error: Unable to receive token. {str(e)}')

    def _connect(self):
        if not (self._username and self._password):
            raise RESTException('No username or password')

        try:
            self._get_token()

            url_params = {
                'offset': 1,
                'limit': 1,
            }
            self._get(API_URL_ACCESS_POINT_SUFFIX, url_params=url_params)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _paginated_access_points_get(self):
        try:
            yield from self._paginated_object_get(ACCESS_POINT_TYPE, ACCESS_POINT_API_FIELD)
        except RESTException as err:
            logger.exception(str(err))

    def _paginated_switches_get(self):
        try:
            yield from self._paginated_object_get(SWITCH_TYPE, SWITCH_API_FIELD)
        except RESTException as err:
            logger.exception(str(err))

    def _paginated_object_get(self, object_type: str, object_field: str):
        try:
            total_fetched_objects = 0

            # Get total count of objects
            url_params = {
                'offset': 1,
                'limit': 1
            }
            if object_type == ACCESS_POINT_TYPE:
                url_suffix = API_URL_ACCESS_POINT_SUFFIX
            elif object_type == SWITCH_TYPE:
                url_suffix = API_URL_SWITCH_SUFFIX
            else:
                raise ValueError(f'Received unknown object type {object_type}')

            total_objects_count = MAX_NUMBER_OF_DEVICES
            response = self._get(url_suffix, url_params=url_params)
            if isinstance(response, dict) and int_or_none(response.get('total')):
                if int_or_none(response.get('total')) > MAX_NUMBER_OF_DEVICES:
                    logger.debug(f'Total count of {object_type} is too much {int_or_none(response.get("total"))}')
                total_objects_count = min(int_or_none(response.get('total')), MAX_NUMBER_OF_DEVICES)

            url_params['limit'] = DEVICE_PER_PAGE
            while total_fetched_objects <= total_objects_count:
                response = self._get(url_suffix, url_params=url_params)
                if not (isinstance(response, dict) and isinstance(response.get(object_field), list)):
                    logger.warning(f'Received invalid response for {object_type}:{object_field}: {response}')
                    break

                for device_object in response.get(object_field):
                    if isinstance(device_object, dict):
                        yield device_object, object_type
                        total_fetched_objects += 1

                if response.get('count') < DEVICE_PER_PAGE:
                    logger.info(f'Done {object_type} pagination, got {response.get("count")} / {DEVICE_PER_PAGE}')
                    break

                url_params['offset'] += DEVICE_PER_PAGE

            logger.info(f'Got total of {total_fetched_objects} {object_type}')
        except Exception:
            logger.exception(f'Invalid request made while paginating {object_type}')
            raise

    def get_device_list(self):
        try:
            yield from self._paginated_access_points_get()
        except RESTException as err:
            logger.exception(str(err))

        try:
            yield from self._paginated_switches_get()
        except RESTException as err:
            logger.exception(str(err))
