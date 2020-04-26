import logging

from typing import Dict, List, Optional, Iterable

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from redhat_satellite_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class RedhatSatelliteConnection(RESTConnection):
    """ rest client for RedhatSatellite adapter """

    def __init__(self, fetch_host_facts: bool, *args,
                 hosts_chunk_size: int = consts.DEVICE_PER_PAGE, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._fetch_host_facts = fetch_host_facts
        self._hosts_chunk_size = hosts_chunk_size

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        # raises HTTPError(403/401) if there are no permissions
        host = next(self._iter_hosts(limit=1, should_raise=True), None)
        if not isinstance(host, dict):
            message = 'Invalid hosts response received from Satellite Server. Please contact Axonius.'
            logger.warning(f'{message} {host}')
            raise RESTException(message)

        # only check facts if it was requested and the first host had host_name
        if self._fetch_host_facts and isinstance(host.get('name'), str):
            facts = self._get(**self._request_params_for_facts_for_host(host['name']))
            if not isinstance(facts, dict):
                message = 'Invalid facts response received from Satellite Server. Please contact Axonius.'
                logger.warning(f'{message} {facts}')
                raise RESTException(message)

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

    def paginated_get(self, *args, limit: Optional[int] = None, should_raise=False, **kwargs):
        pagination_params = kwargs.setdefault('url_params', {})
        chunk_size = self._hosts_chunk_size
        if isinstance(limit, int):
            chunk_size = min(chunk_size, limit)
        pagination_params.setdefault('per_page', chunk_size)

        curr_page = pagination_params.setdefault('page', 1)  # page is 1-index based
        # Note: initial value used only for initial while iteration
        total_count = count_so_far = 0
        try:
            while count_so_far <= min(total_count, limit or consts.MAX_NUMBER_OF_DEVICES):
                pagination_params['page'] = curr_page
                response = self._do_request(*args, **kwargs)

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
    def _request_params_for_facts_for_host(host_name):
        return {'name': f'v2/hosts/{host_name}/facts', 'do_basic_auth': True}

    def _iter_async_facts_for_hosts(self, host_names: Iterable[str]):
        get_params_by_host_name = {host_name: self._request_params_for_facts_for_host(
            host_name) for host_name in host_names}

        # Handle succesful fact retrievals
        for response in self._async_get(list(get_params_by_host_name.values()),
                                        chunks=consts.ASYNC_CHUNKS,
                                        retry_on_error=True):
            if not self._is_async_response_good(response):
                logger.error(f'Async response returned bad, its {response}')
                continue
            if not (isinstance(response, dict) and isinstance(response.get('results'), dict)):
                logger.warning(f'invalid response returned: {response}')
                continue
            for host_name, facts in response['results'].items():
                if not get_params_by_host_name.pop(host_name, None):
                    logger.warning(f'cannot find hostname {host_name} in requests')
                    continue

                yield (host_name, facts)

        # Yield the rest of the hosts
        logger.info(f'The following host_names did not return facts: {list(get_params_by_host_name.keys())}')
        yield from ((host_name, None) for host_name in get_params_by_host_name.keys())

    def _iter_hosts_and_facts(self, limit: Optional[int]=None):

        hosts_by_hostname = {}  # type: Dict[str, List[Dict]]

        def _inject_facts_and_flush_hosts():
            if not hosts_by_hostname:
                return

            for host_name, facts_response in self._iter_async_facts_for_hosts(hosts_by_hostname.keys()):
                for host in (hosts_by_hostname.pop(host_name, None) or []):
                    # Note: facts_response might be None if no facts were returned for host_name
                    host[consts.ATTR_INJECTED_FACTS] = facts_response
                    yield host

            # yield the rest if for some reason not yielded by self._iter_async_facts_for_hosts
            # Note: this relies on the dict.pop above to clear any host from the dict that was yielded by facts
            for host_name, hosts in hosts_by_hostname:
                yield from hosts

        for i, host in enumerate(self._iter_hosts(limit=limit)):
            host_name = host.get('name')
            if not isinstance(host_name, str):
                # hosts with no hostname are yielded here
                yield host
                continue

            # Note: we're popping the hosts for the current host_name because we dont need them anymore.
            hosts_by_hostname.setdefault(host_name, []).append(host)

            # after every page, run the facts requests
            if (i % self._hosts_chunk_size) == 0:
                yield from _inject_facts_and_flush_hosts()

        # perform facts injection and flush the rest
        yield from _inject_facts_and_flush_hosts()

    def _iter_hosts(self, limit: Optional[int]=None, should_raise=False):
        yield from self.paginated_get('v2/hosts', limit=limit, should_raise=should_raise)

    def get_device_list(self):
        if self._fetch_host_facts:
            yield from self._iter_hosts_and_facts()
        else:
            yield from self._iter_hosts()
