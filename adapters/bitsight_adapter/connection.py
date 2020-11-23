import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class BitsightConnection(RESTConnection):
    """ rest client for Bitsight adapter """

    def __init__(self, *args, company_name, **kwargs):
        super().__init__(*args, url_base_prefix='ratings/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._company_name = company_name
        self._username = self._apikey
        self._password = ''

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')
        response = self._get('companies', do_basic_auth=True)
        if not self._company_name:
            if not 'my_company' in response and 'guid' not in response['my_company']:
                raise RESTException(f'Bad response: {response}')
            company = response['my_company']['guid']
        else:
            company = None
            if not response.get('companies') or not isinstance(response.get('companies'), list):
                raise RESTException(f'Bad Response: {response}')
            for company_raw in response.get('companies'):
                if company_raw.get('name') == self._company_name:
                    company = company_raw['guid']
                    break
            if not company:
                raise RESTException(f'Could not find company name')
        self._get(f'companies/{company}/observations', do_basic_auth=True)

    def get_device_list(self):
        response = self._get('companies', do_basic_auth=True)
        if not self._company_name:
            if not 'my_company' in response and 'guid' not in response['my_company']:
                raise RESTException(f'Bad response: {response}')
            company = response['my_company']['guid']
        else:
            company = None
            if not response.get('companies') or not isinstance(response.get('companies'), list):
                raise RESTException(f'Bad Response: {response}')
            for company_raw in response.get('companies'):
                if company_raw.get('name') == self._company_name:
                    company = company_raw['guid']
                    break
            if not company:
                raise RESTException(f'Could not find company name')
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
