import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from code42_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class Code42Connection(RESTConnection):
    """ rest client for Code42 adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'}, **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._get('Computer',
                  url_params={'pgSize': DEVICE_PER_PAGE,
                              'pgNum': 1},
                  do_basic_auth=True)

    def _get_api_endpoint(self, endponint, dict_name, url_params_extra=None):
        page_num = 1
        url_params = {'pgSize': DEVICE_PER_PAGE, 'pgNum': page_num}
        if url_params_extra:
            url_params.update(url_params_extra)
        response = self._get(endponint,
                             url_params=url_params,
                             do_basic_auth=True)
        yield from response['data'][dict_name]
        while page_num * DEVICE_PER_PAGE < MAX_NUMBER_OF_DEVICES:
            try:
                page_num += 1
                url_params = {'pgSize': DEVICE_PER_PAGE, 'pgNum': page_num}
                if url_params_extra:
                    url_params.update(url_params_extra)
                response = self._get(endponint,
                                     url_params=url_params,
                                     do_basic_auth=True)
                if not response['data'].get(dict_name):
                    break
                yield from response['data'][dict_name]
            except Exception:
                logger.exception(f'Problem at page number {page_num}')
                break

    def get_user_list(self):
        yield from self._get_api_endpoint('User', 'users')

    def get_device_list(self):
        yield from self._get_api_endpoint('Computer', 'computers', url_params_extra={'incBackupUsage': 'true'})
