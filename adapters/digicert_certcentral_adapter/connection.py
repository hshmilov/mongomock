import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException, RESTConnectionError
from digicert_certcentral_adapter.consts import REST_PATH_AUTH, \
    REST_PATH_LIST_ENDPOINTS, DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES, DEFAULT_START_INDEX, \
    PAGINATION_FIELD_PAGE_SIZE, PAGINATION_FIELD_OFFSET, PAGINATION_FIELD_COUNT_CURRENT, PAGINATION_FIELD_COUNT_TOTAL


logger = logging.getLogger(f'axonius.{__name__}')


class DigicertCertcentralConnection(RESTConnection):
    """ rest client for DigicertCertcentral adapter """

    def __init__(self, *args, api_key, account_id, division_ids=None, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         domain='',
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
            response = self._get(REST_PATH_AUTH)
        except RESTException:
            logger.exception(f'Failed to get permissions for client {self.client_id}')
            raise

        # debug print for test runs
        logger.debug(f'Successful Digicert authorization response: {response}')

        authorizations = response.get('authorizations') or None
        if authorizations is None:
            message = f'No permissions returned in response {response}'
            logger.error(message)
            raise RESTException(message)

        self._permissions = {authorization['permission']: authorization['authorized']
                             for authorization in authorizations}

    def _connect(self):
        if not self._api_key:
            raise RESTException('No API Key')
        self._update_headers()
        self._refresh_permissions()
        _ = list(self._fetch_devices(max_devices=1))

    def _paginated_post(self, *args, limit: int = 0, **kwargs):

        # make sure limit does not exceed the maximum allowed and in the case of 0 use max
        if limit < 0 or limit > MAX_NUMBER_OF_DEVICES:
            message = f'Invalid limit {limit} given, may only be 0 < limit < {MAX_NUMBER_OF_DEVICES}'
            logger.error(message)
            raise ValueError(message)
        limit = limit or MAX_NUMBER_OF_DEVICES

        # Initiate pagination and body params (if not given)
        # Note: body_params is equivalent to kwargs['body_params'] because its an object -
        #           affecting body_params affects kwargs' one as well.
        body_params = kwargs.setdefault('body_params', {})
        body_params.setdefault(PAGINATION_FIELD_PAGE_SIZE, DEVICE_PER_PAGE)
        curr_offset = body_params.setdefault(PAGINATION_FIELD_OFFSET, DEFAULT_START_INDEX)

        # Perform the request per page
        total_count = None
        while (total_count is None) or (curr_offset < min(total_count, limit)):

            try:
                response = self._post(*args, **kwargs)
            except RESTException:
                logger.exception(f'Failed paginated request on {curr_offset}/{total_count}.')
                raise

            try:
                curr_count, total_count = (int(response.get(field, 0)) for field in
                                           [PAGINATION_FIELD_COUNT_CURRENT, PAGINATION_FIELD_COUNT_TOTAL])
            except ValueError:
                logger.exception(f'Invalid count values in response {response}')
                return

            # Debug print response for test runs
            logger.debug(f'Digicert response: {response}')
            yield response

            if curr_count <= 0 or total_count <= 0:
                logger.error(f'Invalid count {curr_count}/{total_count} encountered after {curr_offset} offset.')
                return

            curr_offset += curr_count
            body_params[PAGINATION_FIELD_OFFSET] = curr_offset

    def _fetch_devices(self, max_devices=MAX_NUMBER_OF_DEVICES):
        self._update_headers()

        # prepare parameters
        body_params = {
            'accountId': self._account_id,
            'divisionIds': self._division_ids,
            'searchCriteriaList': [],
        }

        try:
            for response in self._paginated_post(REST_PATH_LIST_ENDPOINTS, limit=max_devices, body_params=body_params):
                devices_chunk = response.get('onlineIPPortDetailsDTOList') or None
                if not isinstance(devices_chunk, list):
                    logger.warning(f'Retrieved invalid "onlineIPPortDetailsDTOList" for response {response}')
                    return
                for raw_device in devices_chunk:
                    yield raw_device
        except RESTException as e:
            # pylint: disable=invalid-string-quote
            if "'message': 'Forbidden'" in str(e):
                message = f'Access denied to CertCentral Discovery Endpoint'
                logger.exception(message)
                raise RESTConnectionError(message)
            raise

    def get_device_list(self):
        yield from self._fetch_devices()
