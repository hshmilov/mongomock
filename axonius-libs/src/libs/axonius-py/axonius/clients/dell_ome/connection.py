import logging

from typing import Optional

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.dell_ome.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES, TOKEN_API_URL_SUFFIX, \
    TOKEN_API_SESSION_TYPE, URL_BASE_PREFIX, DEVICE_API_URL_SUFFIX, DEVICE_INVENTORY_API_URL_SUFFIX, EXTRA_INVENTORY
from axonius.utils.parsing import int_or_none

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class DellOmeConnection(RESTConnection):
    """ rest client for DellOme adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix=URL_BASE_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _set_token(self):
        try:
            body_params = {
                'UserName': self._username,
                'Password': self._password,
                'SessionType': TOKEN_API_SESSION_TYPE
            }
            response = self._post(TOKEN_API_URL_SUFFIX,
                                  body_params=body_params,
                                  use_json_in_response=False,
                                  return_response_raw=True)
            if not response.headers.get('x-auth-token'):
                raise RESTException(f'Failed receiving token while trying to connect. {str(response)}')

            self._session_headers['X-Auth-Token'] = response.headers.get('x-auth-token')
        except Exception as e:
            logger.exception('Error: Failed getting token, invalid request was made.')
            raise RESTException(f'Error: Failed getting token, invalid request was made. {str(e)}')

    def _connect(self):
        if not (self._username and self._password):
            raise RESTException('No username or password')

        try:
            self._set_token()

            url_params = {
                'top': 1
            }
            self._get(DEVICE_API_URL_SUFFIX, url_params=url_params)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _paginated_get_devices_by_id(self):
        try:
            total_fetched_devices = 0

            devices_by_id = {}

            url_params = {
                'skip': 0,
                'top': DEVICE_PER_PAGE
            }
            while total_fetched_devices < MAX_NUMBER_OF_DEVICES:
                response = self._get(DEVICE_API_URL_SUFFIX, url_params=url_params)
                if not (isinstance(response, dict) and
                        isinstance(response.get('value'), list)):
                    logger.warning(f'Received invalid response for devices: {response}')
                    return devices_by_id

                for device in response.get('value'):
                    if isinstance(device, dict) and device.get('id'):
                        devices_by_id[device.get('id')] = device
                        total_fetched_devices += 1

                if total_fetched_devices >= MAX_NUMBER_OF_DEVICES:
                    logger.info(f'Exceeded max number {MAX_NUMBER_OF_DEVICES} of devices')
                    break

                current_fetch = int_or_none(response.get('@odata.count')) or len(response.get('value'))
                if current_fetch < url_params['top']:
                    logger.info(f'Finished pagination, last page received '
                                f'{current_fetch} / {url_params["top"]}')
                    break

                url_params['skip'] += DEVICE_PER_PAGE

            logger.info(f'Got total of {total_fetched_devices} devices')
            return devices_by_id
        except Exception:
            logger.exception(f'Invalid request made while paginating devices')
            return devices_by_id

    def _paginated_get_devices_inventory(self, async_chunks: int):
        try:
            total_fetched_devices_inventories = 0
            device_raw_requests = []

            devices_by_id = self._paginated_get_devices_by_id()

            for device_id, device_raw in devices_by_id.items():
                device_raw_requests.append({
                    'name': DEVICE_INVENTORY_API_URL_SUFFIX.format(device_id=device_id)
                })

            for device_id, response in zip(
                    devices_by_id.keys(),
                    self._async_get(device_raw_requests, retry_on_error=True, chunks=async_chunks)):
                if not self._is_async_response_good(response):
                    logger.error(f'Async response returned bad: {response}')
                    continue

                if not (isinstance(response, dict) and isinstance(response.get('value'), list)):
                    logger.warning(f'Invalid response returned: {response}')
                    continue

                device_raw = devices_by_id[device_id]
                device_raw[EXTRA_INVENTORY] = response.get('value')
                yield device_raw
                total_fetched_devices_inventories += 1

            logger.info(f'Fetched total of {total_fetched_devices_inventories} inventories / {len(devices_by_id)}')
        except Exception:
            logger.exception(f'Invalid request made while paginating devices inventory')
            raise

    # pylint: disable=arguments-differ
    def get_device_list(self, async_chunks: Optional[int] = None):
        try:
            yield from self._paginated_get_devices_inventory(async_chunks)
        except RESTException as err:
            logger.exception(str(err))
            raise
