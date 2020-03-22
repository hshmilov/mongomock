import logging
import base64
from typing import Optional, List, Generator
from functools import partialmethod

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from contrast_security_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class ContrastSecurityConnection(RESTConnection):
    """ rest client for ContrastSecurity adapter """

    def __init__(self, domain: str, service_key: str, *args, org_uuids: Optional[List[str]] = None, **kwargs):
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

    def _iter_libraries_for_org(self, org_uuid: str):
        try:
            yield from self._paginated_get_iteration(f'ng/{org_uuid}/libraries/filter',
                                                     pagination_list_field='libraries',
                                                     url_params={'expand': 'vulns,apps,skip_links'})
        except Exception as e:
            logger.exception(f'Failed iterating libraries for organization {org_uuid}. error: {str(e)}')
            return

    def _iter_libraries_by_app_for_org(self, org_uuid: str):
        libraries_by_app_id = {}
        for library in self._iter_libraries_for_org(org_uuid):
            for application in (library.get('apps') or []):
                if not application.get('app_id'):
                    logger.debug(f'Skipping application missing app_id, app: {application}')
                    continue
                libraries_by_app_id.setdefault(application['app_id'], []).append(library)
            del library['apps']
        return libraries_by_app_id

    def _iter_applications_for_org(self, org_uuid: str):
        try:
            yield from self._paginated_get_iteration(f'ng/{org_uuid}/applications',
                                                     pagination_list_field='applications',
                                                     url_params={'expand': 'skip_links'})
        except Exception as e:
            logger.exception(f'Failed iterating applications for organization {org_uuid}. error: {str(e)}')
            return

    def _list_applications_by_app_id_for_org(self, org_uuid: str, include_libraries=True):
        applications_by_app_id = {app_dict['app_id']: app_dict
                                  for app_dict in self._iter_applications_for_org(org_uuid)}
        if include_libraries:
            libraries_by_app_id = self._iter_libraries_by_app_for_org(org_uuid)
            for app_id, libraries in libraries_by_app_id.items():
                if app_id not in applications_by_app_id:
                    logger.warning(f'Failed to locate app {app_id}. Ditching its libraries')
                    continue
                applications_by_app_id[app_id].setdefault('libs', []).extend(libraries)
        return applications_by_app_id

    def _iter_servers_for_org(self, org_uuid: str):
        try:
            yield from self._paginated_get_iteration(f'ng/{org_uuid}/servers',
                                                     pagination_list_field='servers',
                                                     url_params={'expand': 'applications,skip_links'})
        except Exception as e:
            logger.exception(f'Failed iterating servers for organization {org_uuid}. error: {str(e)}')
            return

    def _paginated_request_iteration(self, *args, pagination_list_field, **kwargs) -> Generator[dict, None, None]:
        """
        Only use paginated methods if the endpoint has 'limit' and 'offset'
        """
        url_params = kwargs.setdefault('url_params', {})
        url_params.setdefault('limit', consts.DEVICE_PER_PAGE)
        count_so_far = url_params.setdefault('offset', 0)
        total_count = 0
        while True:
            response = self._do_request(*args, **kwargs)

            pagination_list = response.get(pagination_list_field) or []
            if not isinstance(pagination_list, list):
                logger.warning(f'Unknown "{pagination_list_field}" encountered on offset {count_so_far},'
                               f' Halting. Value: {pagination_list}')
                return

            curr_count = len(pagination_list)
            if total_count != response.get('count'):
                total_count = int(response.get('count') or curr_count)
                logger.info(f'Fetching overall {total_count} "{pagination_list_field}".')

            logger.debug(f'yielding {curr_count}/{total_count} "{pagination_list_field}"')

            yield from pagination_list

            count_so_far += curr_count
            if (curr_count < 1) or (count_so_far >= total_count):
                logger.debug(f'Done paginated request')
                return
            url_params['offset'] = count_so_far

    _paginated_get_iteration = partialmethod(_paginated_request_iteration, 'GET')
    _paginated_post_iteration = partialmethod(_paginated_request_iteration, 'POST')

    # pylint: disable=arguments-differ
    def _handle_response(self, response, **kwargs):
        response = super()._handle_response(response, **kwargs)
        # if success is present, use it! otherwise, just keep on.
        if not response.get('success', True):
            raise RESTException(f'{response.get("messages", [])}')
        return response

    def get_device_list(self):
        for org_uuid in self._org_uuids:
            org_applications_by_app_id = self._list_applications_by_app_id_for_org(org_uuid, include_libraries=True)
            for server in self._iter_servers_for_org(org_uuid):
                if server.get('applications'):
                    server_app_ids = [app_dict['app_id'] for app_dict in (server.get('applications') or [])
                                      if app_dict.get('app_id')]
                    # run over the existing applications list with a more enriched version of it
                    server['applications'] = [org_applications_by_app_id[app_id] for app_id in server_app_ids if
                                              app_id in org_applications_by_app_id]
                yield (org_uuid, server)
