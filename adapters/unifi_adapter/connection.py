import logging
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

# pylint: disable=wildcard-import
from unifi_adapter.consts import *

logger = logging.getLogger(f'axonius.{__name__}')


class UnifiConnection(RESTConnection):
    """ rest client for Unifi adapter """

    def __init__(self, *args, site=None, **kwargs):
        super().__init__(*args, url_base_prefix=URL_BASE_PREFIX, **kwargs)
        if not site:
            site = DEFAULT_SITE
        self._site = site

    # pylint: disable=arguments-differ
    def _do_request(self, method, name, *args, **kwargs):
        kwargs['raise_for_status'] = False

        resp = super()._do_request(method, name, *args, **kwargs)
        if 'meta' not in resp or 'rc' not in resp['meta']:
            raise RESTException(f'{name} returned invalid response: resp: {resp}')

        if resp['meta']['rc'] == 'error':
            raise RESTException(f'{name} Failed: {resp["meta"]["msg"]}')

        return resp['data']
    # pylint: enable=arguments-differ

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._post(LOGIN_URL, {'username': self._username, 'password': self._password})

    def get_device_list(self):
        for client in self.list_clients():
            yield (UnifiAdapterDeviceType.client.name, client)

        for ap in self.list_devices():
            yield (UnifiAdapterDeviceType.network_device.name, ap)

    def list_clients(self) -> list:
        """
        List all available connected endpoints from the api
        """
        return self._get('s/{}/stat/sta'.format(self._site))

    def list_devices(self) -> list:
        """
        List all available (ubiquiti) devices from the api
        """
        return self._get('s/{}/stat/device'.format(self._site))
