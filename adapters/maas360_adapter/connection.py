import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from maas360_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class Maas360Connection(RESTConnection):
    """ rest client for Maas360 adapter """

    def __init__(self, *args, billing_id, app_id, app_version, platform_id, app_access_key, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._app_id = app_id
        self._billing_id = billing_id
        self._platform_id = platform_id
        self._app_version = app_version
        self._app_access_key = app_access_key

    def _connect(self):
        # pylint: disable=too-many-boolean-expressions
        if not self._username or not self._password or not self._app_id \
                or not self._billing_id or not self._platform_id or not self._app_version or not self._app_access_key:
            raise RESTException('Missing Critical Parameter')
        auth_body = {'authRequest': {'maaS360AdminAuth': {'billingID': self._billing_id,
                                                          'password': self._password,
                                                          'userName': self._username,
                                                          'appID': self._app_id,
                                                          'appVersion': self._app_version,
                                                          'platformID': self._platform_id,
                                                          'appAccessKey': self._app_access_key}
                                     }}
        response = self._post(f'auth-apis/auth/1.0/authenticate/{self._billing_id}',
                              body_params=auth_body)
        if 'authResponse' not in response or 'authToken' not in response['authResponse']:
            raise RESTException(f'Bad response: {response}')
        if response['authResponse'].get('errorCode') != 0:
            error_msg = response['authResponse'].get('errorCode') or 'No Error Code'
            raise RESTException(f'Bad Response: {error_msg}')
        self._token = response['authResponse']['authToken']
        self._session_headers['Authorization'] = f'MaaS token={self._token}'
        self._get(f'device-apis/devices/2.0/search/customer/{self._billing_id}',
                  url_params={'pageSize': DEVICE_PER_PAGE,
                              'pageNumber': 1})

    def get_device_list(self):
        page_number = 1
        while page_number * DEVICE_PER_PAGE < MAX_NUMBER_OF_DEVICES:
            try:
                response = self._get(f'device-apis/devices/2.0/search/customer/{self._billing_id}',
                                     url_params={'pageSize': DEVICE_PER_PAGE,
                                                 'pageNumber': page_number})
                if not response.get('devices') or not response['devices'].get('device'):
                    break
                device_list = response['devices']['device']
                if isinstance(device_list, list):
                    yield from device_list
                elif isinstance(device_list, dict):
                    yield device_list
                else:
                    logger.warning(f'Bad device format {device_list}')
                    break
                page_number += 1
            except Exception:
                logger.exception(f'Problem at page {page_number}')
