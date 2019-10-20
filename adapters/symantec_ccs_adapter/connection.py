import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from symantec_ccs_adapter.consts import DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class SymantecCcsConnection(RESTConnection):
    """ rest client for SymantecCcs adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='ccs/api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        response = self._post('oauth/tokens',
                              body_params={'username': self._username,
                                           'password': self._password,
                                           'grant_type': 'password'})
        if not response.get('access_token'):
            raise RESTException(f'Bad login response: {response}')
        self._token = response['access_token']
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        response = self._get('Assets',
                             url_params={'pagesize': 1,
                                         'page': 0,
                                         'ContainerPath': 'asset system',
                                         'SearchSubTree': True,
                                         'attributes': '(displayName = *)'})
        if not response.get('assetDataList'):
            raise RESTException(f'Bad response from server')

    def _get_device_ids(self):
        page = 0
        response = self._get('Assets',
                             url_params={'pagesize': DEVICE_PER_PAGE,
                                         'page': page,
                                         'ContainerPath': 'asset system',
                                         'SearchSubTree': True,
                                         'attributes': '(displayName = *)'})
        if not response.get('assetDataList'):
            raise RESTException(f'Bad response from server')
        for device_raw in response.get('assetDataList'):
            if device_raw.get('Id'):
                yield device_raw.get('Id')
        total_pages = response.get('TotalPages')
        if not isinstance(total_pages, int):
            return
        page = 1
        while page < total_pages:
            try:
                response = self._get('Assets',
                                     url_params={'pagesize': DEVICE_PER_PAGE,
                                                 'page': page,
                                                 'ContainerPath': 'asset system',
                                                 'SearchSubTree': True,
                                                 'attributes': '(displayName = *)'})
                if not response.get('assetDataList'):
                    raise RESTException(f'Bad response from server')
                for device_raw in response.get('assetDataList'):
                    if device_raw.get('Id'):
                        yield device_raw.get('Id')
                page += 1
            except Exception:
                logger.exception(f'Problem with page {page}')
                break

    def get_device_list(self):
        for device_id in self._get_device_ids():
            try:
                yield self._get(f'Assets/{device_id}')
            except Exception:
                logger.exception(f'Problem getting data for {device_id}')
