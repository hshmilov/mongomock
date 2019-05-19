import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.sysaid.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class SysaidConnection(RESTConnection):
    """ rest client for Sysaid adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'}, **kwargs)

    def create_sysaid_incident(self, sysaid_dict):
        description = sysaid_dict.get('description')
        self._post('sr',
                   body_params={'info': [{'key': 'notes',
                                          'value': [
                                              {'text': description}
                                          ]
                                          }
                                         ]
                                }
                   )
        return True

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._post('login', body_params={'user_name': self._username, 'password': self._password})

    def get_device_list(self):
        offset = 0
        while offset < MAX_NUMBER_OF_DEVICES:
            try:
                response = self._get('asset', url_params={'offset': offset, 'limit': DEVICE_PER_PAGE})
                if not response:
                    break
                yield from response
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem at offset {offset}')
                break
