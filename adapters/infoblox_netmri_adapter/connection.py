import logging
from typing import Optional, Iterable

# pylint: disable = import-error
from infoblox_netmri import InfobloxNetMRI

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from infoblox_netmri_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class InfobloxNetmriConnection(RESTConnection):
    """ rest client for InfobloxNetmri adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._client = None

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        if self._client:
            return
        try:
            self._client = InfobloxNetMRI(self._domain, self._username, self._password, ssl_verify=self._verify_ssl)
            if self._proxies:
                self._client.session.proxies = self._proxies
            self._client.api_request('devices/index', {'limit': 1})
        except Exception as e:
            logger.exception(f'Error connecting to NetMRI server: {str(e)}')
            raise RESTException(f'Error: Invalid response from server, please check domain or credentials.'
                                f' The error was: {str(e)}')

    def _get_total(self, api_endpoint, params):
        logger.info(f'Attempting to fetch result count for api endpoint {api_endpoint}')
        params = params or {}
        try:
            total = self._client.api_request(api_endpoint, {**params, 'limit': 1}).get('total')
            if not isinstance(total, int):
                raise ValueError(f'Unexpected value for total: {total}')
        except Exception:
            message = f'Failed to get total count of results for {api_endpoint}'
            logger.exception(message)
            raise
        logger.info(f'Expecting total of {total} results, max is {consts.MAX_NUMBER_OF_DEVICES}')
        return min(total, consts.MAX_NUMBER_OF_DEVICES)

    def _paginated_get(self,
                       api_endpoint,
                       result_param: str = 'devices',
                       limit: Optional[int] = None,
                       params: Optional[dict] = None) -> Iterable[dict]:
        limit = min(limit or consts.DEVICE_PER_PAGE, consts.DEVICE_PER_PAGE)
        params = params or dict()
        try:
            total = self._get_total(api_endpoint, params)
        except Exception as e:
            message = f'Failed to fetch total result count for request "{api_endpoint}"!'
            logger.exception(message)
            raise RESTException(f'{message} Error: {str(e)}')
        params.setdefault('limit', limit)
        params.setdefault('start', 0)
        logger.info(f'Starting to fetch {total} results for {api_endpoint}.')
        count_so_far = 0
        while count_so_far < total:
            try:
                resp = self._client.api_request(api_endpoint, params)
            except Exception as e:
                message = f'Request for {api_endpoint} failed with {str(e)}'
                logger.error(message)
                raise RESTException(message)
            results = resp.get(result_param)
            if isinstance(results, list):
                yield from results
            elif isinstance(results, dict):
                yield results
            else:
                raise RESTException(f'Got bad results: {results}')
            this_page = resp.get('current')
            if not isinstance(this_page, int):
                raise RESTException(f'Failed to parse result count from {resp}')
            count_so_far += this_page
            if not this_page:
                logger.info(f'Got 0 results after {count_so_far}, out of total {total}')
                break
            params['start'] += this_page
        logger.info(f'Finished fetching results for {api_endpoint}, yielded {count_so_far} out of {total} results.')

    def _paginated_device_get(self):
        try:
            yield from self._paginated_get('devices/index')
        except Exception:
            logger.exception(f'Invalid request made while paginating devices')
            raise

    def close(self):
        self._client = None
        return super().close()

    def get_device_list(self):
        try:
            yield from self._paginated_device_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
