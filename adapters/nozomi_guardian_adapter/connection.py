import logging
from typing import Generator

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from nozomi_guardian_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class NozomiGuardianConnection(RESTConnection):
    """ rest client for NozomiGuardian adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        try:
            # perform a minimal query to raise any permission errors
            _ = next(self._iter_query('assets | head 1'))
        except Exception:
            message = 'Failed to fetch assets'
            logger.exception(message)
            raise RESTException(
                f'{message}, did you grant "Queries and Exports" permission to the provided user\'s group? ')

    # pylint: disable=arguments-differ
    def _do_request(self, *args, **kwargs):
        kwargs.setdefault('do_basic_auth', True)
        return super()._do_request(*args, **kwargs)

    def _paginated_get_iteration(self, *args, pagination_list_field='result', **kwargs) -> Generator[dict, None, None]:
        url_params = kwargs.setdefault('url_params', {})
        url_params.setdefault('count', consts.DEVICE_PER_PAGE)
        curr_page = url_params.setdefault('page', 1)
        count_so_far = 0
        # value used only for initial while iteration
        total_count = None
        while count_so_far < min(total_count or 1, consts.MAX_NUMBER_OF_DEVICES):
            url_params['page'] = curr_page
            response = self._get(*args, **kwargs)
            if not isinstance(response, dict):
                logger.error(f'Invalid response received on page {curr_page}: {response}')
                return

            if response.get('error'):
                logger.error(f'Error received on page {curr_page}: {response}')
                return

            pagination_list = response.get(pagination_list_field) or []
            if not isinstance(pagination_list, list):
                logger.warning(f'Unknown "{pagination_list_field}" encountered on offset {count_so_far},'
                               f' Halting. Value: {pagination_list}')
                return

            curr_count = len(pagination_list)
            # set total_count on initial iteration
            if total_count is None:
                total_count = response.get('total')
                if isinstance(total_count, str):
                    try:
                        total_count = int(response.get('total'))
                    except Exception:
                        total_count = None
                if not isinstance(response.get('total'), int):
                    logger.warning(f'Invalid total found in response: {response}')
                else:
                    logger.info(f'Fetching overall {total_count} "{pagination_list_field}".')
            count_so_far += curr_count

            logger.debug(f'yielding {curr_count} "{pagination_list_field}" ({count_so_far} incl./{total_count})')

            yield from pagination_list

            # if total_count was not set, exit
            if total_count is None:
                logger.warning(f'No total_count')
                break

            curr_page += 1
        logger.info(f'Done paginated request after {count_so_far}/{total_count}')

    def _iter_query(self, query: str):
        logger.debug(f'running query "{query}"')
        yield from self._paginated_get_iteration('api/open/query/do', url_params={'query': query})

    def get_device_list(self):
        yield from self._iter_query('assets')
