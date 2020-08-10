import logging
import datetime

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.parsing import int_or_none
from extreme_networks_extreme_control_adapter.consts import TOKEN_GRANT_TYPE, DEFAULT_TOKEN_REFRESH_TIME, \
    GET_TOKEN_URL_SUFFIX, TOKEN_TYPE_REFRESH_TYPE, REFRESH_TOKEN_URL_SUFFIX, SWITCH_API_SUFFIX, API_BASE_PREFIX

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class ExtremeNetworksExtremeControlConnection(RESTConnection):
    """ rest client for ExtremeNetworksExtremeControl adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix=API_BASE_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._session_refresh_time = None
        self._session_refresh_token = None

    def _get_token(self, url: str, body_params: dict):
        response = self._post(url, body_params=body_params)
        if not (isinstance(response, dict) and response.get('access_token')):
            raise RESTException(f'Failed getting token, received invalid response: {response}')

        expires_in = int_or_none(response.get('expires_in')) or DEFAULT_TOKEN_REFRESH_TIME
        self._session_refresh_time = datetime.datetime.now() + datetime.timedelta(seconds=(expires_in - 100))

        self._token = response.get('access_token')
        self._session_refresh_token = response.get('refresh_token')

        # authorization with small letters as documented
        # https://documentation.extremenetworks.com/extremecloud/information_center/GUID-FDB2CFB3-5793-4A97-B680-57EE8FA577FD.shtml
        self._session_headers['authorization'] = f'Bearer {self._token}'

    def _refresh_access_token(self):
        try:
            if self._session_refresh_time and self._session_refresh_time > datetime.datetime.now():
                return

            body_params = {
                'grantType': TOKEN_TYPE_REFRESH_TYPE,
                'refreshToken': self._session_refresh_token
            }

            self._get_token(url=REFRESH_TOKEN_URL_SUFFIX, body_params=body_params)
        except Exception:
            logger.exception(f'Error: Failed refreshing token, invalid request was made.')
            raise RESTException(f'Error: Failed refreshing token, invalid request was made.')

    def _get_access_token(self):
        try:
            body_params = {
                'grantType': TOKEN_GRANT_TYPE,
                'userId': self._username,
                'password': self._password,
            }
            self._get_token(url=GET_TOKEN_URL_SUFFIX, body_params=body_params)
        except Exception:
            logger.exception(f'Error: Failed getting token, invalid request was made.')
            raise RESTException(f'Error: Failed getting token, invalid request was made.')

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        try:
            self._get_access_token()
            self._get(SWITCH_API_SUFFIX)

        except Exception as e:
            raise RESTException(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _get_switches(self):
        try:
            total_switches = 0

            self._refresh_access_token()
            response = self._get(SWITCH_API_SUFFIX)
            if isinstance(response, dict):
                response = [response]
            if not isinstance(response, list):
                logger.warning(f'Received invalid response while getting switches {response}')
                return

            for switch in response:
                if not isinstance(switch, dict):
                    logger.warning(f'Switch is not a dict type, got {switch}')
                    continue

                total_switches += 1
                yield switch

            logger.info(f'Got total of {total_switches} switches')
        except Exception:
            logger.exception(f'Invalid request made while getting switches')
            raise

    def get_device_list(self):
        try:
            yield from self._get_switches()
        except RESTException as err:
            logger.exception(str(err))
            raise
