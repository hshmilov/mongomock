import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from kolide_adapter.consts import DEVICE_URL

logger = logging.getLogger(f'axonius.{__name__}')


class KolideConnection(RESTConnection):
    """ rest client for Kolide adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        # Api token bypasses username-password login.
        if not self._apikey:
            raise RESTException('No api token')

        try:
            self._session_headers['Authorization'] = f'Bearer {self._apikey}'
            self._get(DEVICE_URL)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _get_devices(self):
        try:
            response = self._get(DEVICE_URL)
            if not (isinstance(response, dict) and isinstance(response.get('hosts'), list)):
                logger.warning(f'Response is not in the correct format: {response}')
                return

            for host in response.get('hosts'):
                yield host

        except Exception:
            logger.exception(f'Invalid request made while fetching devices')
            raise

    def get_device_list(self):
        try:
            yield from self._get_devices()
        except RESTException as err:
            logger.exception(str(err))
            raise

    def get_user_list(self):
        pass
