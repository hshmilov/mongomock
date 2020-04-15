import logging
from itertools import repeat
from functools import partialmethod

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException, RESTRequestException
from digicert_certcentral_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class DigicertCertcentralConnection(RESTConnection):
    """ rest client for DigicertCertcentral adapter """

    def __init__(self, *args, api_key, account_id, division_ids=None, **kwargs):
        super().__init__(*args, domain=consts.REST_SERVICES_API, use_domain_path=True,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._api_key = api_key
        self._account_id = account_id
        self._division_ids = division_ids or []
        self._permissions = {}

    def _update_headers(self):
        self._session_headers = {
            'X-DC-DEVKEY': self._api_key,
        }

    def _refresh_permissions(self):
        try:
            response = self._get(consts.REST_ENDPOINT_AUTH)
        except RESTException:
            logger.exception(f'Failed to get permissions')
            raise

        authorizations = response.get('authorizations')
        if not isinstance(authorizations, list):
            message = f'No permissions returned in response {response}'
            logger.error(message)
            raise RESTException(message)

        self._permissions = {authorization['permission']: authorization['authorized']
                             for authorization in authorizations
                             if (isinstance(authorization, dict) and
                                 all(map(authorization.__contains__, ['permission', 'authorized'])))}

    def _connect(self):
        if not self._api_key:
            raise RESTException('No API Key')
        self._update_headers()
        self._refresh_permissions()

        missing_permissions = [rp for rp in consts.REQUIRED_PERMISSIONS if rp not in self._permissions]
        if len(missing_permissions) == len(consts.REQUIRED_PERMISSIONS):
            raise RESTException(f'Missing required permissions: {consts.REQUIRED_PERMISSIONS}')
        if missing_permissions:
            logger.warning(f'Missing partial permissions: {missing_permissions}')

    @staticmethod
    def _handle_http_error(error):
        try:
            super()._handle_http_error(error)
        except RESTRequestException as e:

            # Best effort error handling of the official Digicert error flow
            # See: https://dev.digicert.com/errors/
            try:
                response = error.response.json()
                if response.get('errors'):
                    raise RESTException(f'Digicert Errors: {response["errors"]}. {str(e)}')
            except Exception:
                pass

            raise e

    # pylint: disable=arguments-differ
    def _handle_response(self, *args, **kwargs):

        response = super()._handle_response(*args, **kwargs)
        if not isinstance(response, dict):
            return response

        # Undocumented field-encountered error flow in Digicert Certcentral's Discovery API
        if response.get('error'):
            raise RESTException(f'Digicert Error: {response["error"]}')

        if response.get('data'):
            return response['data']

        return response

    def _paginated_request(self, *args, offset_field_name: str,  initial_offset: int = 0, **kwargs):

        # Initiate pagination and body params (if not given)
        # Note: body_params is equivalent to kwargs['body_params'] because its an object -
        #           affecting body_params affects kwargs' one as well.
        body_params = kwargs.setdefault('body_params', {})
        curr_offset = body_params.setdefault(offset_field_name, initial_offset)
        total_count = None
        while (total_count is None) or (curr_offset < min(total_count, consts.MAX_NUMBER_OF_DEVICES)):
            # Perform the request per page
            try:
                response = self._do_request(*args, **kwargs)
            except RESTException:
                logger.exception(f'Failed paginated request on {curr_offset}/{total_count}.')
                raise

            # (PEP-342) values set by generator.send method
            curr_count, total_count = (yield response)

            if curr_count <= 0 or total_count <= 0:
                logger.error(f'Invalid count {curr_count}/{total_count} encountered after {curr_offset} offset.')
                return

            curr_offset += curr_count
            body_params[offset_field_name] = curr_offset

    def _paginated_discovery_request(self, *args, **kwargs):

        # Initiate pagination and body params (if not given)
        # Note: body_params is equivalent to kwargs['body_params'] because its an object -
        #           affecting body_params affects kwargs' one as well.
        body_params = kwargs.setdefault('body_params', {})
        body_params.setdefault('pageSize', consts.DEVICE_PER_PAGE)

        # Note: The API specifies its default as 1, I assume it is 1-based.
        gen_paginated_request = self._paginated_request(*args, offset_field_name='startIndex',
                                                        initial_offset=1, **kwargs)

        # retrieve initial response
        response = next(gen_paginated_request)
        while response:

            try:
                curr_count, total_count = (int(response.get(field, 0)) for field in ['currentCount', 'totalCount'])
            except ValueError:
                logger.exception(f'Invalid count values in response {response}')
                return

            response = gen_paginated_request.send((curr_count, total_count))

    def _paginated_services_request_iter(self, *args, pagination_field: str, **kwargs):

        # Initiate pagination and body params (if not given)
        # Note: body_params is equivalent to kwargs['body_params'] because its an object -
        #           affecting body_params affects kwargs' one as well.
        body_params = kwargs.setdefault('body_params', {})
        body_params.setdefault('limit', consts.DEVICE_PER_PAGE)

        gen_paginated_request = self._paginated_request(*args, offset_field_name='offset', **kwargs)
        curr_count = 0
        total_count = 0
        # Note: initial value for gen.send (equivalent to next())
        curr_total_tup = None
        while True:
            try:
                response = gen_paginated_request.send(curr_total_tup)
            except StopIteration:
                response = None

            if not response:
                logger.debug(f'Done paginated services request after {curr_count}/{total_count}')
                return

            page = response.get('page')
            if not isinstance(page, dict):
                logger.error(f'Unable to paginate without page details. response: {response}')
                return

            pagination_value = response.get(pagination_field)
            if not pagination_value:
                logger.info(f'No "{pagination_field}" returned.')
                return
            if not isinstance(pagination_value, list):
                logger.error(f'Unable to paginate without pagination field "{pagination_field}". response: {response}')
                return

            yield from pagination_value

            try:
                curr_count = len(pagination_value)
                total_count = int(page.get('total') or total_count)
            except ValueError:
                logger.exception(f'Invalid count values in response: {response}')
                return

            gen_paginated_request.send((curr_count, total_count))

    _paginated_discovery_post = partialmethod(_paginated_discovery_request, 'POST')
    _paginated_services_get_iter = partialmethod(_paginated_services_request_iter, 'GET')

    def _iter_scanned_endpoints(self):

        if consts.REST_ENDPOINT_DISCOVERY_SCANS_PERMISSION not in self._permissions:
            logger.debug('Skipping un-permitted Scanned endpoints')
            return
        logger.debug('Iterating Scanned Endpoints')

        self._update_headers()

        # prepare parameters
        body_params = {
            'accountId': self._account_id,
            'divisionIds': self._division_ids,
            'searchCriteriaList': [],
        }

        try:
            # Note: Endpoints are retrieved from the 'Discovery API' which has a whole separate subdomain.
            #       Therefore, the whole url is passed and 'force_full_url' is set.
            for response in self._paginated_discovery_post(consts.REST_ENDPOINT_DISCOVERY_SCANS_FULL_URL,
                                                           force_full_url=True,
                                                           body_params=body_params):
                devices_chunk = response.get('onlineIPPortDetailsDTOList')
                if not devices_chunk:
                    logger.info(f'No scanned endpoints returned.')
                    return
                if not isinstance(devices_chunk, list):
                    logger.warning(f'Retrieved invalid "onlineIPPortDetailsDTOList" for response {response}')
                    return
                yield from devices_chunk
        except RESTException:
            logger.exception(f'Failed fetching endpoints')

    def _iter_orders(self):

        if consts.REST_ENDPOINT_ORDERS_PERMISSION not in self._permissions:
            logger.debug('Skipping un-permitted Orders')
            return
        logger.debug('Iterating Orders')

        self._update_headers()

        # prepare parameters
        body_params = {
            'accountId': self._account_id,
            'divisionIds': self._division_ids,
            'searchCriteriaList': [],
        }

        try:
            yield from self._paginated_services_get_iter(consts.REST_ENDPOINT_ORDERS,
                                                         pagination_field='orders',
                                                         body_params=body_params)
        except RESTException:
            logger.exception(f'Failed fetching orders')

    def _fetch_devices(self):
        yield from zip(repeat(consts.DeviceType.SCANNED_ENDPOINT), self._iter_scanned_endpoints())
        yield from zip(repeat(consts.DeviceType.ORDER), self._iter_orders())

    def get_device_list(self):
        yield from self._fetch_devices()
