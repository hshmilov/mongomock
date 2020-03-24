import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from sevone_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class SevoneConnection(RESTConnection):
    """ rest client for Sevone adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='/api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        # API: https://sevdemo.sevone.com/api/docs
        if not self._username or not self._password:
            raise RESTException('No username or password')
        response = self._post(
            'authentication/signin',
            body_params={'name': self._username, 'password': self._password}
        )

        if 'token' not in response:
            raise RESTException(f'Invalid response: {response}')

        self._session_headers['X-AUTH-TOKEN'] = response['token']
        self._get('devices', url_params={'page': 0, 'size': 1})

    def get_device_list(self):
        response = self._get('devices', url_params={'page': 0, 'size': consts.DEVICE_PER_PAGE})
        yield from response.get('content') or []

        total_pages = response.get('totalPages')
        if not isinstance(total_pages, int):
            logger.error(f'Wrong total pages value: {str(total_pages)}')
            return

        current_page = 1
        while current_page <= min(total_pages, consts.MAX_PAGES):
            try:
                response = self._get('devices', url_params={'page': current_page, 'size': consts.DEVICE_PER_PAGE})
                content = response.get('content') or []
                if not content:
                    break
                yield from content

                current_page += 1
            except Exception:
                logger.exception(f'Exception in page {current_page}, stopping')
                break
