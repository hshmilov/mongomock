import logging
import datetime

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from centrify_adapter.consts import URL_GET_TOKEN, GRANT_TYPE_CLIENT, URL_USERS, URL_APPS

logger = logging.getLogger(f'axonius.{__name__}')


class CentrifyConnection(RESTConnection):
    """ rest client for Centrify adapter """

    def __init__(self, app_id: str, scope: str, *args, **kwargs):
        self._app_id = app_id
        self._scope = scope
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json', 'X-CENTRIFY-NATIVE-CLIENT': 'true',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._token = None  # auth token
        self._token_expires = None  # seconds

    def _fetch_token(self):
        # API docs here are bad.
        # Details: https://developer.centrify.com/docs/client-credentials-flow#step-5-develop-a-client
        url = f'{URL_GET_TOKEN}/{self._app_id}'
        # Body should not be json,
        # And should be formatted pretty much like url params.
        # See powershell sample (verify v.s. REST Sandbox like GetSandbox) at:
        # https://github.com/centrify/centrify-samples-powershell/blob/master/module/Centrify.Samples.PowerShell.psm1
        body_params = {
            'grant_type': GRANT_TYPE_CLIENT,
            'scope': self._scope
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        try:
            response = self._post(url,
                                  body_params=body_params,
                                  do_basic_auth=True,
                                  use_json_in_body=False,
                                  extra_headers=headers)
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
        self._session_headers['Authorization'] = f'Bearer {self._token}'

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

    def _connect(self):
        self._token = None
        if not self._username or not self._password:
            raise RESTException('No username or password')
        try:
            self._renew_token_if_needed()
            self._post(URL_USERS)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def get_device_list(self):
        pass

    def _get_user_apps(self, user_uuid):
        # Get user's portal/apps data
        # Still no pagination unfortunately
        # API link: https://developer.centrify.com/reference#post_uprest-getresultantappsforuser
        self._renew_token_if_needed()
        url_params = {
            'userUuid': user_uuid
        }
        # Intentionally not wrapped in try/except, exceptions handled in get_user_list()
        apps_response = self._post(URL_APPS, url_params=url_params)
        if isinstance(apps_response.get('Result'), dict):
            result = apps_response.get('Result')
            apps = result.get('Apps')
            if apps and isinstance(apps, dict):  # in case there's only one app result
                apps = [apps]
            if apps and isinstance(apps, list):  # apps should be a list of dicts
                return apps
            if result.get('Message'):
                message = result.get('Message')
                error_id = result.get('ErrorID')
                raise RESTException(f'{error_id}: {message}')
        # If we got here then we didn't return apps, log a warning
        logger.debug(f'Failed to get apps for {user_uuid}. Response was: {apps_response}')
        return None

    def get_user_list(self):
        # No pagination, unfortunately.
        # API Link: https://developer.centrify.com/reference#post_cdirectoryservice-getusers
        try:
            self._renew_token_if_needed()
            users_response = self._post(URL_USERS)
            if not isinstance(users_response.get('Result'), dict) \
                    or not isinstance(users_response['Result'].get('Results'), list):
                raise RESTException(f'Bad response from server: {users_response}')
            for user_result_raw in users_response.get('Result').get('Results'):
                if not isinstance(user_result_raw, dict):
                    logger.warning(f'Got bad entry in response from server: {user_result_raw}')
                    continue
                user_result = user_result_raw.get('Row')
                if not isinstance(user_result, dict):
                    logger.warning(f'Got bad entry in response from server: {user_result_raw}')
                    continue
                uuid = user_result.get('Uuid')
                try:
                    user_result['x_apps'] = self._get_user_apps(uuid)  # inject apps data
                except Exception as e:
                    logger.debug(f'Failed to get application data for {user_result}: {str(e)}', exc_info=True)
                yield user_result
        except RESTException as err:
            logger.exception(str(err))
            raise
