import logging
# pylint: disable=deprecated-module
import string
# pylint: enable=deprecated-module
import random
import requests

# pylint: disable=import-error
from zeep import Client
from zeep.helpers import serialize_object
from zeep.transports import Transport
# pylint: enable=import-error

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.files import create_temp_file
from axonius.clients.digicert_pki_platform.consts import WS_CERTMGMT_SERVICE, \
    CLIENT_TRANSACTION_ID_PREFIX, DIGICERT_WEBSERVICES_CA

logger = logging.getLogger(f'axonius.{__name__}')


class DigicertPkiPlatformConnection(RESTConnection):
    ''' rest client for DigicertPkiPlatform adapter '''

    def __init__(self, domain: str, cert_file_data: bytes, private_key_data: bytes, *args, **kwargs):

        super().__init__(*args, domain=domain, url_base_prefix='',
                         headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                         verify_ssl=DIGICERT_WEBSERVICES_CA.name,
                         **kwargs)

        self.__cert_file = create_temp_file(cert_file_data)
        self.__private_key_file = create_temp_file(private_key_data)

        self.client = None

    def _connect(self):
        try:
            session = requests.Session()
            if self._proxies:
                session.proxies = self._proxies
            if self._verify_ssl:
                session.verify = self._verify_ssl
            if not self.add_ssl_cert(self.__cert_file.name, self.__private_key_file.name):
                raise ValueError('Private and Certificate do no match')
            session.cert = self._session.cert
            self.client = Client(f'{self._domain}/{WS_CERTMGMT_SERVICE}',
                                 transport=Transport(session=session))
        except Exception as e:
            raise RESTException(f'Failed connecting to PKI Platform: {str(e)}')

    def get_device_list(self):
        # Note: The following line generates a random "Axonius-0123456789ABCDEF" request identifier
        #        for auditing on Digicert systems and debugging purposes.
        transaction_id = f'{CLIENT_TRANSACTION_ID_PREFIX}-{"".join(random.choices(string.hexdigits, k=16))}'
        logger.debug(f'Fetching devices using transaction_id "{transaction_id}"')

        try:
            response = serialize_object(self.client.service.searchCertificate(version='1.0',
                                                                              clientTransactionID=transaction_id))
            logger.debug(f'Retrieved {response.get("certificateCount")} certificates'
                         f' from serverTransactionID: {response.get("serverTransactionID")}')
            if response.get('clientTransactionID') != transaction_id:
                logger.warning(f'Retrieved answer with different client identifier:'
                               f' {response.get("clientTransactionID")} != {transaction_id}')
            yield from response.get('certificateList', {}).get('certificateInformation', [])
        except Exception as e:
            logger.exception(f'Failed fetching devices using transaction {transaction_id}')
            raise RESTException(f'Failed fetching devices. error: {str(e)}')
