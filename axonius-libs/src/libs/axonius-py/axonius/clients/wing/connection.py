import datetime
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class WingConnection(RESTConnection):
    """ rest client for Wing adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='rest/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._session_refresh = datetime.datetime.now()
        self._token = None

    def _set_cookie(self):
        if not self._token:
            logger.warning(f'Tried to set_cookie without token!')
            return
        try:
            self._session.cookies['auth_token'] = self._token
        except Exception:
            logger.exception(f'Failed to set auth_token cookie.')
            raise RESTException(f'Failed to set authentication cookie')

    def _clear_cookie(self):
        if self._session:
            try:
                self._session.cookies.pop('auth_token', None)
            except Exception as e:
                logger.warning(f'Failed to purge auth_token cookie: {str(e)}', exc_info=True)

    @staticmethod
    def _extract_response_data(response):
        """
        Extract the 'data' dict from the response. Detailed error logs to debug log, raise user-friendly
        exceptions.
        Make sure response is a dict.
        :param response: the response to be handled.
        :return: response.get('data')
        """
        if not isinstance(response, dict):
            raise RESTException(f'Got bad response from server: {response}')
        return_code = response.get('return_code')
        if return_code:  # enter this flow if return code is not None and not 0 or empty string --> error
            logger.debug(f'Got nonzero return code from WiNG API: {return_code}, response: {response}')
            errors = response.get('errors')
            raise RESTException(f'Got errors in response. Return code: {return_code}, errors: {errors}')
        return response.get('data')

    def _increment_refresh_timeout(self):
        self._session_refresh = datetime.datetime.now() + datetime.timedelta(minutes=30)

    def _create_token(self):
        """
        Clear the cookie, get a new token, set the cookie.
        If fails at any point, raise a user-friendly exception and log detailed exception data.
        """
        self._token = None
        self._session_refresh = None
        self._clear_cookie()
        try:
            response = self._get('act/login', do_basic_auth=True)
            response_data = self._extract_response_data(response)
            if not isinstance(response_data, dict):
                raise RESTException(f'Bad response data. Expected dict, got: {type(response_data)}')
            token = response_data.get('token')
            if not token:
                raise RESTException(f'Failed to retrieve authentication token. Got: {token}')
            self._token = token
            self._increment_refresh_timeout()
            self._set_cookie()
        except Exception as e:
            logger.exception(f'Failed to get session token. Got exception: {str(e)}')
            raise RESTException(f'Failed to create session token for user {self._username}')

    def _refresh_token(self, advance_refresh=True):
        if self._session_refresh and self._session_refresh > datetime.datetime.now():
            self._create_token()
        elif advance_refresh:
            # advance refresh token
            self._session_refresh = datetime.datetime.now() + datetime.timedelta(minutes=30)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        try:
            self._create_token()
            self._get('cfg/device')
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def get_device_list(self):
        try:
            self._refresh_token()
            devices_response = self._get('cfg/device')
            devices_data = self._extract_response_data(devices_response)
            logger.info(f'BETA cfg/devices data type is {type(devices_data)}. Data follows:')
            to_log = '--DATA IS EMPTY--'
            if devices_data:
                if isinstance(devices_data, list):
                    to_log = devices_data[:5]
                if isinstance(devices_data, dict):
                    to_log = devices_data
            logger.info(f'{to_log}')
            logger.info(f'BETA cfg/devices data end')

            self._refresh_token()
            noc_devices_resp = self._get('stats/noc/devices')
            noc_devices_data = self._extract_response_data(noc_devices_resp)
            logger.info(f'BETA stats/noc/devices data type is {type(noc_devices_data)}. Data follows:')
            to_log = '--DATA IS EMPTY--'
            if noc_devices_data:
                if isinstance(noc_devices_data, list):
                    to_log = noc_devices_data[:5]
                if isinstance(noc_devices_data, dict):
                    to_log = noc_devices_data
            logger.info(f'{to_log}')
            logger.info(f'BETA stats/noc/devices data end')

        except RESTException as err:
            logger.exception(str(err))
            raise
        return []
