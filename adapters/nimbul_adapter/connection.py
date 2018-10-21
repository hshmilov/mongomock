import logging

from axonius.clients.rest.connection import RESTConnection

logger = logging.getLogger(f'axonius.{__name__}')


class NimbulConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._permanent_headers = {'Content-Type': 'application/json-rpc', 'Accept': 'application/json',
                                   'Authorization': f'Token token={self._apikey}'}

    def _connect(self):
        self._get('instances')

    def get_device_list(self):
        for device in self._get('instances'):
            yield 'instance', device

        for device in self._get('unmanaged_instances'):
            yield 'unmanaged', device

    def get_user_list(self):
        for user in self._get('users'):
            yield 'user', user

        for user in self._get('apps'):
            yield 'app', user
