import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from omnivista_adapter.consts import MANAGED_DEVICE, CIRRUS_DEVICE, OV_DEVICE

logger = logging.getLogger(f'axonius.{__name__}')


class OmnivistaConnection(RESTConnection):
    """ rest client for Omnivista adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json',
                                  'Ov-App Version': '4.2.1.R01'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._post('login', body_params={'userName': self._username,
                                         'password': self._password
                                         })

    def get_device_list(self):
        response = self._get('devices')
        if not response.get('status') == 'SUCCESS' or not response.get('response'):
            raise RESTException(f'Bad response {response}')
        for device_raw in response['response']:
            yield device_raw, MANAGED_DEVICE
        try:
            response = self._post('wma/onlineClient/getOnlineClientList',
                                  body_params={'filterBy': 'all', 'filterContent': '', 'startMac': ''})
            if not response.get('status') == 'SUCCESS' or not response.get('response'):
                raise RESTException(f'Bad response {response}')
            for device_raw in response['response']:
                yield device_raw, OV_DEVICE
        except Exception:
            logger.exception(f'Problem with ov wlan')
        try:
            response = self._get('wma/onlineClient/getOnlineClientList')
            if not response.get('status') == 'SUCCESS' or not response.get('response'):
                raise RESTException(f'Bad response {response}')
            for device_raw in response['response']:
                yield device_raw, CIRRUS_DEVICE
        except Exception:
            logger.exception(f'Problem with cirrus wlan')
