import logging
import time

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.adapter_exceptions import ClientConnectionException


logger = logging.getLogger(f'axonius.{__name__}')


class CensysConnection(RESTConnection):
    def __init__(self, *args, domain_preferred=None, free_tier=False, search_type=None, **kwargs):
        super().__init__(*args, url_base_prefix='api/v1', domain=domain_preferred or 'censys.io',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self.free_tier = free_tier
        self.search_type = search_type

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No API ID or API Key set')

        # Also get /account to check that api key/secret are valid
        try:
            self._get('account', do_basic_auth=True)
        except RESTException as e:
            message = f'Error connecting to domain {self._domain}: {str(e)}'
            logger.exception(message)
            raise ClientConnectionException(message)

    def _get_search_result_page(self, search_query, page=1):
        """
        Returns the given page of Censys results for the given search query/type

        :return: A single page worth of Censys search results
        """
        # Free limit: 1 req / 2.5s
        # Paid rate limit: 1 req / 1s
        #
        # See: https://support.censys.io/sales-questions/which-censys-product-should-i-buy
        if self.free_tier:
            time.sleep(1.5)
        time.sleep(1)
        return self._post(f'search/{self.search_type}',
                          body_params={
                              'query': search_query,
                              'page': page,
                              'flatten': True
                          },
                          do_basic_auth=True,
                          use_json_in_body=True)

    def _get_search_results(self, search_query):
        """
        Returns a list of all Censys results for the given search query/type

        :return: A List of search results (all pages) to pass to the View API
        """
        initial_search = self._get_search_result_page(search_query)
        if 'results' not in initial_search:
            raise RESTException(f'Received malformed/empty initial search response: {initial_search}')
        result_pages = initial_search['metadata']['pages']
        for page in range(1, result_pages + 1):
            yield from self._get_search_result_page(search_query, page)['results']

    def _get_view_details(self, result_id):
        """
        Returns the full/raw details for a given Censys search result given a type and id.

        :return: A JSON blob representing the full Censys document corresponding to the type/id
        """
        # Free limit: 1 req / 2.5s
        # Paid rate limit: 1 req / 1s
        #
        # See: https://support.censys.io/sales-questions/which-censys-product-should-i-buy
        if self.free_tier:
            time.sleep(1.5)
        time.sleep(1)
        return self._get(f'view/{self.search_type}/{result_id}', do_basic_auth=True)

    # Use normal Censys workflow of Search API --> results --> View API --> result details
    # pylint: disable=arguments-differ
    def get_device_list(self, search_query):
        search_results = self._get_search_results(search_query)

        if self.search_type == 'ipv4':
            result_id_key = 'ip'
        elif self.search_type == 'websites':
            result_id_key = 'domain'
        else:
            logger.info(f'Error querying devices due to invalid search_type {self.search_type}')

        for result in search_results:
            try:
                yield self._get_view_details(result.get(result_id_key))
            except Exception:
                logger.info(f'Problem getting information for search result: {result}')
