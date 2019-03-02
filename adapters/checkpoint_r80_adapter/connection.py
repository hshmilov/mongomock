import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from checkpoint_r80_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class CheckpointR80Connection(RESTConnection):
    """ rest client for CheckpointR80 adapter """

    def __init__(self, *args, cp_domain: str = None, **kwargs):
        super().__init__(*args, url_base_prefix='web_api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'}, **kwargs)
        self._cp_domain = cp_domain

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        body_params = {'user': self._username,
                       'password': self._password}
        if self._cp_domain:
            body_params['domain'] = self._cp_domain
        response = self._post('login',
                              body_params=body_params)
        if 'sid' not in response:
            raise RESTException(f'Got bad response with no token {response}')
        self._session_headers['X-chkp-sid'] = response['sid']

    def get_device_list(self):
        offset = 0
        response = self._post('show-hosts',
                              body_params={'limit': DEVICE_PER_PAGE,
                                           'offset': offset})
        yield from response['objects']
        total = response['total']
        offset = DEVICE_PER_PAGE
        while offset < min(total, MAX_NUMBER_OF_DEVICES):
            try:
                response = self._post('show-hosts',
                                      body_params={'limit': DEVICE_PER_PAGE,
                                                   'offset': offset})
                yield from response['objects']
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Got exception at offset {offset}')
                break
