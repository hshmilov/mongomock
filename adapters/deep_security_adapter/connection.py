import logging
import time

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

    # pylint: disable=arguments-differ
    def _do_request(self, *args, **kwargs):
        kwargs.pop('raise_for_status', None)
        kwargs.pop('use_json_in_response', None)
        kwargs.pop('return_response_raw', None)
        resp_raw = super()._do_request(
            *args,
            raise_for_status=False,
            use_json_in_response=False,
            return_response_raw=True,
            **kwargs
        )
        if resp_raw.status_code == 429:
            try:
                retry_after = resp_raw.headers.get('Retry-After') or resp_raw.headers.get('retry-after')
                if retry_after:
                    logger.info(f'Got 429, sleeping for {retry_after}')
                else:
                    logger.info(f'Got 429 with no retry-after header, sleeping for 3')
                    retry_after = 2
                time.sleep(int(retry_after) + 1)
            except Exception:
                time.sleep(6)
            return super()._do_request(*args, **kwargs)

        return self._handle_response(resp_raw)

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
