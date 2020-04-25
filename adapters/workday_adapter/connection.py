import logging
import datetime

# pylint: disable=import-error
import zeep
import zeep.helpers
from zeep.wsse.signature import MemorySignature
from zeep.wsse.username import UsernameToken

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from workday_adapter.consts import DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')

WSDL_SUFFIX = '?wsdl'


class WorkdayConnection(RESTConnection):
    """ rest client for Workday adapter """

    def __init__(self,
                 domain,
                 tenant,
                 *args,
                 version='v24.1',
                 priv_key=None,
                 pub_cert=None,
                 cert_pass=None,
                 **kwargs):
        self._tenant = tenant
        self._priv_key = priv_key
        self._pub_cert = pub_cert
        self._cert_pass = cert_pass
        url_base_prefix = f'ccx/service/{self._tenant}/Human_Resources/{version}'
        super().__init__(*args,
                         domain=domain,
                         url_base_prefix=url_base_prefix,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._client = None
        self._wsse = list()
        if self._url.endswith('/'):
            self._url = self._url[:-1]
        self._wsdl_url = f'{self._url}{WSDL_SUFFIX}'

    def _create_client(self):
        if not self._verify_ssl:
            self._session.verify = False
        if self._proxies:
            self._session.proxies = self._proxies
        transport = zeep.Transport(session=self._session)
        self._client = zeep.Client(wsdl=self._wsdl_url,
                                   wsse=self._wsse,
                                   transport=transport)

    def _create_auth(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        try:
            self._wsse.append(UsernameToken(self._username, self._password))
        except Exception as e:
            message = f'Failed to create wsse signature from supplied credentials: {str(e)}'
            logger.exception(message)
            raise RESTException(message)
        if bool(self._priv_key) != bool(self._pub_cert):
            raise RESTException('Invalid options: Please supply both key and certificate, or neither.')
        if self._priv_key and self._pub_cert:
            try:
                self._wsse.append(MemorySignature(self._priv_key, self._pub_cert, self._cert_pass))
            except Exception as e:
                message = f'Failed to create wsse signature from supplied credentials: {str(e)}'
                logger.exception(message)
                raise RESTException(message)

    def _connect(self):
        self._create_auth()
        self._create_client()

    @staticmethod
    def _gen_args():
        request_crit = {
            'Response_Filter': {
                'Page': 1,
                'Count': DEVICE_PER_PAGE,
                'As_Of_Entry_DateTime': datetime.datetime.utcnow()
            },
            'Response_Group': {
                'Include_Compensation': False,
                'Include_Organizations': True,
                'Exclude_Company_Hierarchies': True,
                'Exclude_Matrix_Organizations': True,
                'Exclude_Funds': True,
                'Exclude_Fund_Hierarchies': True,
                'Exclude_Grants': True,
                'Exclude_Grant_Hierarchies': True,
                'Exclude_Gifts': True,
                'Exclude_Gift_Hierarchies': True,
                'Exclude_Pay_Groups': True,
                'Include_User_Account': True,

            }
        }
        return request_crit

    def get_users(self):
        kwargs = self._gen_args()
        response = self._client.service.Get_Workers(**kwargs)
        logger.debug(f'Got response: {response}')
        logger.debug(f'Response is {type(response)}')
        logger.debug(f'Response dict is: {response.__dict__}')
        logger.debug(f'Response deserialized is: {zeep.helpers.serialize_object(response)}')
        yield from response.data

    def get_device_list(self):
        # AUTOADAPTER - implement get_device_list
        raise NotImplementedError()
