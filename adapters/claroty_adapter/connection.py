import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from claroty_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class ClarotyConnection(RESTConnection):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='', headers={'Content-Type': 'application/json',
                                                             'Accept': 'application/json'}, **kwargs)

    def _connect(self):
        if self._username is not None and self._password is not None:
            response = self._post('auth/authenticate', body_params={'username': self._username,
                                                                    'password': self._password})
            if 'token' not in response:
                raise RESTException(f'Didnt get token on response: {str(response)}')
            self._session_headers['Authorization'] = response['token']
        else:
            raise RESTException('No username or password')

    def get_device_list(self):
        page_num = consts.FIRST_PAGE
        response = self._get('ranger/assets', url_params={'fields': '',
                                                          'format': 'asset_list',
                                                          'page': page_num,
                                                          'per_page': consts.DEVICE_PER_PAGE,
                                                          'special_hint__exact': '0,;$4'})
        yield from response['objects']
        count_total = min(response.get('count_total', 0), consts.MAX_NUMBER_OF_DEVICES)
        while page_num * consts.DEVICE_PER_PAGE < count_total:
            page_num += 1
            try:
                response = self._get('ranger/assets', url_params={'fields': '',
                                                                  'format': 'asset_list',
                                                                  'page': page_num,
                                                                  'per_page': consts.DEVICE_PER_PAGE,
                                                                  'special_hint__exact': '0,;$4'})
                yield from response['objects']
            except Exception:
                logger.exception(f'Got problem fetching page: {page_num}')
