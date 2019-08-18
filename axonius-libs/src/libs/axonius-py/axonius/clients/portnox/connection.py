import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class PortnoxConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='arm/v1',
                         headers={'Accept': 'application/json'}, **kwargs)

    def _connect(self):
        pass

    def get_device_list(self):
        pass

    def get_portnox_id_information(self, portnox_id):
        response = self._get(f'device/{portnox_id}',
                             do_basic_auth=True)
        if 'Error' in response:
            err_msg = response['Error'] + ';' + response.get('AdditionalDetails')
            raise RESTException(err_msg)
        return response
