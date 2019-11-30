import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from wazuh_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class WazuhConnection(RESTConnection):
    """ rest client for Wazuh adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _get_request_and_validate(self, url):
        response = self._get(url, do_basic_auth=True)
        if not isinstance(response, dict) \
                or not response.get('error') == 0 \
                or not isinstance(response.get('data'), dict) \
                or not isinstance(response['data'].get('totalItems'), int) \
                or not isinstance(response['data'].get('items'), list):
            raise RESTException(f'Bad response: {response}')
        return response

    def _connect(self):
        self._get_request_and_validate(f'agents?limit={DEVICE_PER_PAGE}&pretty')

    def get_device_list(self):
        response = self._get_request_and_validate(f'agents?limit={DEVICE_PER_PAGE}&pretty')
        yield from response['data']['items']
        total_count = response['data']['totalItems']
        offset = DEVICE_PER_PAGE
        while offset < min(MAX_NUMBER_OF_DEVICES, total_count):
            try:
                response = self._get_request_and_validate(f'agents?offset={offset}&limit={DEVICE_PER_PAGE}&pretty')
                yield from response['data']['items']
                if len(response['data']['items']) == 0:
                    break
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem at offset {offset}')
                break
