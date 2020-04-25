# pylint: disable=logging-format-interpolation,broad-except
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from sophos_cloud_optix_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class SophosCloudOptixConnection(RESTConnection):
    """ REST client for Sophos Cloud Optix adapter """

    def __init__(self, *args, providers: dict, **kwargs):
        super().__init__(*args,
                         url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._providers = providers

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API key found.')
        self._session_headers['Authorization'] = f'ApiKey {self._apikey}'

        if not self._providers:
            self._providers = {'AWS': True, 'Azure': True, 'GCP': True}

        providers = (k for k, v in self._providers.items() if v is True)
        for provider in providers:
            self._get(consts.HOST_ENDPOINT, url_params={'provider': provider,
                                                        'page': 0,
                                                        'size': consts.MIN_DEVICES_PER_PAGE})

    def get_lists(self, endpoint: str):
        providers = [k for k, v in self._providers.items() if v is True]
        for provider in providers:
            page = 0
            has_next = True
            try:
                while has_next:
                    response = self._get(endpoint,
                                         url_params={'provider': provider,
                                                     'size': consts.DEVICE_PER_PAGE,
                                                     'page': page
                                                     })

                    if not isinstance(response, dict):
                        logger.warning(f'Invalid response got for provider {provider} on page {page}: {response}')
                        break

                    if not isinstance(response.get('data'), list):
                        logger.info(f'No data found for provider {provider} on page {page}, Halting')
                        break

                    yield from response.get('data')

                    if not response.get('hasNext'):
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
