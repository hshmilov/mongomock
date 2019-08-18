import datetime
import logging
import time

from json.decoder import JSONDecodeError

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.adapter_exceptions import ClientConnectionException


logger = logging.getLogger(f'axonius.{__name__}')


class CensysConnection(RESTConnection):
    def __init__(self, *args, domain_preferred=None, free_tier=False, search_type=None, **kwargs):
        self._internal_censys = domain_preferred and ';' in domain_preferred
        self._auth_url = None
        if self._internal_censys:
            domain_preferred, self._auth_url = domain_preferred.split(';')[0], domain_preferred.split(';')[1]
        super().__init__(*args, domain=domain_preferred or 'censys.io',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        if self._internal_censys:
            if len(self._username.split(';')) > 1:
                self._username, self._app_id = self._username.split(';')[0], self._username.split(';')[1]
            else:
                self._app_id = ''
            if len(self._password.split(';')) > 1:
                self._password, self._app_secret = self._password.split(';')[0], self._password.split(';')[1]
            else:
                self._app_secret = ''
        self.free_tier = free_tier
        self.search_type = search_type
        self._session_refresh = None

    def _refresh_token(self):
        """
        Temporarily adjusts the connection properties to handle a specific customer's
        internal API proxy mechanism that sits in front of Censys. This should be
        refactored ASAP...
        """
        if self._session_refresh and self._session_refresh > datetime.datetime.now():
            return

        self._session_headers = {'Content-Type': 'application/x-www-form-urlencoded',
                                 'Accept': 'application/json'}

        response = self._post(self._auth_url,
                              force_full_url=True,
                              body_params=f'grant_type=password&username={self._app_id}&password={self._app_secret}',
                              use_json_in_body=False,
                              do_basic_auth=True)
        try:
            access_token = response['access_token']
            token_type = response['token_type']
            expires_in = response['expires_in']
            self._session_refresh = datetime.datetime.now() + datetime.timedelta(seconds=(expires_in - 1))
        except Exception as e:
            message = f'Error parsing response: {str(e)}'
            logger.exception(message)
            raise message
        if token_type == 'Bearer' and expires_in > 0:
            self._session_headers = {'Content-Type': 'application/json',
                                     'Accept': 'application/json',
                                     'Authorization': access_token}
        else:
            message = f'Invalid access_token type or token already expired!'
            logger.exception(message)
            raise message

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('Missing credentials')

        # Do customer-specific internal auth (we need to refactor this ASAP...)
        account_endpoint = 'api/v1/account'
        if self._internal_censys:
            self._refresh_token()
            account_endpoint = f'censys/{account_endpoint}'

        # Do normal Censys API check
        try:
            self._get(account_endpoint, do_basic_auth=bool(self._url.lower().startswith('https://censys.io/')))
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
        search_endpoint = f'api/v1/search/{self.search_type}'
        if self._internal_censys:
            self._refresh_token()
            search_endpoint = f'censys/{search_endpoint}'
        return self._post(search_endpoint,
                          body_params={
                              'query': search_query,
                              'page': page,
                              'flatten': True
                          },
                          do_basic_auth=bool(self._url.lower().startswith('https://censys.io/')),
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
        Returns the full/raw details for a given Censys search result given a type and id. If no
        information is known to Censys, don't raise an exception for the resulting 404.

        :return: A JSON blob representing the full Censys document corresponding to the type/id
        """
        # Free limit: 1 req / 2.5s
        # Paid rate limit: 1 req / 1s
        #
        # See: https://support.censys.io/sales-questions/which-censys-product-should-i-buy
        if self.free_tier:
            time.sleep(1.5)
        time.sleep(1)
        view_endpoint = f'api/v1/view/{self.search_type}/{result_id}'
        if self._internal_censys:
            self._refresh_token()
            view_endpoint = f'censys/{view_endpoint}'
        response = self._get(view_endpoint,
                             do_basic_auth=bool(self._url.lower().startswith('https://censys.io/')),
                             raise_for_status=False,
                             use_json_in_response=False,
                             return_response_raw=True)
        if response.status_code != 200:
            try:
                if 'error' in response.json():
                    return response.json()
            except JSONDecodeError as e:
                pass
        return self._handle_response(response)

    # Use normal Censys workflow of Search API --> results --> View API --> result details
    # pylint: disable=arguments-differ
    def get_device_list(self, search_query):
        search_results = self._get_search_results(search_query)

        if self.search_type == 'ipv4':
            result_id_key = 'ip'
        elif self.search_type == 'websites':
            result_id_key = 'domain'
        else:
            logger.error(f'Error querying devices due to invalid search_type {self.search_type}')

        for result in search_results:
            try:
                yield self._get_view_details(result.get(result_id_key))
            except Exception:
                logger.exception(f'Problem getting information for search result: {result}')
