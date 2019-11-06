import logging
import tempfile
from pathlib import Path

import requests
from gridfs import GridOut

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class CyberarkVaultException(Exception):

    def __init__(self, field_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._field_name = field_name

    def __repr__(self):
        # This is so the gui will recognize this specific error and to what field it's relevant to.
        return f'cyberark_vault_error:{self._field_name}:{super().__repr__()}'

    def __str__(self):
        # This is so the gui will recognize this specific error and to what field it's relevant to.
        return f'cyberark_vault_error:{self._field_name}:{super().__str__()}'


class CyberArkVaultConnection(RESTConnection):
    def get_device_list(self):
        pass

    def __init__(self, domain: str, port: int, cyberark_appid: str, cert: GridOut, *args, **kwargs):
        """ Initializes a connection to FreshService using its rest API """
        super().__init__(domain=domain, port=port, url_base_prefix='/AIMWebService/api/Accounts', *args, **kwargs)
        self._appid = cyberark_appid
        self._cert = cert
        self._cert_file = tempfile.NamedTemporaryFile()
        self._cert_file.write(self._cert)

    def _connect(self):
        """
        Establish a connection by retreiving.
        """

        # if username and password are not working with basic auth, you can base64 encode before auth header
        if self._apikey is not None:
            # will return the tickets of the last 30 days
            self._get('tickets')
        else:
            logger.exception('No username and password for connection to FreshService')
            raise RESTException('No username and password')

    @property
    def cert_path(self) -> Path:
        return Path(self._cert_file.name)

    def query_password(self, field_name, query):
        payload = {'AppID': self._appid, 'Query': query}
        try:
            response = self._handle_response(
                requests.get(self._url, cert=self.cert_path.as_posix(), params=payload, timeout=30))
        except Exception as exc:
            logger.exception(f'Failed to fetch password from vault using query: {query}')
            raise CyberarkVaultException(field_name, exc)

        return response.get('Content')
