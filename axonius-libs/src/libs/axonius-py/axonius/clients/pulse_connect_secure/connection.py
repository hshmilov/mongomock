import logging

from axonius.clients.pulse_connect_secure.consts import MAX_NUMBER_OF_DEVICES, AUTHENTICATION_URL, USERS_URL, \
    URL_BASE_PREFIX
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class PulseConnectSecureConnection(RESTConnection):
    """ rest client for PulseConnectSecure adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix=URL_BASE_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not (self._username and self._password):
            raise RESTException('No username or password')

        try:
            response = self._get(AUTHENTICATION_URL, do_basic_auth=True, is_auth=True)
            if not (isinstance(response, dict) and response.get('api_key')):
                raise RESTException(f'Response not in correct format {response}')

            self._apikey = response.get('api_key')

            url_params = {'number': 1}
            response = self._get(USERS_URL, url_params=url_params)
        except Exception as e:
            raise Exception(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    # pylint: disable=arguments-differ
    def _get(self, *args, is_auth: bool = False, **kwargs):
        """
        Overrides _get function.
        Adding each API request Authorization header of the apikey received in the authentication.
        """
        if self._apikey is None or is_auth:
            return super()._get(*args, **kwargs)

        return super()._get(*args, do_basic_auth=True, alternative_auth_dict=(self._apikey, ''), **kwargs)

    def get_device_list(self):
        pass

    def _get_active_users(self):
        try:
            total_fetched_users = 0

            url_params = {'number': MAX_NUMBER_OF_DEVICES}
            response = self._get(USERS_URL, url_params=url_params)
            if not (isinstance(response, dict) and
                    isinstance(response.get('active-users'), dict) and
                    isinstance(response.get('active-users').get('active-user-records'), dict) and
                    isinstance(response.get('active-users').get('active-user-records').get('active-user-record'),
                               list)):
                logger.warning(f'Received invalid response for users: {response}')
                return

            total_users_in_request = response.get('total-returned-record-number')

            for user in response.get('active-users').get('active-user-records').get('active-user-record'):
                if not isinstance(user, dict):
                    continue
                yield user
                total_fetched_users += 1
                if total_fetched_users >= MAX_NUMBER_OF_DEVICES:
                    logger.info('Exceeded max number of users')
                    break

            logger.info(f'Got total of {total_fetched_users} / {total_users_in_request} users')
        except Exception as err:
            logger.exception(f'Invalid request made while getting active users {str(err)}')
            raise

    def get_user_list(self):
        try:
            yield from self._get_active_users()
        except RESTException as err:
            logger.exception(str(err))
            raise
