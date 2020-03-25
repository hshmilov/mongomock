import logging
from functools import partialmethod

from typing import Dict, List

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from redhat_satellite_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class RedhatSatelliteConnection(RESTConnection):
    """ rest client for RedhatSatellite adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._environments = []

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        # TTOODDDDO: add permission check

    # pylint: disable=arguments-differ
    def _do_request(self, *args, **kwargs):
        # if not instructed otherwise, default to basic auth
        kwargs.setdefault('do_digest_auth', True)
        return super()._do_request(*args, **kwargs)

    # pylint: disable=arguments-differ
    def _handle_response(self, *args, **kwargs):
        response = super()._handle_response(*args, **kwargs)
        if isinstance(response, dict):
            error_dict = response.get('error')
            if isinstance(error_dict, dict):
                raise RESTException(f'Red Hat Satellite Error: {error_dict}')
        return response

    def _paginated_request(self, *args, **kwargs):
        pagination_params = kwargs.setdefault(
            'url_params' if (kwargs.get('method') or args[0]) == 'GET'
            else 'body_params', {})
        pagination_params.setdefault('per_page', consts.DEVICE_PER_PAGE)
        curr_page = pagination_params.setdefault('page', 1)  # page is 1-index based
        # Note: initial value used only for initial while iteration
        total_count = count_so_far = 0
        try:
            while count_so_far <= total_count:
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
        except Exception:
            logger.exception(f'Failed paginated request after {count_so_far}/{total_count}')

    paginated_get = partialmethod(_paginated_request, 'GET')

    def _iter_hosts(self, include_facts=True):

        hosts_iter = self.paginated_get('v2/hosts')
        if not include_facts:
            # If facts are not included, all hosts are yielded here
            yield from hosts_iter
            return

        fact_requests = []
        hosts_by_hostname = {}  # type: Dict[str, List[Dict]]
        for host in hosts_iter:
            host_name = host.get('name')
            if isinstance(host_name, str):
                # hosts with no hostname are yielded here
                yield host
                continue

            hosts_by_hostname.setdefault(host_name, []).append(host)
            fact_requests.append(self._request_params_for_facts_for_host(host_name))

        for host_name, facts in self._async_get_only_good_response(fact_requests):
            for host in (hosts_by_hostname.get(host_name) or []):
                host[consts.ATTR_INJECTED_FACTS] = facts
                # the rest of the hosts, including their facts, are yielded here
                yield host

    @staticmethod
    def _request_params_for_facts_for_host(host_name):
        return {'name': f'v2/hosts/{host_name}/facts'}

    def _list_facts_for_host(self, host_name):
        yield from self.paginated_get(**self._request_params_for_facts_for_host(host_name))

    def get_device_list(self):
        yield from self._iter_hosts()
