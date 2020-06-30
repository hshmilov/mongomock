import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from rancher_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class RancherConnection(RESTConnection):
    """ rest client for Rancher adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password given')
        body_params = {'username': self._username,
                       'password': self._password}
        response = self._post(consts.RANCHER_LOGIN_PROVIDER_LOCAL, body_params=body_params)
        if not (isinstance(response, dict) and response.get('token')):
            raise RESTException(f'Invalid login response retrieved: {response}')
        self._token = response['token']
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        next(self._iter_nodes(total_limit=1), None)

    def _paginated_get(self, *args, total_limit: int = consts.MAX_NUMBER_OF_DEVICES, **kwargs):
        url_params = kwargs.setdefault('url_params', {})
        # per page limit
        url_params['limit'] = min(consts.DEVICE_PER_PAGE, total_limit)
        count_so_far = 0

        # Make sure total_limit doesnt exceed MAX DEVICES
        total_limit = min(total_limit, consts.MAX_NUMBER_OF_DEVICES)

        # perform initial request
        response = self._get(*args, **kwargs)
        if not (isinstance(response, dict) and isinstance(response.get('data'), list)):
            raise RESTException(f'Invalid response received {response}')

        data_list = response.get('data')
        logger.debug(f'Yielding {len(data_list)}')
        yield from data_list
        count_so_far += len(data_list)

        pagination = response.get('pagination')
        if not isinstance(pagination, dict):
            logger.warning(f'No pagination information received')
            return

        total_count = None
        try:
            # Note: total_count is not required to return by Rancher's api-spec, so we dont rely on it
            # https://github.com/rancher/api-spec/blob/master/specification.md#pagination
            total_count = int(pagination.get('total'))
            logger.info(f'Got total_count {total_count}')
            # reduce total_limit if needed to total_count
            total_limit = min(total_limit, total_count)
        except Exception as e:
            logger.warning(f'Failed locating total in pagination: {pagination}. {str(e)}', exc_info=True)
            # fallthrough, we dont rely on total_count

        # Second page onwards - we use 'next' links as full_url as instructed.
        kwargs['force_full_url'] = True

        while (pagination.get('next') and count_so_far < total_limit):

            response = self._get(pagination.get('next'), **kwargs)
            if not (isinstance(response, dict) and isinstance(response.get('data'), list)):
                raise RESTException(f'Invalid response received {response}')
            data_list = response.get('data')
            logger.debug(f'Yielding {len(data_list)}')
            yield from data_list
            count_so_far += len(data_list)

            pagination = response.get('pagination')
            if not isinstance(pagination, dict):
                logger.warning(f'No pagination information received')
                return
        logger.info(f'Done pagination after {count_so_far}/{total_count}')

    def _iter_nodes(self, total_limit: int = consts.MAX_NUMBER_OF_DEVICES):
        yield from self._paginated_get(consts.RANCHER_API_NODES, total_limit=total_limit)

    def get_device_list(self):
        yield from self._iter_nodes()
