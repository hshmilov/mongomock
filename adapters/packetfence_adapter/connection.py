import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class PacketfenceConnection(RESTConnection):
    """ rest client for Packetfence adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._permanent_headers['Authorization'] = f'Bearer {self._apikey}'

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')
        self._get('nodes')

    def get_device_list(self):
        response = self._get('nodes')
        yield from response.get('items')
        while response.get('nextCursor'):
            try:
                cursor = response.get('nextCursor')
                response = self._get('nodes', url_params={'cursor': cursor})
                yield from response.get('items')
            except Exception:
                logger.exception(f'Problem in fetch last response was {response}')
                break
