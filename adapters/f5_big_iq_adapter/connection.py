import logging
from datetime import datetime

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.parsing import int_or_none
from f5_big_iq_adapter.consts import LOGIN_URL, DEFAULT_TOKEN_TIMEOUT, LTM_VIRTUAL_SERVER_URL, TIMEOUT_EPSILON, \
    MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class F5BigIqConnection(RESTConnection):
    """ rest client for F5BigIq adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._token_timeout = None
        self._token = None
        self._token_fetch_date = None

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        try:
            self._set_token()
            self._get(LTM_VIRTUAL_SERVER_URL)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _set_token(self):
        body_params = {
            'username': self._username,
            'password': self._password
        }
        response = self._post(LOGIN_URL, body_params=body_params)
        if not (isinstance(response, dict) and isinstance(response.get('token'), dict)):
            message = f'Error while trying to connect, response is missing a token. {response}'
            logger.exception(message)
            raise RESTException(message)
        self._token_timeout = int_or_none(response.get('token').get('timeout')) or DEFAULT_TOKEN_TIMEOUT
        self._token_timeout -= TIMEOUT_EPSILON
        self._token_fetch_date = datetime.now()
        self._token = response.get('token').get('token')
        self._session_headers['X-F5-Auth-Token'] = self._token

    def _renew_token_if_needed(self):
        if (datetime.now() - self._token_fetch_date).total_seconds() >= self._token_timeout:
            self._set_token()

    def _get(self, *args, **kwargs):
        """
        Overrides _get function in order to renew token if needed.
        """
        self._renew_token_if_needed()
        return super()._get(*args, **kwargs)

    def _get_devices(self):
        try:
            response = self._get(LTM_VIRTUAL_SERVER_URL)
            if not (isinstance(response, dict) and isinstance(response.get('items'), list)):
                logger.warning(f'Response doesn\'t contain items in the correct format: {response}')
                return
            items = response.get('items')
            number_of_devices = 0
            for item in items:
                if not isinstance(item, dict):
                    message = f'Item not in the correct format: {item}'
                    logger.error(message)
                    continue
                yield item
                number_of_devices += 1
                if number_of_devices >= MAX_NUMBER_OF_DEVICES:
                    logger.info(
                        f'Exceeded max number of devices, collected: {number_of_devices}, '
                        f'left: {len(items) - number_of_devices}')
                    break
            logger.info(f'Got total of {number_of_devices} devices')
        except Exception:
            logger.exception(f'Invalid request made while fetching devices')
            raise

    def get_device_list(self):
        try:
            yield from self._get_devices()
        except RESTException as err:
            logger.exception(str(err))
            raise
