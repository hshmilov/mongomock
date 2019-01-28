import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from samange_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class SamangeConnection(RESTConnection):
    """ rest client for Samange adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='', headers={'Content-Type': 'application/json',
                                                             'Accept': 'application/vnd.samanage.v2.1+json'},
                         **kwargs)
        self._permanent_headers['X-Samanage-Authorization'] = f'Bearer {self._apikey}'

    def _connect(self):
        if not self._apikey:
            raise RESTException('No APIKEY')
        self._get('hardwares.json',
                  url_params={'page': 1,
                              'per_page': DEVICE_PER_PAGE})

    def get_device_list(self):
        response = self._get('hardwares.json',
                             url_params={'page': 1,
                                         'per_page': DEVICE_PER_PAGE},
                             return_response_raw=True,
                             use_json_in_response=False)
        total_pages = int(response.headers['X-Total-Pages'])
        page = 2
        yield from response.json()
        while page < min(total_pages, int(MAX_NUMBER_OF_DEVICES / DEVICE_PER_PAGE)):
            try:
                response = self._get('hardwares.json',
                                     url_params={'page': page,
                                                 'per_page': DEVICE_PER_PAGE})
                if not response:
                    break
                yield from response
                page += 1
            except Exception:
                logger.exception(f'Problem at page {page}')
                break
