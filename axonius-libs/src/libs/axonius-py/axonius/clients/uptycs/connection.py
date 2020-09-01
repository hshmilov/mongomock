import logging
import datetime
import jwt

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class UptycsConnection(RESTConnection):
    """ rest client for Uptycs adapter """

    def __init__(self, *args, customer_id, apisecret, **kwargs):
        super().__init__(*args, url_base_prefix=f'public/api/customers/{customer_id}',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._apisecret = apisecret

    def _set_headers(self):
        utcnow = datetime.datetime.utcnow()
        date = utcnow.strftime('%a, %d %b %Y %H:%M:%S GMT')
        auth = jwt.encode({'iss': self._apikey}, self._apisecret).decode('utf-8')
        authorization = f'Bearer {auth}'

        self._session_headers['Date'] = date
        self._session_headers['Authorization'] = authorization

    def _connect(self):
        if not (self._apikey and self._apisecret):
            raise RESTException('No api key or api secret')
        try:
            self._set_headers()
            self._get('assets')
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def get_device_list(self):
        for device_raw in self._get('assets')['items']:
            yield device_raw
