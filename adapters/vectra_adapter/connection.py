import logging
# pylint: disable=import-error
from vat.vectra import VectraClient

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class VectraConnection(RESTConnection):
    """ rest client for Vectra adapter """

    def __init__(self, *args, domain, token, verify_ssl, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         domain=domain,
                         verify_ssl=verify_ssl,
                         **kwargs)
        self._token = token
        self._vc = VectraClient(url=self._domain,
                                token=self._token,
                                verify=self._verify_ssl)

    def _connect(self):
        if not self._token:
            raise RESTException('No token')

        try:
            self._vc.get_hosts(page=1, page_size=1)
        except Exception:
            logger.exception(f'Failed validate connection')
            raise

    def _paginated_get(self):
        try:
            response = self._vc.get_all_hosts()
            for page in response:
                logger.info(f'got {page}')
                try:
                    logger.info(f'got {page.json()}')
                except Exception:
                    logger.exception(f'Failed parsing json')
                break
        except Exception:
            logger.exception(f'Invalid request made')

    def get_device_list(self):
        try:
            yield from self._paginated_get()
        except RESTException as err:
            logger.exception(err)
            raise
