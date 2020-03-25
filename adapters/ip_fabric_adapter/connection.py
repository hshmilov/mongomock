import logging
from datetime import datetime, timedelta
from functools import partialmethod

import requests
# pylint: disable=import-error
from retrying import retry
from jose import jwt

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from ip_fabric_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class IpFabricRefreshTokenRetryException(Exception):
    """ Exception used to retry a request with refreshed token"""


class IpFabricConnection(RESTConnection):
    """ rest client for IpFabric adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='/api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._access_token = None
        self._refresh_token = None
        self._last_refresh_time = None

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        # Contains both login and permission check and validity
        self.__login()

    @staticmethod
    def _assert_access_token_validity_and_permissions(access_token):
        # parse retrieved access token and make sure it has sufficient permissions
        try:
            payload = jwt.get_unverified_claims(access_token)
        except Exception:
            raise RESTException(f'Invalid access token returned on login.')

        # See: https://docs.ipfabric.io/api/#header-authorization
        user_permissions = payload.get('scope') or []
        if 'read' not in user_permissions:
            raise RESTException(f'Missing required "read" permissions')

    def __login(self):
        # Note: Invalid credentials would result in HTTPError(401)
        response = self._post('auth/login', body_params={
            'username': self._username,
            'password': self._password,
        }, authenticated=False)

        access_token = response.get('accessToken')
        refresh_token = response.get('refreshToken')
        if not (access_token and refresh_token):
            raise RESTException(f'Invalid tokens received for response: {response}')

        self._assert_access_token_validity_and_permissions(access_token)

        self._access_token = access_token
        self._refresh_token = refresh_token
        self._last_refresh_time = datetime.now()
        logger.debug('Logged in succesfully')

    def __refresh_token(self):
        if not (self._refresh_token and self._last_refresh_time):
            raise RESTException(f'Missing refresh token')

        # Make sure refresh token is still valid (within 24 hours of last refresh)
        if (datetime.now() - self._last_refresh_time) > timedelta(hours=consts.INTERVAL_REFRESH_TOKEN_HRS):
            self._connect()
            return

        # Note: Invalid refresh_token would result in HTTPError(401)
        response = self._post('auth/token', body_params={
            'refreshToken': self._refresh_token
        }, authenticated=False)

        access_token = response.get('accessToken')
        if not access_token:
            raise RESTException(f'Invalid access token receivied for response: {response}')
        self._assert_access_token_validity_and_permissions(access_token)
        self._access_token = access_token
        self._last_refresh_time = datetime.now()

    #pylint: disable=arguments-differ
    @retry(stop_max_attempt_number=2,
           retry_on_exception=lambda exc: isinstance(exc, IpFabricRefreshTokenRetryException))
    def _do_request(self, *args, authenticated: bool = True, **kwargs):
        if authenticated:
            if not self._access_token:
                raise RESTException('Must connect first')
            # refresh access token if more than 30 mins passsed
            if (datetime.now() - self._last_refresh_time) > timedelta(minutes=consts.INTERVAL_ACCESS_TOKEN_MIN):
                self.__refresh_token()
            # Note: This is undocumented and found thanks to Postman manual trials
            kwargs.setdefault('extra_headers', {})['Authorization'] = f'Bearer {self._access_token}'
        return super()._do_request(*args, **kwargs)

    @staticmethod
    def _handle_http_error(error: requests.HTTPError):

        try:
            rp = error.response.json()
        except Exception:
            RESTConnection._handle_http_error(error)
            raise error  # unreachable mock exception for code inspector

        error_code = rp.get('code')
        if error_code:
            if error_code == 'API_EXPIRED_ACCESS_TOKEN':
                # Note: for server-side expired / revoked(blacklisted) token cases
                raise IpFabricRefreshTokenRetryException()
            raise RESTException(f'IP Fabric Error: {rp}')

        super()._handle_http_error(error)

    #pylint: disable=arguments-differ
    def _handle_response(self, response, *args, raise_for_status=True, **kwargs):

        # This wrapper was used to call this class's self._handle_http_error because it's staticmethod
        try:
            if raise_for_status:
                response.raise_for_status()
        except requests.HTTPError as e:
            self._handle_http_error(e)

        return super()._handle_response(response, *args, raise_for_status=raise_for_status, **kwargs)

    def _paginated_request(self, *args, **kwargs):
        pagination_params = kwargs.setdefault(
            'url_params' if (kwargs.get('method') or args[0]) == 'GET'
            else 'body_params', {}).setdefault('pagination', {})
        pagination_params.setdefault('limit', consts.DEVICE_PER_PAGE)
        curr_offset = pagination_params.setdefault('start', 0)
        # Note: initial value used only for initial while iteration
        total_count = curr_offset
        try:
            while curr_offset <= total_count:
                pagination_params['start'] = curr_offset
                response = self._do_request(*args, **kwargs)

                yield from response.get('data') or []

                meta = response.get('_meta') or {}
                if not meta:
                    logger.debug(f'No "_meta" found, halting pagination after {curr_offset}/{total_count}')
                    return

                try:
                    curr_count = int(meta.get('size'))
                    # API inconsistency, I really hate IP FABRIC!
                    total_count = int(meta.get('totalCount') or meta.get('count') or 0)
                except (ValueError, TypeError):
                    logger.exception(f'Received invalid meta values {meta} after/on {curr_offset}/{total_count}')
                    return

                if total_count <= 0:
                    logger.info(f'Done paginated request after {curr_offset}/{total_count}')
                    return

                curr_offset = curr_offset + curr_count
        except Exception:
            logger.exception(f'Failed paginated request after {curr_offset}/{total_count}')

    paginated_post = partialmethod(_paginated_request, 'POST')

    def get_device_list(self):
        yield from self.paginated_post('tables/inventory/devices', body_params={
            'snapshot': '$last',
            'columns': consts.DEVICE_INVENTORY_COLUMNS,
        })
