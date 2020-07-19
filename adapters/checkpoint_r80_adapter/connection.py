import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from checkpoint_r80_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES, GATEWAY_DEVICE, HOST_DEVICE

logger = logging.getLogger(f'axonius.{__name__}')


class CheckpointR80Connection(RESTConnection):
    """ rest client for CheckpointR80 adapter """

    def __init__(self, *args, cp_domain: str = None, **kwargs):
        super().__init__(*args, url_base_prefix='web_api/v1',
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
        raw_response = self._post('login',
                                  body_params=body_params, use_json_in_response=False, return_response_raw=True)
        try:
            response = raw_response.json()
            if 'sid' not in response:
                raise RESTException(f'Got bad response with no token {response}')
            self._session_headers['X-chkp-sid'] = response['sid']
        except Exception:
            logger.exception(f'Got invalid response: {raw_response.content}')
            raise RESTException(f'Got invalid response: {raw_response.content}')

    def _get_api_object(self, api_endpoint):
        offset = 0
        response = self._post(api_endpoint,
                              body_params={'limit': DEVICE_PER_PAGE,
                                           'offset': offset})
        yield from response['objects']
        total = response['total']
        offset = DEVICE_PER_PAGE
        while offset < min(total, MAX_NUMBER_OF_DEVICES):
            try:
                response = self._post(api_endpoint,
                                      body_params={'limit': DEVICE_PER_PAGE,
                                                   'offset': offset})
                yield from response['objects']
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Got exception at offset {offset}')
                break

    def get_device_list(self):
        for device_raw in self._get_api_object('show-hosts'):
            yield device_raw, HOST_DEVICE
        try:
            for device_raw in self._get_api_object('show-gateways-and-servers'):
                yield device_raw, GATEWAY_DEVICE
        except Exception:
            logger.exception(f'Problem with gateways')
