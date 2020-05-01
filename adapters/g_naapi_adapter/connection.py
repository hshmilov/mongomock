import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class GNaapiConnection(RESTConnection):
    """ rest client for GNaapi adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        try:
            pass
        except Exception:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials')

    def _paginated_device_get(self):
        try:
            yield from self._get('')
        except Exception:
            logger.exception(f'Invalid request made while paginating devices')
            raise

    def get_device_list(self):
        try:
            yield from self._paginated_device_get()
        except RESTException as err:
            logger.exception(str(err))
            raise

    def _paginated_user_get(self):
        try:
            yield from self._get('')
        except Exception as err:
            logger.exception(f'Invalid request made while paginating users {str(err)}')
            raise

    def get_user_list(self):
        try:
            yield from self._paginated_user_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
