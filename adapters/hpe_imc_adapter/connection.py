import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from hpe_imc_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES, URL_USERS, URL_DEVICES, URL_BASE_PREFIX

logger = logging.getLogger(f'axonius.{__name__}')


class HpeImcConnection(RESTConnection):
    """
    rest client for HpeImc adapter.
    API information: https://support.hpe.com/hpesc/public/docDisplay?docId=emr_na-c03382045
    also https://techlibrary.hpe.com/device_help/eapi/rest_en/api/
     """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix=URL_BASE_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        try:
            self._get_total_result_count(URL_USERS)
            self._get_total_result_count(URL_DEVICES)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials: {str(e)}')

    def _get(self, *args, **kwargs):
        """
        Overriding _get because the imc eAPI requires digest auth for all requests.
        Forces `do_digest_auth=True` .
        :param args: args for RESTConnection._get()
        :param kwargs: kwargs for RESTConnection._get()
        :return: see RESTConnection._get()
        """
        return super()._get(*args, **kwargs, do_digest_auth=True)

    def _get_total_result_count(self, url, **extra_params):
        """
        Get a total of result count. The API states that the total is returned as a header, and the body is empty.
        So we use `return_response_raw=True` here and extract the header.
        Raises KeyError if Total not in response headers, or ValueError if the value cannot be made an int.
        :param url: URL to try and get total from (see `URL_DEVICES` and `URL_USERS`)
        :param extra_params: Extra url params, if needed. (dict)
        :return: Int representing the total amount of records matching the filter.
        """
        url_params = {'total': True, **extra_params}
        # Why in all the flying ducks does `use_json_in_response` take precedence
        # over `return_response_raw`???
        response = self._get(url, return_response_raw=True, use_json_in_response=False, url_params=url_params)
        return int(response.headers['Total'])

    def _paginated_get(self, url, yield_param: str = 'devices'):
        """
        Paginated get for imc eAPI
        :param url: URl to get, relative to `base_url`
        :param yield_param: Parameter to yield from the response. Should be either 'user' or 'device'
        :return: iterable of dicts representing the assets.
        Note: Will raise an exception if fetch fails at any point.
        """
        try:
            total = self._get_total_result_count(url)
            if not total:
                # no results
                return
            logger.info(f'Expecting a total of {total} {yield_param}s.')
            total = min(total, MAX_NUMBER_OF_DEVICES)
            logger.info(f'Actually fetching {total} {yield_param}s.')
            url_params = {
                'start': 0,
                'size': DEVICE_PER_PAGE,
                'orderBy': 'id',
                'desc': False,
                'total': False,
                'exact': False
            }
            for offset in range(0, total, DEVICE_PER_PAGE):
                url_params['start'] = offset
                response = self._get(url, url_params)
                if not response.get(yield_param):
                    logger.warning(f'Got no more {yield_param}s for offset {offset}')
                    return
                logger.debug(f'Yielding next {yield_param} from offset {offset}')
                if isinstance(response.get(yield_param), dict):
                    yield response.get(yield_param)
                elif isinstance(response.get(yield_param), list):
                    yield from response.get(yield_param)
                else:
                    message = f'Got bad response from imc after offset {offset}! Response is: {response}'
                    logger.error(message)
                    raise ValueError(message)
            logger.info(f'Finished yielding {yield_param}s after {total} returned.')
        except Exception:
            logger.exception(f'Invalid request made while paginating {yield_param}s')
            raise

    def get_device_list(self):
        try:
            yield from self._paginated_get(URL_DEVICES, 'device')
        except RESTException as err:
            logger.exception(str(err))
            raise

    def get_user_list(self):
        try:
            yield from self._paginated_get(URL_USERS, 'user')
        except RESTException as err:
            logger.exception(str(err))
            raise
