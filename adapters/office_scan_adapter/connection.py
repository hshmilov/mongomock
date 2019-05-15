import base64
import hashlib
import time
import logging
import jwt

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from office_scan_adapter.consts import GET_AGENTS_URL

logger = logging.getLogger(f'axonius.{__name__}')


class OfficeScanConnection(RESTConnection):
    """ rest client for OfficeScan adapter """

    def __init__(self, *args, app_id, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._app_id = app_id

    @staticmethod
    def _create_checksum(http_method, raw_url, headers, request_body):
        string_to_hash = http_method.upper() + '|' + raw_url.lower() + '|' + headers + '|' + request_body
        base64_string = base64.b64encode(hashlib.sha256(str.encode(string_to_hash)).digest()).decode('utf-8')
        return base64_string

    def _create_jwt_token(self, http_method, raw_url, headers, request_body):
        iat = time.time()
        algorithm = 'HS256'
        version = 'V1'
        checksum = self._create_checksum(http_method, raw_url, headers, request_body)
        payload = {'appid': self._app_id,
                   'iat': iat,
                   'version': version,
                   'checksum': checksum}
        token = jwt.encode(payload, self._apikey, algorithm=algorithm).decode('utf-8')
        self._session_headers['Authorization'] = f'Bearer {token}'

    def _connect(self):
        if not self._app_id or not self._apikey:
            raise RESTException('No Application ID or API Key')
        self._get_agents_list()

    def _get_agents_list(self):
        self._create_jwt_token(request_body='',
                               headers='',
                               http_method='GET',
                               raw_url='/' + GET_AGENTS_URL)
        response = self._get(GET_AGENTS_URL)
        if response.get('result_code') == 1:
            yield from response.get('result_content')
        else:
            logger.error(f'Response: {response}')
            error_msg = response.get('result_description')
            raise RESTException(f'Bad response: {error_msg}')

    def get_device_list(self):
        yield from self._get_agents_list()
