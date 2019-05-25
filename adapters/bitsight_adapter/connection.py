import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class BitsightConnection(RESTConnection):
    """ rest client for Bitsight adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='ratings/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._username = self._apikey
        self._password = ''

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')
        response = self._get('companies', do_basic_auth=True)
        if not 'my_company' in response and 'guid' not in response['my_company']:
            raise RESTException(f'Bad response: {response}')
        company = response['my_company']['guid']
        self._get(f'companies/{company}/observations', do_basic_auth=True)

    def get_device_list(self):
        response = self._get('companies', do_basic_auth=True)
        if 'my_company' not in response and 'guid' not in response['my_company']:
            raise RESTException(f'Bad response: {response}')
        company = response['my_company']['guid']
        response = self._get(f'companies/{company}/observations', do_basic_auth=True)
        yield from response['data']
        while (response.get('cursors') or {}).get('next_url'):
            try:
                next_url = (response.get('cursors') or {}).get('next_url')
                response = self._get(next_url, force_full_url=True, do_basic_auth=True)
                yield from response['data']
            except Exception:
                logger.exception(f'Problem with fetching')
                break
