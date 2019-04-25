import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from sentinelone_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class SentinelOneConnection(RESTConnection):

    def __init__(self, *args, **kwargs):
        self.__api_version = None
        super().__init__(url_base_prefix='/', *args, **kwargs)
        self._permanent_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    def _set_token_v2(self, token):
        """ Sets the API token (as the connection credentials)

        :param str token: API Token
        """
        self._token = token
        if not self._username:
            token_type = 'ApiToken '
            self._permanent_headers['Authorization'] = token_type + self._token
        else:
            token_type = 'Token '
            self._session_headers['Authorization'] = token_type + self._token

    def _set_token_v1(self, token):
        self._token = token
        if not self._username:
            token_type = 'APIToken '
            self._permanent_headers['Authorization'] = token_type + self._token
        else:
            token_type = 'Token '
            self._session_headers['Authorization'] = token_type + self._token

    def _connect(self):
        if not self.__api_version:
            try:
                self._connect_v2()
            except Exception as e:
                if '404' in repr(e):
                    self._connect_v1()
                    return
                raise
        elif self.__api_version == consts.V1:
            self._connect_v1()
        elif self.__api_version == consts.V2:
            self._connect_v2()
        else:
            raise RESTException('No API Version found')

    def _connect_v2(self):
        if self._username and self._password:
            connection_dict = {'username': self._username,
                               'password': self._password}
            response = self._post('web/api/v2.0/users/login', body_params=connection_dict)
            if 'data' not in response or 'token' not in response['data']:
                error = response.get('error', 'unknown connection error')
                message = response.get('message', '')
                if message:
                    error += ': ' + message
                raise RESTException(error)
            self._set_token_v2(response['data']['token'])
        elif self._apikey:
            self._set_token_v2(self._apikey)
        else:
            raise RESTException(f'Insufficient credentials, please provide username & password or api-key')
        self._get('web/api/v2.0/agents', url_params={'limit': consts.DEVICE_PER_PAGE,
                                                     'skip': 0})
        self.__api_version = consts.V2

    def _connect_v1(self):
        if self._username and self._password:
            connection_dict = {'username': self._username,
                               'password': self._password}
            response = self._post('web/api/v1.6/users/login', body_params=connection_dict)
            if 'token' not in response:
                error = response.get('error', 'unknown connection error')
                message = response.get('message', '')
                if message:
                    error += ': ' + message
                raise RESTException(error)
            self._set_token_v1(response['token'])
        elif self._apikey:
            self._set_token_v1(self._apikey)
        else:
            raise RESTException(f'Insufficient credentials, please provide username & password or api-key')
        self._get('web/api/v1.6/agents/count')
        self.__api_version = consts.V1

    def _get_device_list_v1(self):
        count = self._get('web/api/v1.6/agents/count')['count']
        logger.info(f'Got {count} Devices from count api')
        start_offset = 0
        while start_offset < min(count, consts.MAX_DEVICES):
            try:
                for device_raw in self._get('web/api/v1.6/agents', url_params={'limit': consts.DEVICE_PER_PAGE,
                                                                               'skip': start_offset}):
                    try:
                        device_id = device_raw.get('id')
                        device_raw['apps'] = self._get(f'web/api/v1.6/agents/{device_id}/applications')
                    except Exception:
                        logger.exception(f'Problem adding software to {device_raw}')
                    yield device_raw, consts.V1
            except Exception:
                logger.exception(f'Problem with offset {start_offset}')
            start_offset += consts.DEVICE_PER_PAGE

    def _get_device_list_v2(self):
        response = self._get('web/api/v2.0/agents', url_params={'limit': consts.DEVICE_PER_PAGE})
        for device_raw in response['data']:
            yield device_raw, consts.V2
        total_devices = response['pagination']['totalItems']
        cursor = response['pagination']['nextCursor']
        while cursor:
            try:
                response = self._get('web/api/v2.0/agents', url_params={'limit': consts.DEVICE_PER_PAGE,
                                                                        'cursor': cursor})
                for device_raw in response['data']:
                    yield device_raw, consts.V2
                if len(response['data']) < consts.DEVICE_PER_PAGE:
                    break
                cursor = response['pagination']['nextCursor']
            except Exception:
                logger.exception(f'Problem while fetching')
                break

    def get_device_list(self):
        if self.__api_version == consts.V2:
            yield from self._get_device_list_v2()
        elif self.__api_version == consts.V1:
            yield from self._get_device_list_v1()
