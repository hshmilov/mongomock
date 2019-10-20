import datetime
import logging
import uuid

import jwt

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from cylance_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


def blockify(iter_, blksize):
    result = []
    for item in iter_:
        result.append(item)
        if len(result) == blksize:
            yield result
            result = []


class CylanceConnection(RESTConnection):
    def __init__(self, *args, app_id: str = '', tid: str = '', app_secret: str = '', **kwargs):
        """ Initializes a connection to Cylance using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for Cylance
        """
        super().__init__(*args, **kwargs)
        self._app_id = app_id
        self._app_secret = app_secret
        self._tid = tid
        self._tokens = {}
        self._token_times = {}

    def _create_token_for_scopre(self, scope, force_get_token=False):
        # pylint: disable=line-too-long
        if force_get_token or (self._token_times.get(scope) and (datetime.datetime.now() - self._token_times.get(scope) < datetime.timedelta(minutes=(consts.NUMBER_OF_MINUTES_UNTIL_TOKEN_TIMEOUT - 1)))):
            return
        if self._tid is not None and self._app_id is not None and self._app_secret is not None:
            int((datetime.datetime.now() - datetime.datetime(1970, 1, 1)).total_seconds())
            epoch_time = int((datetime.datetime.now() - datetime.datetime(1970, 1, 1)).total_seconds())
            epoch_timeout = epoch_time + 60 * consts.NUMBER_OF_MINUTES_UNTIL_TOKEN_TIMEOUT
            claims = {'exp': epoch_timeout, 'iat': epoch_time, 'iss': 'http://cylance.com', 'sub': self._app_id,
                      'tid': self._tid, 'jti': str(uuid.uuid4()), 'scp': scope}
            auth_token_encoded = jwt.encode(claims, self._app_secret, algorithm='HS256').decode('utf-8')
            response = self._post('auth/v2/token', body_params={'auth_token': auth_token_encoded})
            if 'access_token' not in response:
                raise RESTException(f'Couldnt get token from response {response}')
            self._tokens[scope] = response['access_token']
            self._token_times[scope] = datetime.datetime.now()
        else:
            raise RESTException('No tid or app secrer or app id')

    def _connect(self):
        """ Connects to the service """
        self._create_token_for_scopre('device:list')

    def _get_ids_bulks(self, endpoint, scope):
        self._create_token_for_scopre(scope)
        page_num = 1
        self._session_headers['Authorization'] = 'Bearer ' + self._tokens[scope]
        devices_response_raw = self._get(
            f'{endpoint}/v2', url_params={'page_size': consts.DEVICE_PER_PAGE, 'page': str(page_num)})
        yield [basic_device.get('id') for basic_device in devices_response_raw.get('page_items', [])]
        total_pages = devices_response_raw.get('total_pages', 0)  # Waiting to know to right fields
        first_try_to_refresh = True
        while page_num < total_pages:
            try:
                page_num += 1
                self._create_token_for_scopre(scope)
                self._session_headers['Authorization'] = 'Bearer ' + self._tokens[scope]
                yield [basic_device.get('id') for basic_device in
                       self._get(f'{endpoint}/v2', url_params={'page_size': consts.DEVICE_PER_PAGE,
                                                               'page': str(page_num)}).get('page_items', [])]
            except Exception as e:
                if first_try_to_refresh and '401' in str(e):
                    self._create_token_for_scopre(scope, force_get_token=True)
                    first_try_to_refresh = False
                    page_num -= 1
                logger.exception(f'Problem fetching page number {str(page_num)}')

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _get_results_of_entity(self, endpoint, scope_list, scope_read, second_endpoint=None, second_scope=None):
        # Now use asyncio to get all of these requests
        for bulk_number, bulk_ids in enumerate(self._get_ids_bulks(endpoint, scope_list)):
            # We must refresh the token sometimes so we won't get to token timeout
            failed_second_scope_first_block = False
            self._create_token_for_scopre(scope_read)
            if second_scope:
                try:
                    self._create_token_for_scopre(second_scope)
                except Exception:
                    if bulk_number == 0:
                        failed_second_scope_first_block = True
                    logger.exception(f'Coudld get second scope')
                    self._tokens[second_scope] = ''
            async_requests = []
            for device_id in bulk_ids:
                try:
                    if not device_id:
                        logger.warning(f'Bad device')
                        continue
                    async_requests.append({'name': f'{endpoint}/v2/{device_id}'})
                    if second_endpoint and not failed_second_scope_first_block:
                        async_requests.append({'name': f'{second_endpoint}/v2/{device_id}/{second_endpoint}',
                                               'headers': {'Authorization': 'Bearer ' + self._tokens[second_scope]}})
                except Exception:
                    logger.exception(f'Got problem with id {device_id}')
            self._session_headers['Authorization'] = 'Bearer ' + self._tokens[scope_read]
            if second_endpoint:
                if not failed_second_scope_first_block:
                    yield from blockify(self._async_get(async_requests), 2)
                else:
                    for device_raw in self._async_get(async_requests):
                        yield device_raw, None
            else:
                yield from self._async_get(async_requests)

    def get_device_list(self):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses Cylance's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        policies_dict = {}
        try:
            policies_raw = self._get_results_of_entity('policies', 'policy:list', 'policy:read')
            for policy_raw in policies_raw:
                if not self._is_async_response_good(policies_raw):
                    continue
                if policy_raw.get('policy_id'):
                    policies_dict[policy_raw.get('policy_id')] = policy_raw
        except Exception:
            logger.exception(f'Problem getting policies')
        for device_raw, zone_raw in self._get_results_of_entity('devices', 'device:list', 'device:read',
                                                                'zones', 'zone:list'):
            if not self._is_async_response_good(device_raw):
                continue
            if zone_raw is not None and self._is_async_response_good(zone_raw):
                device_raw['zone_raw'] = zone_raw
            else:
                logger.debug(f'Async response returned bad, its {zone_raw}')
            yield device_raw, policies_dict
