import logging
import time

from axonius.clients.rest.connection import RESTException
from axonius.clients import tanium
from tanium_adapter.consts import CACHE_EXPIRATION, CACHE_DT_FMT, PAGE_SIZE, MAX_DEVICES_COUNT, HEADERS, PAGE_SLEEP

logger = logging.getLogger(f'axonius.{__name__}')


class TaniumPlatformConnection(tanium.connection.TaniumConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='', headers=HEADERS, **kwargs)

    def advanced_connect(self, client_config):
        self._tanium_get(endpoint='system_status', options={'row_count': 1, 'row_start': 0})

    # pylint: disable=arguments-differ, too-many-locals
    def get_device_list(self, client_name, client_config):
        server_version = self._get_version()
        workbenches = self._get_workbenches_meta()

        metadata = {
            'server_name': client_config['domain'],
            'client_name': client_name,
            'server_version': server_version,
            'workbenches': workbenches,
        }

        last_reg_mins = client_config.get('last_reg_mins', 0)
        for asset in self._get_assets(last_reg_mins=last_reg_mins):
            yield asset, metadata

    def _get_assets(self, last_reg_mins):
        page = 1
        row_start = 0
        fetched = 0
        options = {}
        total_all = 0
        logger.info(f'started fetch')

        if last_reg_mins:
            last_reg_dt = tanium.tools.dt_ago_mins(mins=last_reg_mins)
            last_reg_dt = self._cache_filter_dt(value=last_reg_dt)
            options['cache_filters'] = [
                {'field': 'last_registration', 'type': 'Date', 'operator': 'GreaterEqual', 'value': last_reg_dt}
            ]
            logger.debug(f'last seen mins={last_reg_mins}, filter={options["cache_filters"]}')

        while row_start < MAX_DEVICES_COUNT:
            try:
                options['row_start'] = row_start
                options['row_count'] = PAGE_SIZE
                options['cache_expiration'] = CACHE_EXPIRATION

                objs = self._tanium_get(endpoint='system_status', options=options)

                assets = []
                for obj in objs:
                    if obj.get('computer_id'):
                        assets.append(obj)
                    if obj.get('cache_id'):
                        options['cache_id'] = obj['cache_id']
                        total = obj['filtered_row_count']
                        total_all = obj['cache_row_count']

                this_fetch = len(assets)
                fetched += this_fetch

                left_to_fetch = total - fetched

                row_start += PAGE_SIZE

                stats = [
                    f'PAGE #{page} rows={this_fetch}',
                    f'fetched=[{fetched}/{total}]',
                    f'left={left_to_fetch}',
                    f'total unfiltered {total_all}',
                ]
                stats = ', '.join(stats)
                page += 1

                if assets:
                    logger.debug(f'fetched {stats}')
                    for asset in assets:
                        yield asset
                else:
                    logger.info(f'DONE no rows returned {stats}')
                    break

                if fetched >= total:
                    logger.info(f'DONE hit rows total {stats}')
                    break

                time.sleep(PAGE_SLEEP)
            except Exception as exc:
                raise RESTException(f'ERROR fetching assets: {exc}')

        logger.info(f'finished fetch')

    @staticmethod
    def _cache_filter_dt(value):
        return value.strftime(CACHE_DT_FMT)
