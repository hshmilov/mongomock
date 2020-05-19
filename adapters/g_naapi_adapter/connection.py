import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')
ENTITIES_PER_PAGE = 1000


class GNaapiConnection(RESTConnection):
    """ rest client for GNaapi adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')

        self._permanent_headers['x-api-key'] = self._apikey

        try:
            for _ in self.get_device_list():
                break
        except Exception:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials')

    def naapi_get(self, endpoint, size=ENTITIES_PER_PAGE, search_after=None):
        url_params = {'size': size}
        if search_after:
            url_params['search_after'] = search_after

        return self._get(
            endpoint,
            url_params=url_params
        )

    def _paginated_device_get(self, endpoint: str):
        try:
            result = self.naapi_get(endpoint)
            hits = result.get('hits')
            if not isinstance(hits, dict) or not hits:
                raise ValueError(f'Invalid hits: {hits}')

            total = hits.get('total')
            logger.info(f'Endpoint "{endpoint}": total of {str(total)} entities')
            items = hits.get('hits') or []
            logger.debug(f'Endpoint "{endpoint}": Yielding {len(items)} items')
            for item in items:
                if item.get('_source'):
                    yield item.get('_source')

            while items:
                last_id = items[-1]['_id']
                result = self.naapi_get(endpoint, search_after=last_id)
                items = (result.get('hits') or {}).get('hits') or []
                logger.debug(f'Endpoint "{endpoint}": Yielding {len(items)} items')
                for item in items:
                    if item.get('_source'):
                        yield item.get('_source')
        except Exception:
            logger.exception(f'Invalid request made while paginating devices')
            raise

    def get_device_list(self):
        try:
            for device in self._paginated_device_get('aws/ec2/instance'):
                yield device
        except RESTException as err:
            logger.exception(str(err))
            raise

    @staticmethod
    def _paginated_user_get():
        yield from []

    def get_user_list(self):
        try:
            yield from self._paginated_user_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
