import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from men_and_mice_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class MenAndMiceConnection(RESTConnection):
    """ rest client for MenAndMice adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='mmws/api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    @staticmethod
    def test_reachability(host, port=None, path='/', ssl=True, use_domain_path=False,
                          http_proxy=None, https_proxy=None):
        if host.lower().startswith('http://'):
            ssl = False
        return RESTConnection.test_reachability(
            host, port, path, ssl, use_domain_path, http_proxy, https_proxy)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        # test that data can be fetched
        self._get_entity_count('Devices')

    def _get_entity_count(self, url='Devices'):
        url_params = {
            'offset': 0,
            'limit': 1
        }
        try:
            response = self._get(url, do_basic_auth=True, url_params=url_params)['result']
            logger.debug(str(response))
        except RESTException as e:
            message = f'Failed to get entities from {self._domain} with user {self._username}: {str(e)}'
            logger.exception(message)
            raise RESTException(message)
        return response['totalResults']

    # pylint:disable=no-else-return
    def _fetch_entities(self, offset=0, url='Devices', retry_max=consts.MAX_RETRIES):
        url_params = {
            'offset': offset,
            'limit': consts.DEVICE_PER_PAGE,
        }
        # try to get thing.
        # if success, return.
        # if failed, increment retry_count and try again
        retry_count = 0
        while retry_count <= retry_max:
            try:
                results_raw = self._get(url, do_basic_auth=True, url_params=url_params)['result']
            except RESTException as e:
                message = f'Failed to get entities no. {url_params["offset"]} until ' \
                          f'{url_params["offset"] + consts.DEVICE_PER_PAGE} from {self._domain} ' \
                          f'with user {self._username}: {str(e)}'
                logger.exception(message)
                retry_count += 1
                if retry_count >= retry_max:
                    raise RESTException(message)
            else:
                return results_raw

    def get_device_list(self):
        device_count = self._get_entity_count('Devices')
        if device_count > consts.MAX_NUMBER_OF_DEVICES:
            logger.warning(f'Device count {device_count} is '
                           f'greater than {consts.MAX_NUMBER_OF_DEVICES}! '
                           f'Only fetching first {consts.MAX_NUMBER_OF_DEVICES} devices.')
            device_count = consts.MAX_NUMBER_OF_DEVICES
        for offset in range(0, device_count + 1, consts.DEVICE_PER_PAGE):
            try:
                devices = self._fetch_entities(offset, url='Devices')['devices'] or []
            except RESTException as e:
                logger.exception(str(e))
                devices = []
            yield from devices

    def get_users(self):
        """ Gets users """
        users_count = self._get_entity_count('Users')
        if users_count > consts.MAX_NUMBER_OF_DEVICES:
            logger.warning(f'User count {users_count} is '
                           f'greater than {consts.MAX_NUMBER_OF_DEVICES}! '
                           f'Only fetching first {consts.MAX_NUMBER_OF_DEVICES} users.')
            users_count = consts.MAX_NUMBER_OF_DEVICES
        for offset in range(0, users_count + 1, consts.DEVICE_PER_PAGE):
            try:
                users = self._fetch_entities(offset, url='Users')['users'] or []
            except RESTException as e:
                logger.exception(str(e))
                users = []
            yield from users
