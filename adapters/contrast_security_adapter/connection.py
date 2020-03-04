import logging
import base64
from typing import Optional, List, Generator, Tuple
from functools import partialmethod

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from contrast_security_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class ContrastSecurityConnection(RESTConnection):
    """ rest client for ContrastSecurity adapter """

    def __init__(self, domain: str, service_key: str, org_uuids: Optional[List[str]], *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         domain=f'{domain.rstrip("/")}/api' if domain else None,
                         use_domain_path=True,
                         **kwargs)
        self._service_key = service_key
        self._org_uuids = org_uuids

    def _connect(self):
        if not (self._username and self._service_key and self._apikey):
            raise RESTException('No username or service key or api key')
        auth_str = f'{self._username}:{self._service_key}'
        self._session_headers.update({
            'Authorization': base64.b64encode(bytearray(auth_str, 'utf-8')).decode('utf-8'),
            'API-Key': self._apikey,
        })

        # Test authentication using allowed organizations retrieval
        try:
            # Bring all allowed organization
            allowed_org_uuids = {org_dict.get('organization_uuid')
                                 for org_dict in self._iter_allowed_organizations_unsafe()}
        except RESTException as e:
            message = f'Login failed. messages: {str(e)}'
            logger.exception(message, exc_info=e)
            raise RESTException(message)

        # If organization uuids given,
        if self._org_uuids:
            # Make sure all org_uuids given are allowed.
            missing_uuids = set(self._org_uuids) - allowed_org_uuids
            if missing_uuids:
                raise RESTException(f'Missing permissions for the following organizations:'
                                    f' {", ".join(missing_uuids)}.')

        else:
            # Otherwise, Make sure there's at least one allowed organization uuid.
            if not allowed_org_uuids:
                raise RESTException(f'No organization with permissions found.')
            #   and use them
            self._org_uuids = allowed_org_uuids

    def _iter_allowed_organizations_unsafe(self):
        response = self._get(consts.ALLOWED_ORGANIZATIONS_ENDPOINT)
        yield from response.get('organizations', [])

    def iter_servers(self, include_applications=True) -> Generator[Tuple[str, dict], None, None]:
        for org_uuid in self._org_uuids:
            yield from ((org_uuid, server_dict) for server_dict in
                        self._iter_servers_for_org(org_uuid, include_applications=include_applications))

    def _iter_servers_for_org(self, org_uuid: str, include_applications=True):
        try:
            url_params = {}
            if include_applications:
                url_params['expand'] = 'applications'
            for response in self._paginated_get(f'ng/{org_uuid}/servers',
                                                url_params=url_params):
                servers = response.get('servers')
                if not (servers and isinstance(servers, list)):
                    logger.debug(f'No Servers returned for organization {org_uuid}')
                    return
                yield from servers
        except Exception as e:
            logger.exception(f'Failed iterating servers for organization {org_uuid}. error: {str(e)}')
            return

    def _paginated_request(self, *args, **kwargs) -> Generator[dict, None, None]:
        """
        Only use paginated methods if the endpoint has 'limit' and 'offset'
        """
        url_params = kwargs.setdefault('url_params', {})
        url_params.setdefault('limit', consts.DEVICE_PER_PAGE)
        count = url_params.setdefault('offset', 0)
        # Perform perpetual requests until returned count is 0
        while True:
            response = self._do_request(*args, **kwargs)
            yield response
            curr_count = response.get('count')
            if curr_count < 1:
                return
            count += curr_count
            url_params['offset'] = count

    _paginated_get = partialmethod(_paginated_request, 'GET')
    _paginated_post = partialmethod(_paginated_request, 'POST')

    # pylint: disable=arguments-differ
    def _handle_response(self, response, **kwargs):
        logger.debug(response.text)
        response = super()._handle_response(response, **kwargs)
        # if success is present, use it! otherwise, just keep on.
        if not response.get('success', True):
            raise RESTException(f'{response.get("messages", [])}')
        return response

    def get_device_list(self):
        yield from self.iter_servers()
