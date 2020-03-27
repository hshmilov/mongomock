import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class DeepSecurityConnection(RESTConnection):
    """ rest client for DeepSecurity adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json', 'api-version': 'v1'},
                         **kwargs)
        self._permanent_headers['api-secret-key'] = self._apikey

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')
        response = self._get('computers', url_params={'expand': 'none'})
        if not response.get('computers'):
            raise RESTException(f'Bad response: {response}')

    def get_device_list(self):
        id_base = 0
        while True:
            body_params = {'maxItems': 5000, 'searchCriteria': [{'idValue': id_base, 'idTest': 'greater-than'}]}
            url_params = {'expand': 'computerStatus'}
            try:
                for device_raw in self._post('computers/search',
                                             url_params=url_params,
                                             body_params=body_params)['computers']:
                    if device_raw.get('ID') is None:
                        continue
                    if int(device_raw.get('ID')) > id_base:
                        id_base = int(device_raw.get('ID'))
                    yield device_raw
            except Exception:
                logger.exception(f'Problem with id {id_base}')
                break
