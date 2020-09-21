import logging
import time

from axonius.clients.rest.connection import RESTException
from axonius.clients.tanium import connection
from tanium_asset_adapter.consts import HEADERS, MAX_DEVICES_COUNT, PAGE_SIZE, PAGE_SLEEP

logger = logging.getLogger(f'axonius.{__name__}')


class TaniumAssetConnection(connection.TaniumConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='', headers=HEADERS, **kwargs)

    def advanced_connect(self, client_config):
        self._get_asset_counts()
        self._get_assets_page(next_id=1, limit=1)

    @property
    def module_name(self):
        return 'asset'

    # pylint: disable=arguments-differ
    def get_device_list(self, client_name, client_config, page_size: int = PAGE_SIZE, page_sleep: int = PAGE_SLEEP):
        server_version = self._get_version()
        workbenches = self._get_workbenches_meta()

        metadata = {
            'server_name': client_config['domain'],
            'client_name': client_name,
            'server_version': server_version,
            'workbenches': workbenches,
        }
        for asset in self._get_assets(page_size=page_size, page_sleep=page_sleep):
            yield asset, metadata

    def _get_assets_page(self, next_id, limit):
        params = {'minimumAssetId': next_id, 'limit': limit}
        endpoint = 'plugin/products/asset/v1/assets'
        return self._get(endpoint, url_params=params)

    def _get_asset_counts(self):
        endpoint = 'plugin/products/asset/v1/stats/count'
        response = self._get(endpoint)
        logger.debug(f'fetched asset counts: {response}')
        return response

    def _get_assets(self, page_size: int = PAGE_SIZE, page_sleep: int = PAGE_SLEEP):
        next_id = 1
        fetched = 0
        page = 1
        page_size = page_size or PAGE_SIZE

        asset_counts = self._get_asset_counts()
        total = asset_counts['deviceCount']

        stop_at = min(total, MAX_DEVICES_COUNT)

        logger.info(f'START FETCH OF ASSETS')

        while fetched <= stop_at:
            try:
                logger.debug(f'Fetching page={page} with next_id={next_id}, limit={page_size}')

                response = self._get_assets_page(next_id=next_id, limit=page_size)

                data = response.get('data', []) or []
                meta = response['meta']
                fetched += len(data)

                logger.debug(f'Fetched page={page}, rows={len(data)}, fetched=[{fetched}/{total}], meta={meta}')

                yield from data

                if not data:
                    logger.info(f'DONE no rows returned in response: {response}')
                    break

                if meta.get('endOfReader', False):
                    logger.info(f'DONE endOfReader=True')
                    break

                next_id = meta.get('nextAssetId', next_id)

                page += 1
                time.sleep(page_sleep)
            except Exception as exc:
                raise RESTException(f'ERROR during fetch page={page}, fetched=[{fetched}/{total}]: {exc}')

        logger.info(f'FINISHED FETCH page={page}, fetched=[{fetched}/{total}]')
