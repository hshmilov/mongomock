# pylint: disable=import-error
import logging

from requests import Session
from requests.auth import HTTPBasicAuth
from zeep import Client  # pylint: disable=import-error
from zeep.transports import Transport  # pylint: disable=import-error
from zeep.helpers import serialize_object  # pylint: disable=import-error
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

        # Try fetching one device
        try:
            self.client.service.getNodeCount('*')
        except Exception as e:
            if 'This request requires HTTP authentication' in str(e):
                raise ValueError(f'Invalid credentials: {str(e)}')
            raise

    def get_constraint(self, name: str, value):
        # Try two methods of creating a constraint, for some reason this varies on different versions
        factory_names = ['ns0', 'ns3']
        for factory_name in factory_names:
            try:
                factory = self.client.type_factory(factory_name)
                return factory.constraint(name=name, value=value)
            except Exception:
                logger.info(f'Probelem with factory {factory_name}', exc_info=True)
        raise RESTException(f'Could not get proper XML format for pagination')

    def get_device_list(self):
        # The documentation does not specify any sign of pagination
        count = self.client.service.getNodeCount('*')
        logger.info(f'Nodes count: {count}')

        offset = 0
        while offset < count:
            try:
                assets = serialize_object(self.client.service.getNodes(self.get_constraint('offset', offset)))
                if not isinstance(assets, list):
                    break
                if len(assets) == 0:
                    break
                offset += len(assets)
                yield from assets
            except Exception:
                logger.exception(f'Exception while getting device list at offset {offset}')
                if offset == 0:
                    yield from serialize_object(self.client.service.getNodes('*'))
                    return
                raise
