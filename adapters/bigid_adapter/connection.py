import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from bigid_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class BigidConnection(RESTConnection):
    """ rest client for Bigid adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        resposne = self._post('sessions', body_params={'username': self._username, 'password': self._password})
        if not isinstance(resposne, dict) or not resposne.get('auth_token'):
            raise RESTException(f'Bad response: {resposne}')
        token = resposne['auth_token']
        self._session_headers['authorization'] = token
        self._get('data-catalog/', url_params={'format': 'json', 'offset': 0, 'limit': DEVICE_PER_PAGE})

    def _paginated_device_get(self):
        try:
            offset = 0
            while offset < MAX_NUMBER_OF_DEVICES:
                try:
                    response = self._get('data-catalog/',
                                         url_params={'format': 'json', 'offset': offset, 'limit': DEVICE_PER_PAGE})
                    yield from response.get('results')
                    if len(response.get('results')) < DEVICE_PER_PAGE:
                        break
                    offset += DEVICE_PER_PAGE
                except Exception:
                    logger.exception(f'Problem at offset {offset}')
                    if offset == 0:
                        raise
                    break

        except Exception:
            logger.exception(f'Invalid request made while paginating devices')
            raise

    def get_device_list(self):
        try:
            for device_raw in self._paginated_device_get():
                try:
                    object_name = device_raw.get('objectName')
                    if not object_name:
                        continue
                    device_raw['extra_data'] = self._get(f'objects/{object_name}/records')
                except Exception:
                    logger.debug(f'Problem getting extra data for {device_raw}', exc_info=True)
                yield device_raw
        except RESTException as err:
            logger.exception(str(err))
            raise
