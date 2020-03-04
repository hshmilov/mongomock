import logging

from axonius.clients import tanium
from axonius.clients.rest.connection import RESTException
from tanium_discover_adapter.consts import HEADERS, MAX_DEVICES_COUNT, PAGE_SIZE, SELECT_FIELDS

logger = logging.getLogger(f'axonius.{__name__}')


class TaniumDiscoverConnection(tanium.connection.TaniumConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='', headers=HEADERS, **kwargs)

    def advanced_connect(self, client_config):
        self._get_devices_page(page_size=1, page_count=1)

    # pylint: disable=arguments-differ
    def get_device_list(self, client_name, client_config):
        server_version = self._get_version()
        workbenches = self._get_workbenches_meta()

        metadata = {
            'server_name': client_config['domain'],
            'client_name': client_name,
            'server_version': server_version,
            'workbenches': workbenches,
        }

        page = 1
        fetched = 0
        columns_printed = False

        logger.info(f'started fetch')

        while fetched < MAX_DEVICES_COUNT:
            try:
                response = self._get_devices_page(page_size=PAGE_SIZE, page_count=page)
                total = response.get('Total') or 0
                total_check = min(total, MAX_DEVICES_COUNT)
                items = response.get('Items')
                columns = response.get('Columns')

                this_fetch = len(items)
                fetched += this_fetch
                stats = f'page={page}, rows={this_fetch}, fetched=[{fetched}/{total}]'

                if not items or not isinstance(items, list):
                    logger.error(f'DONE no items returned {response} {stats}')
                    break

                logger.debug(f'WAIT fetched {stats}')

                for item in items:
                    yield dict(zip(columns, item)), metadata

                if not columns_printed:
                    logger.debug(f'found columns={columns}')
                    columns_printed = True

                if fetched >= total_check:
                    logger.info(f'DONE all assets fetched {stats}')
                    break

                page += 1
            except Exception as exc:
                raise RESTException(f'ERROR during fetch page={page}, fetched={fetched}: {exc}')

    def _get_devices_page(self, page_size, page_count):
        page = {'Size': page_size, 'Number': page_count}
        body_params = {
            'Id': 'all',
            'Name': 'All Interfaces',
            'Filter': [],
            'Page': page,
            'Select': [{'Field': x} for x in SELECT_FIELDS],
            'KeywordFilter': '',
            'CountsOnly': False,
            'ManagementCounts': False,
        }

        try:
            return self._post('plugin/products/discover/report', body_params=body_params)
        except Exception:
            raise RESTException(f'ERROR during fetch page={page}')
