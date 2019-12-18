import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from netbrain_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class NetbrainConnection(RESTConnection):
    """ rest client for Netbrain adapter """

    def __init__(self, *args, auth_id: str = None, tenant_id: str = None, domain_id: str = None, **kwargs):
        super().__init__(*args, url_base_prefix='ServicesAPI/API/V1/',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._auth_id = auth_id
        self._tenant_id = tenant_id
        self._domain_id = domain_id
        self._token = None

    def _login(self):
        url = consts.URL_LOGIN
        body_params = {'username': self._username, 'password': self._password}
        if self._auth_id:
            body_params['authentication_id'] = self._auth_id
        try:
            response = self._post(url, body_params=body_params)
        except Exception as e:
            message = f'Get token failed! Details: {str(e)}'
            logger.error(message)
            raise RESTException(message)
        if not isinstance(response, dict):
            raise RESTException(f'Bad response to login: {str(response)}')
        token = response.get('token')
        if not token:
            raise RESTException(f'Could not get token for username {self._username}! Auth failed?, got {response}')
        self._token = token
        self._session_headers['Token'] = self._token

    def _set_domain_id(self):
        url = consts.URL_SETDOMAIN
        body_params = {
            'tenantId': self._tenant_id,
            'domainId': self._domain_id,
        }
        try:
            self._put(url, body_params=body_params)
        except RESTException as e:
            message = f'Failed to set working domain! Details: {str(e)}'
            logger.error(message)
            raise RESTException(message)

    def _prepare_connection(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        if not self._tenant_id or not self._domain_id:
            raise RESTException('No tenant_id or domain_id')
        if self._token:
            logger.warning('Token already exists. Trying to recycle.')
            try:
                self._logout()
            except Exception as e:
                logger.exception(f'Login: Got an exception trying to recycle token: {str(e)}')
            finally:
                self._token = None

    def _connect(self):
        self._prepare_connection()
        self._login()
        self._set_domain_id()

    def _logout(self):
        if not self._token:
            logger.warning('Tried to logout of a session that is not logged in!')
            return
        url = consts.URL_LOGOUT
        try:
            self._delete(url)
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
        url = consts.URL_DEVICES
        try:
            response = self._get(url)
        except Exception as e:
            message = f'Get devices failed! Details: {str(e)}'
            logger.error(message)
            raise RESTException(message)
        if not isinstance(response, dict):
            raise RESTException(f'Expected response as dict, got instead {response}')
        if not isinstance(response.get('devices'), list):
            raise RESTException(f'Expected devices as list, got instead {response.get("devices")}')
        if 'devices' not in response:
            raise RESTException(f'Expected devices in dict, got instead {response}')
        yield from response.get('devices') or []
