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
                try:
                    software_hrefs = [{'name': device_raw.get('softwares_href'),
                                       'force_full_url': True} for device_raw in response]
                    software_hrefs_hidden = [{'name': device_raw.get('hidden_softwares_href'),
                                              'force_full_url': True} for device_raw in response]
                    for device_raw, software_response in zip(response, self._async_get(software_hrefs)):
                        if self._is_async_response_good(software_response):
                            device_raw['software'] = software_response
                    for device_raw, software_hidden_response in zip(response, self._async_get(software_hrefs_hidden)):
                        if self._is_async_response_good(software_hidden_response):
                            device_raw['hidden_software'] = software_hidden_response
                except Exception:
                    logger.exception(f'Problem getting software for page {page}')
                yield from response
                page += 1
            except Exception:
                logger.exception(f'Problem at page {page}')
                break
