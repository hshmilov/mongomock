import logging

from axonius.clients.proofpoint.consts import MAX_NUMBER_OF_USERS, USERS_URL_SUFFIX
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.parsing import parse_bool_from_raw

logger = logging.getLogger(f'axonius.{__name__}')


class ProofpointConnection(RESTConnection):
    """ rest client for Proofpoint adapter """

    def __init__(self, *args, organization_domain=None, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._organization_domain = organization_domain

    def _connect(self):
        if not (self._username and self._password and self._organization_domain):
            raise RESTException('No username or password')

        try:
            self._session_headers['X-User'] = self._username
            self._session_headers['X-Password'] = self._password

            self._get(USERS_URL_SUFFIX.format(domain=self._organization_domain))
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def get_device_list(self):
        pass

    def _get_users(self, fetch_inactive_users: bool = False):
        try:
            total_fetched_users = 0

            response = self._get(USERS_URL_SUFFIX.format(domain=self._organization_domain))
            if not isinstance(response, list):
                logger.warning(f'Received invalid response for users: {response}')
                return

            for user in response:
                if not isinstance(user, dict):
                    continue
                is_active = parse_bool_from_raw(user.get('is_active')) or False
                if not fetch_inactive_users and not is_active:
                    continue
                yield user
                total_fetched_users += 1

                if total_fetched_users >= MAX_NUMBER_OF_USERS:
                    logger.info(
                        f'Got max number of users: {total_fetched_users}, left: {len(response) - total_fetched_users}')
                    break

            logger.info(f'Got total of {total_fetched_users} users')
        except Exception as err:
            logger.exception(f'Invalid request made while paginating users {str(err)}')
            raise

    def get_user_list(self, fetch_inactive_users: bool = False):
        try:
            yield from self._get_users(fetch_inactive_users)
        except RESTException as err:
            logger.exception(str(err))
            raise
