import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class ZertoConnection(RESTConnection):
    """ rest client for Zerto adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='v2',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not (self._username and self._password):
            raise RESTException('No username or password')

        try:
            response = self._post('auth/token', body_params={'username': self._username, 'password': self._password})
            if not isinstance(response, dict) or not response.get('token'):
                raise RESTException(f'Bad response from server')
            self._token = response.get('token')
            self._session_headers['Authorization'] = f'Bearer {self._token}'
            self._get('monitoring/protected-vms')
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _paginated_device_get(self):
        try:
            response = self._get('monitoring/protected-vms')
            if not isinstance(response, dict) or not isinstance(response.get('vpgs'), list):
                raise RESTException(f'Bad response: {response}')
            yield from response['vpgs']
        except Exception:
            logger.exception(f'Invalid request made while paginating devices')
            raise

    def get_device_list(self):
        # This function must exist even if the adapter doesnt fetch devices
        # Just do pass
        try:
            yield from self._paginated_device_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
