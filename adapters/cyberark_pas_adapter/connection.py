import logging
import datetime

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from cyberark_pas_adapter.consts import API_LOGON_SUFFIX, AuthenticationMethods, USER_LEGACY_API, USERS_API_SUFFIX, \
    MAX_NUMBER_OF_USERS, EXTRA_LEGACY

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class CyberarkPasConnection(RESTConnection):
    """ rest client for CyberarkPas adapter """

    def __init__(self, *args, auth_method, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        # Change CyberArk -> Cyberark
        if auth_method == AuthenticationMethods.Cyberark.value:
            auth_method = auth_method.capitalize()
        self._auth_method = auth_method
        self._token = None
        self._session_refresh = None

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        try:
            url_params = {
                'search': self._username
            }
            self._get_token()
            self._get(USERS_API_SUFFIX, url_params=url_params)

        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _get_token(self):
        try:
            body_params = {
                'username': self._username,
                'password': self._password
            }

            api_suffix = API_LOGON_SUFFIX.format(self._auth_method)
            self._session_refresh = datetime.datetime.now() + datetime.timedelta(seconds=250)
            self._token = self._post(api_suffix, body_params=body_params, use_json_in_response=False,
                                     return_response_raw=False)  # type: bytes
            self._session_headers = {
                'Authorization': self._token.decode('utf-8').strip('"')
            }

            logger.debug('Successfully Got Token')
        except Exception:
            raise ValueError(f'Error: Failed getting token, invalid request was made.')

    def _refresh_token(self):
        if self._session_refresh and self._session_refresh > datetime.datetime.now():
            return
        self._get_token()

    def _get_users(self):
        try:
            total_users = 0

            self._refresh_token()
            response = self._get(USERS_API_SUFFIX)
            if not (isinstance(response, dict) and isinstance(response.get('Users'), list)):
                logger.warning(f'Received invalid response while getting users {response}')
                return

            for user in response.get('Users'):
                if not (isinstance(user, dict) and user.get('id')):
                    logger.warning(f'Received invalid user {user}')
                    continue

                try:
                    user_url_suffix = f'{USERS_API_SUFFIX}/{user.get("id")}'
                    self._refresh_token()
                    response = self._get(user_url_suffix)
                    if isinstance(response, dict):
                        user = response

                except Exception:
                    try:
                        # If we fail to fetch info with the new api we will try to use legacy
                        if not user.get('username'):
                            logger.warning(f'Cant use legacy API, user doesnt contain username {user}')
                        else:
                            # This section purpose is to increase info about the user, therefor inside the else so we
                            # will reach the yield outside the exception
                            legacy_url_suffix = f'{USER_LEGACY_API}/{user.get("username")}'
                            self._refresh_token()
                            response = self._get(legacy_url_suffix)
                            if isinstance(response, dict):
                                user[EXTRA_LEGACY] = response

                    except Exception:
                        # Fallthrough and yield minimal data we have about the user
                        logger.error(f'Failed getting user information by id and username: '
                                     f'{user.get("id")} {user.get("username")}')

                yield user
                total_users += 1

                if total_users >= MAX_NUMBER_OF_USERS:
                    logger.info(f'Exceeded max number of users, {total_users} / {len(response.get("Users"))}')
                    break

            logger.info(f'Got total of {total_users}')
        except Exception as err:
            logger.exception(f'Invalid request made, {str(err)}')
            raise

    def get_device_list(self):
        pass

    def get_user_list(self):
        try:
            yield from self._get_users()
        except RESTException as err:
            logger.exception(str(err))
            raise
