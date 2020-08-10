import logging
from collections import defaultdict
from typing import Optional, Iterable, List
from funcy import chunks

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from redhat_satellite_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class RedhatSatelliteConnection(RESTConnection):
    """ rest client for RedhatSatellite adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix=consts.API_URL_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        # implicit BASIC AUTH (see _do_request)
        try:
            # raises HTTPError(403/401) if there are no permissions
            self._get(consts.HOSTS_V2_ENDPOINT,
                      url_params={'per_page': 1, 'page': 1})
        except Exception as e:
            raise RESTException(f'Error: Invalid response from server, please check domain or credentials:'
                                f' {str(e)}')

    # pylint: disable=arguments-differ
    def _do_request(self, *args, **kwargs):
        # if not instructed otherwise, default to basic auth
        kwargs.setdefault('do_basic_auth', True)
        return super()._do_request(*args, **kwargs)

    # pylint: disable=arguments-differ
    def _handle_response(self, *args, **kwargs):
        response = super()._handle_response(*args, **kwargs)
        if isinstance(response, dict):
            error_dict = response.get('error')
            if isinstance(error_dict, dict):
                raise RESTException(f'Red Hat Satellite Error: {error_dict}')
        return response

    def paginated_get(self, *args,
                      limit: Optional[int] = None,
                      should_raise: bool = False,
                      page_size: int = consts.DEVICE_PER_PAGE,
                      **kwargs):
        url_params = kwargs.setdefault('url_params', {})
        if isinstance(limit, int):
            page_size = min(page_size, limit)
        url_params['per_page'] = page_size

        curr_page = url_params.setdefault('page', 1)  # page is 1-index based
        # Note: initial value used only for initial while iteration
        total_count = count_so_far = 0
        try:
            while count_so_far <= min(total_count, limit or consts.MAX_NUMBER_OF_DEVICES):
                url_params['page'] = curr_page
                response = self._get(*args, **kwargs)

                results = response.get('results')
                if not isinstance(results, (list, dict)):
                    logger.error(f'Invalid results returned after {count_so_far}/{total_count}: {results}')
                    return
                if len(results) == 0:
                    logger.info(f'No results returned after {count_so_far}/{total_count}')
                    return

                if isinstance(results, dict):
                    yield from results.items()
                else:
                    yield from results

                try:
                    count_so_far += len(results)
                    # subtotal defintion from the documentation:
                    #   The number of objects returned with the given search parameters. If there is no
                    #   search, then subtotal is equal to total.
                    total_count = int(response.get('subtotal') or 0)
                except (ValueError, TypeError):
                    logger.exception(f'Received invalid pagination values after/on {count_so_far}/{total_count}')
                    return

                if total_count <= 0:
                    logger.info(f'Done paginated request after {count_so_far}/{total_count}')
                    return

                curr_page = curr_page + 1
        except Exception as e:
            logger.exception(f'Failed paginated request after {count_so_far}/{total_count}')
            if should_raise:
                raise e

    @staticmethod
    def _prepare_async_subendpoint_request(endpoint,
                                           per_page=consts.MAX_SUBENDPOINT_RESULTS):
        return {'name': endpoint,
                'url_params': {'per_page': per_page},
                'do_basic_auth': True}

    def _iter_async_facts_for_hosts(self,
                                    host_names: Iterable[str],
                                    async_chunks: int = consts.ASYNC_CHUNKS):
        try:
            # just in case a single host_name was passed
            if isinstance(host_names, str):
                host_names = [host_names]

            # Facts is under API V2
            async_requests = [
                self._prepare_async_subendpoint_request(
                    f'{consts.HOSTS_V2_ENDPOINT}/{host_name}/{consts.FACTS_SUBENDPOINT}'
                ) for host_name in host_names
            ]

            # Handle succesful fact retrievals
            for response in self._async_get(async_requests,
                                            chunks=async_chunks,
                                            retry_on_error=True):
                if not self._is_async_response_good(response):
                    logger.error(f'Async response returned bad, its {response}')
                    continue

                # response[results]: {host_name: facts_dict, ...}
                if not (isinstance(response, dict) and isinstance(response.get('results'), dict)):
                    logger.warning(f'invalid response returned: {response}')
                    continue

                for host_name, result in response['results'].items():
                    yield (host_name, result)
        except Exception:
            logger.exception(f'Unexpected error during facts iteation')

    def _iter_async_packages_for_hosts(self,
                                       host_ids: list,
                                       async_chunks: int = consts.ASYNC_CHUNKS):
        try:
            # Packages is under API V1
            # https://access.redhat.com/discussions/2592151?tour=8
            async_requests_by_host_id = {
                host_id: self._prepare_async_subendpoint_request(
                    f'{consts.HOSTS_ENDPOINT}/{host_id}/{consts.PACKAGES_SUBENDPOINT}'
                ) for host_id in host_ids
            }

            # Handle succesful package retrievals
            for host_id, response in zip(async_requests_by_host_id.keys(),
                                         self._async_get(list(async_requests_by_host_id.values()),
                                                         chunks=async_chunks,
                                                         retry_on_error=True)):
                if not self._is_async_response_good(response):
                    logger.warning(f'Async response returned bad for packages of host id {host_id}: {response}')
                    continue

                # response[results]: [package_dict, ...]
                if not (isinstance(response, dict) and isinstance(response.get('results'), list)):
                    logger.warning(f'invalid response returned for packages of host id {host_id}: {response}')
                    continue

                yield (host_id, response['results'])

        except Exception:
            logger.exception(f'Unexpected error during packages iteration')

    def _inject_async_packages_for_hosts(self,
                                         hosts: Iterable[dict],
                                         async_chunks: int = consts.ASYNC_CHUNKS):
        hosts_by_ids = {
            host.get('id'): host
            for host in hosts
            if isinstance(host, dict) and host.get('id')
        }
        for host_id, packages_response in self._iter_async_packages_for_hosts(list(hosts_by_ids.keys()),
                                                                              async_chunks=async_chunks):
            try:
                curr_host = hosts_by_ids.get(host_id)
                if not (curr_host and isinstance(curr_host, dict)):
                    logger.warning(f'No host found for packages request for host id {host_id}')
                    continue
                # Note: packages_response might be None if no packages were returned for host_name
                curr_host[consts.ATTR_INJECTED_PACKAGES] = packages_response
            except Exception:
                logger.exception(f'Failed injecting packages for host id {host_id}', exc_info=True)

    def _inject_async_facts_for_hosts_by_hostname(self,
                                                  hosts: List[dict],
                                                  async_chunks: int = consts.ASYNC_CHUNKS):

        hosts_by_hostname = defaultdict(list)
        for host in hosts:
            # Invalid host
            if not isinstance(host, dict):
                logger.warning(f'got invalid host: {host}')
                break

            host_name = host.get('name')
            if not (host_name and isinstance(host_name, str)):
                continue

            hosts_by_hostname[host_name].append(host)
        for host_name, facts_response in self._iter_async_facts_for_hosts(hosts_by_hostname.keys(),
                                                                          async_chunks=async_chunks):
            try:
                curr_hosts = hosts_by_hostname.get(host_name)
                if not (curr_hosts and isinstance(curr_hosts, list)):
                    logger.warning(f'No hosts found for facts request for hostname {host_name}')
                    continue

                for host in curr_hosts:
                    # Note: facts_response might be None if no facts were returned for host_name
                    host[consts.ATTR_INJECTED_FACTS] = facts_response
            except Exception:
                logger.warning(f'Failed injecting facts for host {host_name}', exc_info=True)

    def _iter_hosts(self, limit: Optional[int] = None, should_raise=False):
        yield from self.paginated_get(consts.HOSTS_V2_ENDPOINT,
                                      limit=limit,
                                      should_raise=should_raise)

    def get_device_list(self,
                        fetch_host_facts: bool = False,
                        fetch_host_packages: bool = False,
                        async_chunks: int = consts.ASYNC_CHUNKS,
                        hosts_chunk_size: int = consts.DEVICE_PER_PAGE):

        # For every 1000 hosts, run facts and packages async
        for hosts_chunk in chunks(consts.HOSTS_CHUNKS, self._iter_hosts()):

            if fetch_host_facts:
                self._inject_async_facts_for_hosts_by_hostname(hosts_chunk,
                                                               async_chunks=async_chunks)

            if fetch_host_packages:
                self._inject_async_packages_for_hosts(hosts_chunk,
                                                      async_chunks=async_chunks)

            # yield hosts after being potentially injected
            yield from hosts_chunk
