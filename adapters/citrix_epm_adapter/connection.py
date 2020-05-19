import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from citrix_epm_adapter.consts import DEVICES_PER_PAGE, MAX_NUMBER_OF_DEVICES, \
    API_V1_ENDPOINT, AUTH_ENDPOINT, DEVICE_ENDPOINT

logger = logging.getLogger(f'axonius.{__name__}')


class CitrixEpmConnection(RESTConnection):
    """ REST client for Citrix Endpoint Management adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         url_base_prefix=API_V1_ENDPOINT,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    # pylint: disable=no-else-return
    def _get_token(self):
        """ Grab an API token from username and password. """
        if not self._username or not self._password:
            raise RESTException('No username or password.')

        params = {'login': self._username, 'password': self._password}
        response = self._post(AUTH_ENDPOINT, body_params=params)

        if not isinstance(response.get('auth_token'), str):
            logger.error(f'Token fetch failed: {response}')
            raise RESTException('Unable to fetch the authentication token')

        return response.get('auth_token')

    def _connect(self):
        self._token = self._get_token()
        self._session_headers['auth_token'] = self._token

        params = {'start': '0', 'limit': '1'}
        response = self._post(DEVICE_ENDPOINT, body_params=params)
        if not response.get('message') == 'Success':
            logger.warning(f'Unable to connect to the authentication '
                           f'endpoint: {response}')
            raise RESTException(f'Unable to fetch device data: {response}')

    def get_device_list(self):
        offset = 0
        limit = DEVICES_PER_PAGE

        # these params are used for the initial call ONLY
        params = {'start': offset, 'limit': limit, 'enableCount': 'true',
                  'sortOrder': 'ASC', 'sortColumn': 'ID'}
        try:
            response = self._post(DEVICE_ENDPOINT, body_params=params)
            if not isinstance(response, dict):
                logger.warning(f'TypeError (expected a dict, got a'
                               f' {type(response)}: {response}')
                return

            devices_list = response.get('filteredDevicesDataList')
            if isinstance(devices_list, list):
                yield from devices_list

            offset = DEVICES_PER_PAGE

            matched_records = response.get('matchedRecords')
            if not isinstance(matched_records, int):
                logger.warning(f'Matched Records is not an int: {type(matched_records)}')
                return

            total_devices = matched_records or MAX_NUMBER_OF_DEVICES

            while offset < min(MAX_NUMBER_OF_DEVICES, total_devices):
                # these params are used for all calls after the first
                params = {'start': offset, 'limit': limit,
                          'sortOrder': 'ASC', 'sortColumn': 'ID'}
                try:
                    response = self._post(DEVICE_ENDPOINT, body_params=params)
                    if not isinstance(response, dict):
                        logger.warning(f'TypeError (expected a dict, got a'
                                       f' {type(response)}: {response}')
                        break

                    devices_list = response.get('filteredDevicesDataList')
                    if isinstance(devices_list, list):
                        yield from devices_list

                    if len(devices_list) < limit:
                        logger.warning(f'Found {len(devices_list)}. Breaking out.')
                        break

                except Exception as err:
                    logger.exception(f'Pagination error at {offset}: str({err})')
                    # fallthrough to bypass errors in data returned from POST.
                    # Some pages return HTTP 500.

                offset += DEVICES_PER_PAGE

        except Exception as err:
            logger.debug(f'Response: {response}', exc_info=True)
            logger.exception(f'Unable to acquire device list: str({err})')
