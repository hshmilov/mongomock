import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from alertlogic_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class AlertlogicConnection(RESTConnection):
    """ rest client for Alertlogic adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._password = ''

    def _connect(self):
        if not self._username:
            raise RESTException('No API Key')
        self._get('lm/v1/hosts',
                  do_basic_auth=True,
                  url_params={'offset': 0,
                              'limit': DEVICE_PER_PAGE})

    def get_device_list(self):
        response = self._get('lm/v1/hosts',
                             do_basic_auth=True,
                             url_params={'offset': 0,
                                         'limit': DEVICE_PER_PAGE})
        for device_raw in response['hosts']:
            if device_raw.get('host'):
                yield device_raw.get('host')
        offset = DEVICE_PER_PAGE
        total_count = response.get('total_count')
        while offset < min(total_count, MAX_NUMBER_OF_DEVICES):
            try:
                response = self._get('lm/v1/hosts',
                                     do_basic_auth=True,
                                     url_params={'offset': offset,
                                                 'limit': DEVICE_PER_PAGE})
                for device_raw in response['hosts']:
                    if device_raw.get('host'):
                        yield device_raw.get('host')
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem at offset {offset}')
                break
