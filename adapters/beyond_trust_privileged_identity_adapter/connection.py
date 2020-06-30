import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from beyond_trust_privileged_identity_adapter.consts import AUTHENTICATION_METHOD_CONVERT, API_PREFIX

logger = logging.getLogger(f'axonius.{__name__}')


class BeyondTrustPrivilegedIdentityConnection(RESTConnection):
    """ rest client for BeyondTrustPrivilegedIdentity adapter """

    def __init__(self, *args, login_type: str, **kwargs):
        super().__init__(*args, url_base_prefix=API_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

        self._login_type = login_type
        self._token = None

    def _get_token(self):
        try:
            body_params = {
                'Authenticator': self._login_type,
                'LoginType': AUTHENTICATION_METHOD_CONVERT[self._login_type],
                'Username': self._username,
                'Password': self._password
            }

            token = self._post('Login', body_params=body_params)
            if isinstance(token, str):
                self._token = token
            else:
                raise ValueError(f'Error: Received invalid token {token}, type {type(token)}')

            self._session_headers = {
                'AuthenticationToken': self._token
            }

        except Exception as e:
            raise ValueError(f'Error: Failed getting token, invalid request was made. {str(e)}')

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        try:
            self._get_token()
            self._get('Delegation/Identity')

        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    # pylint: disable=logging-format-interpolation
    def _logout(self):
        if not self._token:
            logger.warning('Tried to logout of a session that is not logged in!')
            return
        try:
            body_params = {
                'AuthenticationToken': self._token
            }
            self._post('Logout', body_params=body_params, use_json_in_response=False, return_response_raw=True)
        except Exception as e:
            message = f'Delete token failed! - {str(e)}'
            logger.warning(message, exc_info=RESTException(message))
        else:
            logger.info(f'Successfully logged out from {self._domain} with {self._username}')
        finally:
            self._token = None
            self._session_headers.clear()

    def close(self):
        self._logout()
        super().close()

    def get_device_list(self):
        pass

    # pylint: disable=logging-format-interpolation
    def _get_users(self):
        # No documentation about pagination
        try:
            identity_counter = 0
            response = self._get('Delegation/Identity')
            if not isinstance(response, list):
                logger.warning(f'Received invalid response while getting users {response}')
                return

            for identity in response:
                if not isinstance(identity, dict):
                    logger.warning(f'identity received is not a dict, received {identity}')
                    continue
                identity_counter += 1
                yield identity

            logger.debug(f'Finished getting identities, got {identity_counter}')
        except Exception as err:
            logger.exception(f'Invalid request made while paginating users {str(err)}')
            raise

    def get_user_list(self):
        try:
            yield from self._get_users()
        except RESTException as err:
            logger.exception(str(err))
            raise
