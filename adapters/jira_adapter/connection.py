import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from jira_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')

ASSET_URL = 'asset'


class JiraConnection(RESTConnection):
    """ rest client for Jira adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='/rest/assetapi',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _paged_get_assets(self):
        start = 0
        remaining = MAX_NUMBER_OF_DEVICES
        url_params = {
            'start': start,
            'limit': DEVICE_PER_PAGE
        }
        try:
            response = self._get(ASSET_URL, url_params=url_params, do_basic_auth=True)
        except RESTException as e:
            message = f'Failed to get assets: {str(e)}'
            logger.exception(message)
            return
        if response.get('values'):
            yield from response.get('values')
        else:
            logger.warning(f'Got no results in response: {response}')
            return
        while remaining >= 0:
            start += DEVICE_PER_PAGE
            remaining -= DEVICE_PER_PAGE
            url_params = {
                'start': start,
                'limit': DEVICE_PER_PAGE
            }
            try:
                response = self._get(ASSET_URL, url_params=url_params, do_basic_auth=True)
            except RESTException:
                message = f'Failed to get {DEVICE_PER_PAGE} assets from offset {start}'
                logger.exception(message)
                raise
            if response.get('values'):
                yield from response.get('values')
            else:
                logger.warning(f'Got no results in response: {response}')
                return
            if response.get('isLastPage', True):
                break

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        try:
            url_params = {
                'start': 0,
                'limit': 1
            }
            self._get(ASSET_URL, url_params=url_params, do_basic_auth=True)
        except Exception as e:
            message = f'Failed to log in to {self._domain} with {self._username}: {str(e)}'
            logger.exception(message)
            raise RESTException(message)

    def get_device_list(self):
        yield from self._paged_get_assets()
