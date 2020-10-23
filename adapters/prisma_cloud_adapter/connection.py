import logging
import datetime

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from prisma_cloud_adapter.consts import TOKEN_VALID_TIME, DEVICE_PER_PAGE, QUERIES, CloudInstances, BODY_PARAMS

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=invalid-triple-quote
class PrismaCloudConnection(RESTConnection):
    """ REST client for PrismaCloud adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._token = None
        self._session_refresh = None

    def _get_token_with_credentials(self):
        try:
            body_params = {
                'username': self._username,
                'password': self._password
            }
            response = self._post('login', body_params=body_params)

            if not isinstance(response, dict) or 'token' not in response:
                raise RESTException(f'Login failed, received invalid response: {response}')

            self._session_refresh = datetime.datetime.now() + datetime.timedelta(seconds=(TOKEN_VALID_TIME - 300))
            self._session_headers = {
                'x-redlock-auth': response.get('token')
            }

        except Exception:
            raise RESTException(f'Error: Could not login to the server, please check domain or credentials')

    def _refresh_token(self):
        try:
            if self._session_refresh and self._session_refresh > datetime.datetime.now():
                return

            response = self._get('auth_token/extend')
            if not isinstance(response, dict) or 'token' not in response:
                raise RESTException(f'Refresh token failed, received invalid response: {response}')

            self._session_refresh = datetime.datetime.now() + datetime.timedelta(seconds=(TOKEN_VALID_TIME - 300))
            self._session_headers = {
                'x-redlock-auth': response.get('token')
            }

        except Exception:
            raise ValueError(f'Error: Failed getting token, invalid request was made.')

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        try:
            self._get_token_with_credentials()
            body_params = {
                'limit': 1,
                'query': QUERIES[0][0]
            }
            self._post('search/config', body_params=body_params)
        except Exception:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials')

    # pylint: disable=too-many-nested-blocks,logging-format-interpolation
    def _paginated_get(self, hours_filter: int):
        try:
            for query, cloud_type in QUERIES:
                total_object_fetched = 0
                body_params = {
                    'limit': DEVICE_PER_PAGE,
                    'query': query,
                    'timeRange': {
                        'type': 'relative',
                        'value': {
                            'amount': hours_filter,
                            'unit': 'hour'
                        }
                    }
                }
                self._refresh_token()
                response = self._post('search/config', body_params=body_params)

                if not (isinstance(response, dict) and isinstance(response.get('data'), dict)):
                    logger.warning(f'Received invalid initial response for cloud {cloud_type}: {response}')
                    continue

                for instance in (response.get('data').get('items') or []):
                    yield instance, cloud_type
                    total_object_fetched += 1

                next_page_token = response.get('data').get('nextPageToken')

                while next_page_token:
                    body_params = {
                        'limit': DEVICE_PER_PAGE,
                        'pageToken': next_page_token
                    }
                    self._refresh_token()
                    response = self._post('search/config/page', body_params=body_params)
                    if not (isinstance(response, dict) and isinstance(response.get('items'), list)):
                        logger.warning(f'Received invalid response {response}')
                        break
                    for instance in response.get('items'):
                        yield instance, cloud_type
                        total_object_fetched += 1

                    next_page_token = response.get('nextPageToken')

                logger.info(f'Got total of {total_object_fetched} of {cloud_type}')
        except Exception as err:
            logger.exception(f'Invalid request made, {str(err)}')
            raise

    def _get_policies_ids(self):
        try:
            total_fetched_policies = 0
            body_params = BODY_PARAMS
            body_params['filters'].append({
                'name': 'alert.status',
                'value': 'open',
                'operator': '='
            })

            policies_ids = set()
            self._refresh_token()
            response = self._post('alert/policy',  body_params=body_params)

            if not isinstance(response, list):
                logger.warning(f'Received invalid alert/policy: {response}')
                return []

            for policy in response:
                if policy.get('policyId'):
                    policies_ids.add(policy.get('policyId'))
                    total_fetched_policies += 1

            logger.info(f'Got total of {total_fetched_policies} policies')
            return list(policies_ids)
        except Exception as err:
            logger.exception(f'Failed fetching Security Group policies ids, {str(err)}')
            return []

    def _paginated_security_groups(self):
        policies_ids = self._get_policies_ids()
        if not policies_ids:
            return

        try:
            total_security_groups = 0
            existing_devices = {}
            for policy_id in policies_ids:
                body_params = BODY_PARAMS
                body_params['limit'] = DEVICE_PER_PAGE
                body_params['sortBy'] = ['lastSeen:desc']
                body_params['filters'].append({
                    'name': 'policy.id',
                    'value': policy_id,
                    'operator': '='
                })
                while True:
                    self._refresh_token()
                    response = self._post('v2/alert', body_params=body_params)

                    if not isinstance(response.get('items'), list):
                        break

                    for item in response.get('items'):
                        if item.get('lastSeen') and item.get('resource'):
                            item['resource']['lastSeen'] = item.get('lastSeen')
                        if not isinstance(item.get('resource'), dict):
                            continue
                        if item.get('resource').get('rrn') and \
                                existing_devices.get(item.get('resource').get('rrn')):
                            continue
                        if item.get('resource').get('rrn'):
                            existing_devices[item.get('resource').get('rrn')] = True
                        yield item.get('resource'), CloudInstances.SECURITYGROUP.value
                        total_security_groups += 1

                    if not response.get('nextPageToken'):
                        break

                    next_page_token = response.get('nextPageToken')
                    body_params = {
                        'limit': DEVICE_PER_PAGE,
                        'pageToken': next_page_token
                    }
            logger.info(f'Got total of {total_security_groups} of security groups')
        except Exception as err:
            logger.exception(f'Invalid request made, {str(err)}')
            raise

    # pylint: disable=arguments-differ
    def get_device_list(self, hours_filter: int):
        try:
            yield from self._paginated_get(hours_filter=hours_filter)
        except RESTException as err:
            logger.exception(f'Failed paginating Prisma Cloud cloud devices. {str(err)}')

        try:
            yield from self._paginated_security_groups()
        except RESTException as err:
            logger.exception(f'Failed paginating Prisma Cloud security groups. {str(err)}')
