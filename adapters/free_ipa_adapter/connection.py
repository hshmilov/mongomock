import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from free_ipa_adapter.consts import API_PREFIX, MAX_NUMBER_OF_DEVICES, MAX_NUMBER_OF_USERS, API_LOGIN_PREFIX, \
    API_JSON_PREFIX, HOSTS_METHOD, USERS_METHODS

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class FreeIpaConnection(RESTConnection):
    """ rest client for FreeIpa adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix=API_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

        self._permanent_headers['referer'] = self._url

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        try:
            body_params = {
                'user': self._username,
                'password': self._password,
            }
            extra_headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            self._post(API_LOGIN_PREFIX, body_params=body_params, extra_headers=extra_headers, use_json_in_body=False,
                       use_json_in_response=False, return_response_raw=True)

            next(self._user_get(fetch_one=True), None)
            next(self._device_get(fetch_one=True), None)

        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _device_get(self, fetch_one: bool=False):
        try:
            params = {
                'all': True
            }

            if fetch_one:
                params['sizelimit'] = 1

            body_params = {
                'method': HOSTS_METHOD,
                'params': [[None], params]
            }
            response = self._post(API_JSON_PREFIX, body_params=body_params)
            if not (isinstance(response, dict) and
                    isinstance(response.get('result'), dict) and
                    isinstance(response.get('result').get('result'), list)):
                logger.warning(f'Received invalid response while getting devices {response}')
                return

            total_devices = 0
            for device in response.get('result').get('result'):
                yield device
                total_devices += 1
                if total_devices >= MAX_NUMBER_OF_DEVICES:
                    logger.debug(f'Reached max number of devices {total_devices}')
                    break

            logger.info(f'Got total of {total_devices} devices')
        except Exception:
            logger.exception(f'Invalid request made while paginating devices')
            raise

    def get_device_list(self):
        try:
            yield from self._device_get()
        except RESTException as err:
            logger.exception(str(err))
            raise

    def _user_get(self, fetch_one: bool=False):
        try:
            for method in USERS_METHODS:
                params = {
                    'all': True
                }

                if fetch_one:
                    params['sizelimit'] = 1

                body_params = {
                    'method': method,
                    'params': [[None], params]
                }
                response = self._post(API_JSON_PREFIX, body_params=body_params)
                if not (isinstance(response, dict) and
                        isinstance(response.get('result'), dict) and
                        isinstance(response.get('result').get('result'), list)):
                    logger.warning(f'Received invalid response while getting users for method {method} {response}')
                    break

                total_users = 0
                for user in response.get('result').get('result'):
                    yield user
                    total_users += 1
                    if total_users >= MAX_NUMBER_OF_USERS:
                        logger.debug(f'Reached max number of users {total_users}')
                        break

                logger.info(f'Got total of {total_users} users for method {method}')
        except Exception as err:
            logger.exception(f'Invalid request made while paginating users {str(err)}')
            raise

    def get_user_list(self):
        try:
            yield from self._user_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
