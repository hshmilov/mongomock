import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from extra_hop_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class ExtraHopConnection(RESTConnection):
    """ rest client for ExtraHop adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

        self._permanent_headers = {
            'Authorization': f'ExtraHop apikey={self._apikey}'
        }

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')

        try:
            url_params = {
                'limit': 1,
                'offset': 0
            }
            self._get('devices', url_params=url_params)
        except Exception:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials')

    # pylint: disable=logging-format-interpolation
    def _paginated_get(self):
        try:
            url_params = {
                'limit': DEVICE_PER_PAGE,
                'offset': 0
            }
            while url_params['offset'] < MAX_NUMBER_OF_DEVICES:
                response = self._get('devices', url_params=url_params)
                if not response:
                    return
                yield from response
                url_params['offset'] += DEVICE_PER_PAGE
        except Exception as err:
            logger.exception(f'Invalid request made, {str(err)}')
            raise

    def get_device_list(self):
        try:
            yield from self._paginated_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
