import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from infoblox_adapter.consts import MAX_NUMBER_OF_PAGES, RESULTS_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class InfobloxConnection(RESTConnection):

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            url_base_prefix='/wapi/v2.2/',
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            **kwargs
        )

    def __get_items_from_url(self, path, url_params):
        try:
            logger.info(f'Starting url path {path} with params {url_params}')
            url_params['_return_as_object'] = 1
            url_params['_max_results'] = RESULTS_PER_PAGE
            url_params['_paging'] = 1
            response = self._get(path, url_params=url_params, do_basic_auth=True)
            yield from response['result']
            next_page_id = response.get('next_page_id')
            number_of_pages = 1
            while next_page_id and number_of_pages < MAX_NUMBER_OF_PAGES:
                try:
                    url_params['_page_id'] = next_page_id
                    response = self._get(path, url_params=url_params, do_basic_auth=True)
                    yield from response['result']
                    next_page_id = response.get('next_page_id')
                except Exception:
                    logger.exception(f'Bad requests at {next_page_id}')
                    break
                number_of_pages += 1
        except Exception:
            logger.exception(f'Problem getting path {path} with params {url_params}')

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        try:
            self._get('zone_auth', url_params={'_return_as_object': 1, '_max_results': 1}, do_basic_auth=True)
        except Exception as e:
            logger.exception(f'can not log in')
            if '401 client error' in str(e).lower():
                raise RESTException(f'401 Unauthorized - Please check your login credentials')
            else:
                raise

    def get_device_list(self):
        yield from self.__get_items_from_url('lease',
                                             url_params={'_return_fields': 'served_by,'
                                                                           'starts,ends,'
                                                                           'address,'
                                                                           'binding_state,'
                                                                           'hardware,'
                                                                           'client_hostname,network_view'})
