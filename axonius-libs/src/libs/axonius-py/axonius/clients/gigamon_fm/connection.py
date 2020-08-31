import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

from .consts import BASE_URL_PREFIX, VERSION_URL_SUFFIX, NODES_URL_SUFFIX, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class GigamonFmConnection(RESTConnection):
    """ rest client for GigamonFm adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix=BASE_URL_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not (self._username and self._password):
            raise RESTException('No username or password')

        try:
            response = self._get(VERSION_URL_SUFFIX, do_basic_auth=True)
            if not isinstance(response, dict):
                raise Exception(f'Unexpected format of the API version: {str(response)}')
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _get_devices(self):
        try:
            response = self._get(VERSION_URL_SUFFIX, do_basic_auth=True)
            if not isinstance(response, dict):
                raise Exception(f'Could not fetch API version, response: {str(response)}')

            api_version = response.get('apiVersion')
            if not api_version:
                raise Exception(f'Empty api version received: {str(api_version)}')

            response = self._get(NODES_URL_SUFFIX.format(api_version), do_basic_auth=True)
            if not isinstance(response.get('nodes'), list):
                raise Exception(f'Could not fetch devices, response: {str(response)}')

            devices = response.get('nodes')
            truncated_devices = devices[: MAX_NUMBER_OF_DEVICES]
            total_devices = 0

            if len(devices) > len(truncated_devices):
                logger.warning(f'Total devices amount is bigger than the maximum allowed, '
                               f'Only {len(truncated_devices)} out of {len(devices)} handled.')

            for raw_device in truncated_devices:
                if not isinstance(raw_device, dict):
                    logger.warning(f'Got a device with unexpected type! raw device:{str(raw_device)}')
                    continue
                yield raw_device
                total_devices += 1

            logger.info(f'Got total of {total_devices} out of {len(devices)}')
        except Exception as err:
            logger.exception(f'Error occurred while fetching devices: {str(err)}')

    def get_device_list(self):
        try:
            yield from self._get_devices()
        except RESTException as err:
            logger.exception(str(err))
            raise
