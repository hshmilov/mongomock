# pylint: disable=logging-format-interpolation,broad-except
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from sophos_cloud_optix_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class SophosCloudOptixConnection(RESTConnection):
    """ REST client for Sophos Cloud Optix adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._session_headers['Authorization'] = f'ApiKey {self._apikey}'
        self._providers = kwargs.get('providers')

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API key found.')
        if not self._providers:
            self._providers = {'AWS': True, 'Azure': True, 'GCP': True}

        try:
            providers = (k for k, v in self._providers.items() if v is True)
            for provider in providers:
                self._get(consts.HOST_ENDPOINT, url_params={'provider': provider,
                                                            'page': 0,
                                                            'size': 1})
                break
        except Exception as err:
            logger.exception(f'Connection failed: {err}')

    def get_lists(self, endpoint: str):
        providers = (k for k, v in self._providers.items() if v is True)
        for provider in providers:
            page = 0
            has_next = True
            try:
                while has_next:
                    for data_raw in self._get(endpoint,
                                              url_params={'provider': provider,
                                                          'size': consts.DEVICE_PER_PAGE,
                                                          'page': page
                                                          }):
                        yield data_raw.get('data')

                        if not data_raw.get('hasNext'):
                            has_next = False
                        else:
                            page += 1

            except Exception:
                logger.exception(f'Data pull from {provider} to the '
                                 f'{endpoint} endpoint failed.')

    def get_device_list(self):
        yield from self.get_lists(endpoint=consts.HOST_ENDPOINT)

    def get_user_list(self):
        yield from self.get_lists(endpoint=consts.USER_ENDPOINT)
