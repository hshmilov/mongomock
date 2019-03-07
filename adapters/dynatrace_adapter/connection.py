import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class DynatraceConnection(RESTConnection):
    """ rest client for Dynatrace adapter """

    def __init__(self, *args, environment_id, premise_domain, **kwargs):
        if premise_domain:
            domain = premise_domain
            url_base_prefix = f'e/{environment_id}/api/v1'
        else:
            domain = f'{environment_id}.live.dynatrace.com'
            url_base_prefix = 'api/v1'
        super().__init__(*args, url_base_prefix=url_base_prefix, domain=domain,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._permanent_headers['Authorization'] = f'Api-Token {self._apikey}'

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')
        self._get('entity/infrastructure/hosts',
                  url_params={'startTimestamp': 1000 * 10})

    def get_device_list(self):
        yield from self._get('entity/infrastructure/hosts')
