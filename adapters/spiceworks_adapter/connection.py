import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from spiceworks_adapter.consts import USERNAME_LOGIN, PASSWORD_LOGIN, REST_PATH_LOGIN, REST_PATH_API, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class SpiceworksConnection(RESTConnection):
    """ rest client for Spiceworks adapter """

    def __init__(self, *args, domain, username, password, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json'},
                         domain=domain,
                         username=username,
                         password=password,
                         **kwargs)

    def _create_params(self):
        self._body_params = {
            USERNAME_LOGIN: self._username,
            PASSWORD_LOGIN: self._password
        }

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._create_params()

        try:
            self._post(REST_PATH_LOGIN, body_params=self._body_params, use_json_in_body=False,
                       extra_headers={'Content-Type': 'application/x-www-form-urlencoded'},
                       use_json_in_response=False, return_response_raw=True)

            try:
                self._get(REST_PATH_API, url_params={'limit': 1, 'offset': 0})
            except Exception:
                raise ValueError(f'Error: Invalid response from server, please check credentials')
        except Exception:
            logger.exception(f'Failed validating connection')
            raise

    def _paginated_get(self, url):
        offset = 0
        response = self._get(url, url_params={'limit': DEVICE_PER_PAGE, 'offset': offset})
        yield from response
        while response:
            try:
                offset += len(response)
                response = self._get(url, url_params={'limit': DEVICE_PER_PAGE, 'offset': offset})
                yield from response
            except Exception:
                logger.exception(f'Invalid request made')
                break

    def _fetch_devices(self):
        try:
            yield from self._paginated_get(REST_PATH_API)
        except RESTException as err:
            logger.exception(err)
            raise

    def get_device_list(self):
        yield from self._fetch_devices()
