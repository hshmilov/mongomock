import ipaddress
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from infoblox_adapter.consts import MAX_NUMBER_OF_PAGES, RESULTS_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class InfobloxConnection(RESTConnection):

    def __init__(self, api_version: float, *args, **kwargs):
        self.__api_version = api_version
        super().__init__(
            *args,
            url_base_prefix=f'/wapi/v{api_version}/',
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
            raise

    def get_device_list(self):
        # First, get all networks to get additional data about the leases
        networks = dict()
        logger.info(f'Getting networks')
        try:
            for network_raw in self.__get_items_from_url(
                    'network',
                    url_params={'_return_fields': 'network,extattrs'}
            ):
                if not network_raw.get('network'):
                    continue
                networks[ipaddress.IPv4Network(network_raw.get('network'))] = network_raw
        except Exception:
            logger.exception(f'Problem getting networks')
        logger.info(f'Finished getting {len(networks)} networks. Getting leases')
        # Then, get leases
        fields_to_return = 'served_by,starts,ends,address,binding_state,hardware,client_hostname,network_view'
        if self.__api_version >= 2.5:
            fields_to_return += ',fingerprint'
        for lease_raw in self.__get_items_from_url('lease', url_params={'_return_fields': fields_to_return}):
            try:
                lease_address = lease_raw.get('address')
                if lease_address:
                    lease_address = ipaddress.IPv4Address(lease_address)
                    for network, network_data in networks.items():
                        if lease_address in network:
                            lease_raw['network_data'] = network_data
                            break
            except Exception:
                pass
            yield lease_raw
