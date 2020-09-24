import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.ivanti_endpoint_security.consts import API_URL_PREFIX, ENDPOINT_URL_SUFFIX, DEVICE_PER_PAGE, \
    MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class IvantiEndpointSecurityConnection(RESTConnection):
    """ rest client for IvantiEndpointSecurity adapter """

    def __init__(self, *args, token: str,  **kwargs):
        super().__init__(*args, url_base_prefix=API_URL_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._token = token

    def _connect(self):
        if not self._token:
            raise RESTException('No API Token')

        try:
            # Not needed, keeping as if Ivanti will come to their senses.
            self._session_headers['Authorization'] = f'rest_api_key={self._token}'

            url_params = {
                'api_key': self._token,
                '$top': 1
            }

            self._get(ENDPOINT_URL_SUFFIX, url_params=url_params)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _paginated_get_endpoints(self):
        try:
            total_endpoints = 0

            url_params = {
                'api_key': self._token,
                '$top': DEVICE_PER_PAGE,
                '$skip': 0
            }

            while url_params['$skip'] < MAX_NUMBER_OF_DEVICES:
                response = self._get(ENDPOINT_URL_SUFFIX, url_params=url_params)

                if not (isinstance(response, dict) and isinstance(response.get('value'), list)):
                    logger.warning(f'Received invalid response while getting endpoints {response}')
                    return

                current_fetch_length = len(response.get('value'))

                for endpoint in response.get('value'):
                    if isinstance(endpoint, dict):
                        yield endpoint
                        total_endpoints += 1

                    if total_endpoints >= MAX_NUMBER_OF_DEVICES:
                        logger.info(f'Exceeded max number of endpoints, {total_endpoints} / {MAX_NUMBER_OF_DEVICES}')
                        break

                    if current_fetch_length < DEVICE_PER_PAGE:
                        logger.info(f'Finished paginating, last page received '
                                    f'{current_fetch_length} / {DEVICE_PER_PAGE}')
                        break

                url_params['$skip'] += DEVICE_PER_PAGE

            logger.info(f'Got total of {total_endpoints} Endpoints')
        except Exception:
            logger.exception(f'Invalid request made while paginating endpoints')
            raise

    def get_device_list(self):
        try:
            yield from self._paginated_get_endpoints()
        except RESTException as err:
            logger.exception(str(err))
            raise
