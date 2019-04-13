import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from webroot_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class WebrootConnection(RESTConnection):
    """ rest client for Webroot adapter """

    def __init__(self, *args, gsm_key, site_id, **kwargs):
        self._gsm_key = gsm_key
        self._site_id = site_id
        super().__init__(*args, url_base_prefix=f'service/api/console/gsm/{self._gsm_key}/sites/{self._site_id}',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._permanent_headers['Authorization'] = f'Bearer {self._apikey}'

    def _connect(self):
        if not self._gsm_key or not self._site_id or not self._apikey:
            raise RESTException('No GSM key or no site ID or no API key')
        self._get('endpoints',
                  url_params={'pageSize': DEVICE_PER_PAGE,
                              'pageNr': 1})

    def get_device_list(self):
        page_num = 1
        response = self._get('endpoints',
                             url_params={'pageSize': DEVICE_PER_PAGE,
                                         'pageNr': 1})
        yield from response['Endpoints']
        count = response['TotalAvailable']
        logger.info(f'Count devices is {count}')
        while page_num * DEVICE_PER_PAGE < min(count, MAX_NUMBER_OF_DEVICES):
            try:
                page_num += 1
                response = self._get('endpoints',
                                     url_params={'pageSize': DEVICE_PER_PAGE,
                                                 'pageNr': page_num})
                if not response.get('Endpoints'):
                    break
                yield from response['Endpoints']
            except Exception:
                logger.exception(f'Problem at page num {page_num}')
                break
