import logging
# pylint: disable = import-error
from infoblox_netmri import InfobloxNetMRI
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class InfobloxNetmriConnection(RESTConnection):
    """ rest client for InfobloxNetmri adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._client = None

    def _connect(self):
        # AUTOADAPTER
        if not self._username or not self._password:
            raise RESTException('No username or password')
        if self._client:
            return
        try:
            self._client = InfobloxNetMRI(self._domain, self._username, self._password, ssl_verify=self._verify_ssl)

        except Exception:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials')

    def _paginated_device_get(self):
        # AUTOADAPTER
        try:
            yield from self._client.api_request('devices/index', {'limit': 10}).get('devices') or []
        except Exception:
            logger.exception(f'Invalid request made while paginating devices')
            raise

    def close(self):
        self._client = None
        return super().close()

    def get_device_list(self):
        # AUTOADAPTER
        try:
            yield from self._paginated_device_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
