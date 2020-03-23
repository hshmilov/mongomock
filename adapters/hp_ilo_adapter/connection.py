# pylint: disable=import-error
import logging
import redfish  # pylint: disable=import-error

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from hp_ilo_adapter.consts import REST_API_PATH, REST_API_AUTH, REST_API_TOTAL_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class HpIloConnection(RESTConnection):
    """ rest client for HpIlo adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    # pylint: disable=logging-format-interpolation
    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        try:
            self._redfish = redfish.LegacyRestClient(base_url=self._domain,
                                                     username=self._username,
                                                     password=self._password)
            self._redfish.login(auth=REST_API_AUTH)
            response = self._redfish.get(REST_API_PATH)
            if response.dict['error']:
                raise RESTException('Error: Server is unavailable or non-existent path')

        except Exception as err:
            logger.exception(f'Failed connecting, {str(err)}')
            raise

    def _paginated_get(self):
        try:
            # Get number of devices
            response = self._redfish.get(REST_API_PATH)
            total_devices = response.dict[REST_API_TOTAL_DEVICES]
        except Exception as err:
            logger.exception(f'Failed retrieving number of device to collect, Error: {str(err)}')
            raise

        # Perform the request per device
        device_number = 1
        try:
            while device_number < total_devices:
                response = self._redfish.get(f'{REST_API_PATH}/{device_number}')
                yield response.dict
                device_number += 1
        except Exception:
            logger.exception('Invalid request made')
            raise

    def _fetch_devices(self):
        try:
            yield from self._paginated_get()
        except RESTException as err:
            logger.exception(str(err))
            raise

    def get_device_list(self):
        yield from self._fetch_devices()
