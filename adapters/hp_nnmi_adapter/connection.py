# pylint: disable=import-error
import logging

from requests import Session
from requests.auth import HTTPBasicAuth
from zeep import Client
from zeep.transports import Transport
from zeep.helpers import serialize_object
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


TEST_SERVICE_CONST = 123


class HpNnmiConnection(RESTConnection):
    """ rest client for HpNnmi adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            url_base_prefix='',
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
            **kwargs
        )
        self.client = None

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        session = Session()
        session.auth = HTTPBasicAuth(self._username, self._password)
        if self._verify_ssl:
            session.verify = self._verify_ssl
        if self._proxies:
            session.proxies = self._proxies

        # Send a requests just to make sure this isa valid ssl. This has to be on a seperate thread, as the other
        # line uses the regular requests.get of the system which is preconfigured to ignore invalid certs
        session.get(f'{self._url}NodeBeanService/NodeBean?wsdl', verify=self._verify_ssl)

        client = Client(f'{self._url}NodeBeanService/NodeBean?wsdl', transport=Transport(session=session))
        # Do not try to fetch assets, as there is no pagination, and this can take time.
        self.client = client

    def get_device_list(self):
        # The documentation does not specify any sign of pagination
        assets = serialize_object(self.client.service.getNodes('*'))
        yield from assets
