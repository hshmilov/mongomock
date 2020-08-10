import logging
import datetime

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.parsing import int_or_none
from symantec_dcs_adapter.consts import API_URL_PREFIX, AUTH_TOKEN_EXPIRE_TIME, UMC_API_TOKEN_PREFIX, ASSETS_URL_PREFIX

logger = logging.getLogger(f'axonius.{__name__}')

# pylint:disable=logging-format-interpolation


class SymantecDcsConnection(RESTConnection):
    """ rest client for SymantecDcs adapter """

    def __init__(self, *args, umc_domain: str, umc_port: int, **kwargs):
        super().__init__(*args, url_base_prefix=API_URL_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

        self._umc_port = umc_port
        self._umc_domain = umc_domain

        self._session_refresh = None

    def _refresh_token(self):
        if self._session_refresh and self._session_refresh > datetime.datetime.now():
            return
        self._get_token()

    def _get_token(self):
        try:
            umc_auth_url = f'https://{self._umc_domain}:{self._umc_port}/{UMC_API_TOKEN_PREFIX}'

            body_params = {
                'username': self._username,
                'password': self._password
            }

            # Documented JSON request
            # https://apidocs.symantec.com/home/DCS#_generating_the_unified_management_console_authorization_token
            response = self._post(umc_auth_url, body_params=body_params, force_full_url=True)
            if not (isinstance(response, dict) and response.get('accessToken')):
                message = f'Received invalid response while trying to get token {response}'
                logger.warning(message)
                raise ValueError(message)

            refresh_time = int_or_none(response.get('expiresIn')) or AUTH_TOKEN_EXPIRE_TIME
            self._session_refresh = datetime.datetime.now() + datetime.timedelta(seconds=refresh_time - 100)
            self._token = response.get('accessToken')

            self._session_headers = {
                'Authorization': f'bearer {self._token}'
            }

        except Exception:
            raise ValueError(f'Error: Failed getting token, invalid request was made.')

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        try:
            self._get_token()
            self._get(ASSETS_URL_PREFIX)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _device_get(self):
        try:
            self._refresh_token()
            response = self._get(ASSETS_URL_PREFIX)
            if not isinstance(response, list):
                logger.warning(f'Received invalid response for devices. {response}')
                return

            yield from response
        except Exception:
            logger.exception(f'Invalid request made while paginating devices')
            raise

    def get_device_list(self):
        try:
            yield from self._device_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
