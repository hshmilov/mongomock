import logging
import re
import time

from axonius.clients import tanium
from axonius.clients.rest.connection import RESTException
from tanium_discover_adapter.consts import (
    HEADERS,
    MAX_DEVICES_COUNT,
    PAGE_SIZE,
    SELECT_FIELDS,
    SELECT_FAIL,
    PAGE_SLEEP,
    PAGE_ATTEMPTS,
    REPORT_KEYS,
    FETCH_OPTS,
    REPORTS_OLD,
)

logger = logging.getLogger(f'axonius.{__name__}')


class TaniumDiscoverConnection(tanium.connection.TaniumConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='', headers=HEADERS, **kwargs)

    def advanced_connect(self, client_config):
        fetches = self.check_fetch_opts(client_config=client_config)
        for report_id in fetches:
            report = self.get_report(report_id=report_id)
            list(self.get_report_page(report=report, page_size=1, page_count=1))

    @staticmethod
    def check_fetch_opts(client_config):
        fetch_opts = {x['report_id']: client_config.get(x['name'], x['default']) for x in FETCH_OPTS}
        if not any(list(fetch_opts.values())):
            raise RESTException(f'Must select at least one fetch option!')
        return [x for x in fetch_opts if fetch_opts[x]]

    @property
    def module_name(self):
        return 'discover'

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

        fetch_opts = self.check_fetch_opts(client_config=client_config)

        fetches = self.check_fetch_opts(client_config=client_config)
        for report_id in fetches:
            for asset in self.get_report_assets(report_id=report_id):
                yield asset, metadata

    def get_reports(self):
        if not getattr(self, '_reports', None):
            try_path = 'plugin/products/discover/report'
            response_raw = self._get(
                try_path, raise_for_status=False, use_json_in_response=False, return_response_raw=True,
            )
            code = response_raw.status_code
            if code == 405:
                logger.error(f'Failed GET against URL path {try_path!r} with code {code}, falling back to old reports')
                self._reports = REPORTS_OLD['v1'][:]
            else:
                self._reports = self._handle_response(response_raw)

                if isinstance(self._reports, dict) and 'data' in self._reports:
                    self._reports = self._reports['data']

                if not self._reports:
                    raise RESTException(f'No reports returned!')

            report_ids = [x.get('Id') for x in self._reports]
            logger.debug(f'Fetched report ids: {report_ids!r}')

        return self._reports

    def get_report(self, report_id):
        reports = self.get_reports()

        search = [x for x in reports if x.get('Id') == report_id]

        if not search:
            report_ids = [x.get('Id') for x in self._reports]
            raise RESTException(f'Report ID {report_id!r} not found - found ids: {report_ids!r}!')

        report = search[0]

        for key in REPORT_KEYS:
            if key not in report:
                msg = f'Invalid report! Report key {key} not found - found keys: {list(report)}'
                raise RESTException(msg)

        return report

    def get_report_assets(self, report_id):
        report = self.get_report(report_id=report_id)
        name = report.get('Name')
        page = 1
        fetched = 0

        while fetched < MAX_DEVICES_COUNT:
            try:
                response = self.get_report_page(report=report, page_size=PAGE_SIZE, page_count=page)
                total = response.get('Total') or 0
                total_check = min(total, MAX_DEVICES_COUNT)
                items = response.get('Items')
                columns = response.get('Columns')

                this_fetch = len(items)
                fetched += this_fetch
                stats = f'name={name!r}, page={page}, rows={this_fetch}, fetched=[{fetched}/{total}]'

                if not items or not isinstance(items, list):
                    msg = f'DONE no items returned in response={response}, {stats}'
                    logger.error(msg)
                    break

                logger.debug(f'WAIT {stats}')

                for item in items:
                    device_raw = dict(zip(columns, item))
                    device_raw['report_source'] = name
                    yield device_raw

                if fetched >= total_check:
                    logger.info(f'DONE all assets fetched {stats}')
                    break

                page += 1
                time.sleep(PAGE_SLEEP)
            except Exception as exc:
                msg = f'ERROR during fetch name={name!r}, page={page}, fetched={fetched}: error={exc}'
                raise RESTException(msg)

    def get_report_page(self, report, page_size, page_count):
        self._selects = getattr(self, '_selects', SELECT_FIELDS)
        module_version = self._get_module_version()
        name = report['Name']

        page = {'Size': page_size, 'Number': page_count}
        logger.debug(f'fetching report name={name!r}, page={page}')
        report['Page'] = page

        for i in range(len(self._selects)):
            report['Select'] = [{'Field': f'Asset.{x}'} for x in self._selects]

            response_raw, response_json = self.page_request(report=report)

            if response_raw.status_code != 200:
                message = str(response_json.get('message', ''))
                # SequelizeDatabaseError: SQLITE_ERROR: no such column: Interface.moo
                fail_match = re.search(SELECT_FAIL, message)
                if fail_match and fail_match.groups():
                    select = fail_match.groups()[0]
                    msg = (
                        f'Retrying name={name!r}, page={page}, select={select!r} removing select '
                        f'due to error {response_json!r} in module version {module_version!r}'
                    )
                    logger.error(msg)
                    self._selects.remove(select)
                    continue

            return self._handle_response(response_raw)
        raise RESTException(f'Unexpected error in name={name!r}, page={page}')

    def page_request(self, report):
        page = report['Page']
        name = report['Name']
        for i in range(PAGE_ATTEMPTS):
            try:
                response_raw = self._post(
                    'plugin/products/discover/report',
                    body_params=report,
                    raise_for_status=False,
                    use_json_in_response=False,
                    return_response_raw=True,
                )

                response_json = response_raw.json()
            except Exception as exc:
                logger.exception(f'ERROR attempt {i} name={name!r}, page={page}: {response_raw.text}')
                if i > PAGE_ATTEMPTS:
                    raise
            else:
                return response_raw, response_json

            time.sleep(PAGE_SLEEP)

        raise RESTException(f'Unexpected error in name={name!r}, page={page}')
