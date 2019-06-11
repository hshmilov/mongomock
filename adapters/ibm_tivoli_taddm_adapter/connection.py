import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')
# TADDM Documentation says:
# A query with a depth greater than 1 can return a large result set, causing low-memory conditions on the TADDM server.
# To avoid this problem, specify fetchSize=1 and use consecutive queries to scroll through the data one
# position at a time
#
# Of course, we can not afford such a slow fetch. so we define it to be 5 but configurable.
DEFAULT_DEPTH = 5

# Max position to prevent infinite loop on errors
MAX_POSITION = 500000


class IBMTivoliTaddmConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            url_base_prefix='rest/model/',
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            session_timeout=(30, 1200),
            **kwargs
        )

    def get_computer_systems(self, depth, fetch_size, position):
        return self._get(
            'ComputerSystem',
            url_params={'depth': depth, 'feed': 'json', 'fetchSize': fetch_size, 'position': position},
            do_basic_auth=True
        )

    def _connect(self):
        if self._username and self._password:
            response = self.get_computer_systems(1, 1, 0)
            if not isinstance(response, list):
                raise ValueError(f'Error connecting: {response}')
        else:
            raise RESTException('No username or password')

    # pylint: disable=arguments-differ
    def get_device_list(self, fetch_size, depth=DEFAULT_DEPTH):
        if fetch_size <= 0 or depth <= 0:
            raise RESTException(f'Error, fetch size {fetch_size} depth {depth} is invalid')
        position = 0
        result = self.get_computer_systems(depth, fetch_size, position)
        yield from result
        while result and position < MAX_POSITION:
            try:
                position += fetch_size
                result = self.get_computer_systems(depth, fetch_size, position)
                yield from result
            except Exception:
                logger.exception(f'Error fetching from position {position}')
                break
