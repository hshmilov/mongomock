import logging

from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class BamboohrConnection(RESTConnection):
    """ rest client for Bamboohr adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username:
            raise RESTException('No api key')

        try:
            self._get('employees/directory', do_basic_auth=True)
        except RESTException as e:
            message = f'Error connecting to BambooHR'
            logger.exception(message)
            raise ClientConnectionException(message)

    def get_users(self):
        response = self._get('employees/directory', do_basic_auth=True)
        try:
            yield from response['employees']
        except Exception:
            logger.exception(f'Problem fetching employee list')

    def get_device_list(self):
            # not a device adapter, so no need to do anything?
        yield from []
