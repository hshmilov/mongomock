import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from jumpcloud_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class JumpcloudConnection(RESTConnection):
    """ rest client for Jumpcloud adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._permanent_headers['x-api-key'] = self._apikey

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')
        response = self._get('systems',
                             url_params={'limit': DEVICE_PER_PAGE,
                                         'skip': 0})
        if not isinstance(response, dict) or not response.get('results'):
            raise RESTException('Empty results from server')

    def _get_endpoint_list(self, endpoint):
        response = self._get(endpoint,
                             url_params={'limit': DEVICE_PER_PAGE,
                                         'skip': 0})
        yield from response['results']
        total_count = response['totalCount']
        offset = DEVICE_PER_PAGE
        while offset < min(total_count, MAX_NUMBER_OF_DEVICES):
            try:
                response = self._get(endpoint,
                                     url_params={'limit': DEVICE_PER_PAGE,
                                                 'skip': offset})
                yield from response['results']
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem with offst {offset}')
                break

    def get_device_list(self):
        users_ids_dict = dict()
        for user_raw in self._get_endpoint_list('systemusers'):
            if user_raw.get('_id'):
                users_ids_dict[user_raw.get('_id')] = user_raw.get('username')
        for device_raw in self._get_endpoint_list('systems'):
            try:
                system_id = device_raw.get('_id')
                system_users = self._get(f'v2/systems/{system_id}/users')
                device_raw['system_users'] = []
                for system_user in system_users:
                    if users_ids_dict.get(system_user.get('id')):
                        device_raw['system_users'].append(users_ids_dict.get(system_user.get('id')))
            except Exception:
                logger.exception(f'Problem with getting user-device data for {device_raw}')
            yield device_raw

    def get_user_list(self):
        yield from self._get_endpoint_list('systemusers')
