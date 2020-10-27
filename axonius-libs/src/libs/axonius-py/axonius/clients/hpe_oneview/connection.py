import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.hpe_oneview.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES,\
    URL_BASE_PREFIX, API_URL_SESSION_SUFFIX, API_URL_DEVICE_SUFFIX, API_VERSION

logger = logging.getLogger(f'axonius.{__name__}')


class HpeOneviewConnection(RESTConnection):
    """ rest client for HpeOneview adapter """

    def __init__(self, *args, username_domain: str, **kwargs):
        # A link to the documenation - https://developer.hpe.com/blog/hpe-oneview-api-version
        # Api version was mentioned in this link
        super().__init__(*args, url_base_prefix=URL_BASE_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json',
                                  'X-Api-Version': API_VERSION},
                         **kwargs)
        self._username_domain = username_domain

    def _connect(self):
        if not (self._username and self._password):
            raise RESTException('No username or password')
        body_params = {'userName': self._username,
                       'password': self._password,
                       'loginMsgAck': 'true'}
        if self._username_domain:
            body_params['authLoginDomain'] = self._username_domain
        response = self._post(API_URL_SESSION_SUFFIX, body_params=body_params)
        if not (isinstance(response, dict) and response.get('sessionID')):
            raise RESTException(f'Bad authentication response from server')
        self._session_headers['Auth'] = response.get('sessionID')
        url_params = {
            'expand': 'all',
            'start': 0,
            'count': 1
        }
        self._get(API_URL_DEVICE_SUFFIX, url_params=url_params)

    def _paginated_device_get(self):
        try:
            total_fetched_devices = 0

            url_params = {
                'expand': 'all',
                'start': 0,
                'count': DEVICE_PER_PAGE
            }
            while url_params['start'] < MAX_NUMBER_OF_DEVICES:
                try:
                    response = self._get(API_URL_DEVICE_SUFFIX, url_params=url_params)
                    if not (isinstance(response, dict) and isinstance(response.get('members'), list)):
                        logger.warning(f'Received invalid response for devices: {response}')
                        break

                    for device in response.get('members'):
                        if isinstance(device, dict):
                            yield device
                            total_fetched_devices += 1

                    if total_fetched_devices >= MAX_NUMBER_OF_DEVICES:
                        logger.info(f'Exceeded max number of Devices {total_fetched_devices}')
                        break

                    if url_params['count'] < len(response.get('members')):
                        logger.info(f'Done Device pagination, got {len(response.get("members"))} / {DEVICE_PER_PAGE}')
                        break
                    url_params['start'] += len(response.get('members'))
                except Exception:
                    logger.exception(f'Problem at offset: {url_params["start"]}')

            logger.info(f'Got total of {total_fetched_devices} devices')
        except Exception:
            logger.exception(f'Invalid request made while paginating Devices')
            raise

    def get_device_list(self):
        try:
            yield from self._paginated_device_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
