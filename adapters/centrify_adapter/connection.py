import logging
import datetime

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from centrify_adapter.consts import URL_GET_TOKEN, GRANT_TYPE_CLIENT, URL_LOGOUT, URL_USERS, URL_APPS

logger = logging.getLogger(f'axonius.{__name__}')


class CentrifyConnection(RESTConnection):
    """ rest client for Centrify adapter """

    def __init__(self, app_id: str, scope: str, *args, **kwargs):
        self._app_id = app_id
        self._scope = scope
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._token = None  # auth token
        self._token_expires = None  # seconds

    def _fetch_token(self):
        # API docs here are bad.
        # Details: https://developer.centrify.com/docs/client-credentials-flow#step-5-develop-a-client
        url = f'{URL_GET_TOKEN}/{self._app_id}'
        body_params = {
            'grant_type': GRANT_TYPE_CLIENT,
            'scope': self._scope
        }
        try:
            response = self._post(url, body_params=body_params, do_basic_auth=True)
            if 'access_token' not in response:
                raise RESTException(f'Bad response when trying to get token: {response}')
            self._token = response['access_token']
            try:
                expires = int(response.get('expires_in'))
                self._token_expires = datetime.datetime.now() + datetime.timedelta(seconds=expires)
            except (ValueError, TypeError):
                message = f'Failed to get expiration time from {response}'
                logger.exception(message)
                raise RESTException(message)
        except Exception as e:
            message = f'Failed to acquire token for app {self._app_id} at scope {self._scope}: {str(e)}'
            logger.exception(message)
            raise RESTException(message)
        self._session_headers = {'Authorization': f'Bearer {self._token}'}

    def _is_token_expired(self):
        if not self._token_expires:
            raise RESTException(f'Bad auth flow: token expiration not set!')
        return datetime.datetime.now() >= self._token_expires

    def _should_fetch_token(self):
        if not self._token:
            return True
        return self._is_token_expired()

    def _renew_token_if_needed(self):
        if self._should_fetch_token():
            self._fetch_token()

    def _logout(self):
        try:
            response = self._post(URL_LOGOUT)
            self._token = None
            self._token_expires = None
            return response
        except Exception:
            logger.exception(f'Failed to logout!')
            # fallthrough
        return None

    def close(self):
        self._logout()
        super().close()

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        try:
            self._renew_token_if_needed()
            next(self.get_user_list(), None)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def get_device_list(self):
        pass

    def _get_user_apps(self, user_uuid):
        # Get user's portal/apps data
        # Still no pagination unfortunately
        # API link: https://developer.centrify.com/reference#post_uprest-getupdata
        self._renew_token_if_needed()
        url_params = {
            'userUuid': user_uuid
        }
        # Intentionally not wrapped in try/except, exceptions handled in get_user_list()
        result = self._post(URL_APPS, url_params)
        if isinstance(result.get('Result'), dict):
            return [result.get('Result')]
        if isinstance(result.get('Result'), list):
            return result.get('Result')
        if result.get('Message'):
            message = result.get('Message')
            error_id = result.get('ErrorID')
            raise RESTException(f'{error_id}: {message}')
        return None

    def get_user_list(self):
        # No pagination, unfortunately.
        # API Link: https://developer.centrify.com/reference#post_cdirectoryservice-getusers
        try:
            self._renew_token_if_needed()
            users_response = self._post(URL_USERS)
            if not isinstance(users_response.get('Result'), list):
                raise RESTException(f'Bad response from server: {users_response}')
            for user_result in users_response.get('Result'):
                if not isinstance(user_result, dict):
                    logger.warning(f'Got bad entry in response from server: {user_result}')
                    continue
                uuid = user_result.get('Uuid')
                try:
                    user_result['x_apps'] = self._get_user_apps(uuid)  # inject apps data
                except Exception as e:
                    logger.warning(f'Failed to get application data for {user_result}: {str(e)}')
                yield user_result
        except RESTException as err:
            logger.exception(str(err))
            raise
