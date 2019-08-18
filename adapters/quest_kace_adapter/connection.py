import time
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from quest_kace_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class QuestKaceConnection(RESTConnection):
    """ rest client for QuestKace adapter """

    def __init__(self, *args, orgname, **kwargs):
        self._orgname = orgname
        if not self._orgname:
            self._orgname = 'Default'
        super().__init__(*args, url_base_prefix='', headers={'Content-Type': 'application/json',
                                                             'Accept': 'application/json'}, **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        response = self._post('ams/shared/api/security/login', body_params={'password': self._password,
                                                                            'userName': self._username,
                                                                            'organizationName': self._orgname},
                              use_json_in_response=False,
                              return_response_raw=True)
        if 'x-dell-csrf-token' not in response.headers:
            raise RESTException(f'Bad Response: {response.content[:100]}')
        self._session_headers['x-dell-csrf-token'] = response.headers['x-dell-csrf-token']
        self._session_headers['x-dell-api-version'] = '5'
        self._get(f'api/inventory/machines?shaping=machine all,software standard&'
                  f'paging=limit {DEVICE_PER_PAGE}')

    def get_device_list(self):
        offset = 0
        was_execption = False
        response = self._get(f'api/inventory/machines?paging=limit {DEVICE_PER_PAGE} offset {offset}')
        yield from response['Machines']
        count = response['Count']
        offset += DEVICE_PER_PAGE
        while offset < min(count, MAX_NUMBER_OF_DEVICES):
            try:
                response = self._get(f'api/inventory/machines?shaping=machine all,software standard&'
                                     f'paging=limit {DEVICE_PER_PAGE} offset {offset}')
                yield from response['Machines']
                was_execption = False
                count = response['Count']
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem at offset {offset}')
                if not was_execption:
                    was_execption = True
                    time.sleep(5)
                else:
                    break
