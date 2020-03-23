import base64
import hashlib
import hmac
import logging
import time

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from logicmonitor_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class LogicmonitorConnection(RESTConnection):
    """ rest client for LogicMonitor adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

        self._access_id = kwargs.get('access_id')
        self._access_key = kwargs.get('access_key')

        if kwargs.get('params'):
            self._url_base_prefix = f'{consts.ENDPOINT}{kwargs.get("params")}'
        else:
            self._url_base_prefix = f'{consts.ENDPOINT}'

    def _create_apikey(self, access_id: str, access_key: str,
                       data: str = '') -> str:
        """ Generate a unique access token for each query session. It is
            important that the epoch time be relatively accurate at both
            the client and server sides.
            :param str access_id: The UUID generated from the user name and password inside LogicMonitor.
            :param str access_key: The key that works with the access_id
            :param str data: An optional data string (rarely used in device
            fetch)
            :returns apikey: A string token that is unique to the request
            :rtype apikey: string
        """
        epoch_time = str(int(time.time() * 1000))

        # create a stronger hmac
        request_variables = (f'GET'
                             f'{epoch_time}'
                             f'{data}'
                             f'{consts.ENDPOINT}')

        # build the hmac from this data mashup
        request_hmac = hmac.new(access_key.encode(),
                                msg=request_variables.encode(),
                                digestmod=hashlib.sha256).hexdigest()

        # finally, build the signature from the hmac
        request_signature = base64.b64encode(request_hmac.encode())

        # create and return the authentication token
        self._apikey = f'LMv1 {access_id}:{request_signature.decode()}:{epoch_time}'

        return self._apikey

    def _connect(self):
        if not self._access_id or not self._access_key:
            raise RESTException('Sufficient authentication variables are not present')

        try:
            self._session_headers['Authorization'] = self._create_apikey(
                access_id=self._access_id,
                access_key=self._access_key)
        except Exception as e:
            logger.exception(f'Generation of the API key failed: {e}')

        endpoint = f'{consts.ENDPOINT}/1/properties'
        try:
            self._get(endpoint, url_params='{"size": consts.DEVICE_PER_PAGE, "offset": 0}')
        except Exception:
            logger.exception('Device pull from the {endpoint} endpoint failed')
            raise

    def get_device_list(self):
        start_offset = 0
        while start_offset < consts.MAX_NUMBER_OF_DEVICES:
            try:
                results = list(self._get(consts.ENDPOINT,
                                         url_params={'size': consts.DEVICE_PER_PAGE,
                                                     'offset': start_offset})['data'].get('items') or [])
                yield from results

                if len(results) == 0:
                    break

                start_offset += consts.DEVICE_PER_PAGE

            except Exception:
                logger.exception(f'Device pull from the {consts.ENDPOINT} endpoint failed')
                break
