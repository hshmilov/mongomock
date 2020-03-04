import logging

from axonius.clients.rest.connection import RESTException
from axonius.clients.tanium import connection
from tanium_asset_adapter.consts import HEADERS, MAX_DEVICES_COUNT, PAGE_SIZE

logger = logging.getLogger(f'axonius.{__name__}')


class TaniumAssetConnection(connection.TaniumConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='', headers=HEADERS, **kwargs)

    def advanced_connect(self, client_config):
        self._get_report(report_name=client_config.get('asset_dvc'))

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
        report_name = client_config['asset_dvc']

        report = metadata['report'] = self._get_report(report_name=report_name)
        total = self._get_report_count(report=report)

        if not total:
            raise RESTException(f'Report {report_name!r} returned {total} devices')

        for asset in self._get_devices(report=report, total=total):
            yield asset, metadata

    def _get_report(self, report_name):
        pre = 'Get Report: '
        response = self._get('plugin/products/asset/private/reports')
        reports = response.get('data', []) or []

        if not reports:
            raise RESTException(f'{pre}no reports found!')

        report_names = ', '.join([x.get('reportName') for x in reports])

        try:
            report = [x for x in reports if x.get('reportName', '').lower().strip() == report_name.lower().strip()][0]
        except Exception:
            raise RESTException(f'{pre}report {report_name!r} not found, found reports: {report_names}')

        try:
            report_id = report['id']
            report = self._get(f'plugin/products/asset/private/reports/{report_id}')
        except Exception:
            msg = f'{pre}report {report_name!r} unable to be fetched'
            logger.exception(msg)
            raise RESTException(msg)

        attributes = report.get('meta', {}).get('attributes', [])
        entity_names = [x.get('entityName') for x in attributes]

        if 'Computer ID' not in entity_names:
            msg = f'{pre}report {report_name!r} does not have "Computer ID" attribute'
            raise RESTException(msg)
        return report

    def _get_report_count(self, report):
        pre = 'Get Report Asset Count: '
        report_info = report.get('data', {}).get('report', {})
        report_id = report_info['id']
        report_name = report_info['reportName']
        try:
            body_params = {'id': report_id, 'columnFilter': '{"$and":[]}'}
            response = self._post(
                f'plugin/products/asset/private/reports/{report_id}/rowCount', body_params=body_params,
            )
            report_count = response['data']
            logger.info(f'{pre}asset count={report_count}, report={report_name!r}')
            return report_count
        except Exception as exc:
            raise RESTException(f'Asset Module: ERROR getting asset count for report={report_name!r}: {exc}')

    def _get_devices(self, report, total):
        report_data = report['data']
        report_meta = report_data['report']
        report_id = report_meta['id']
        report_name = report_meta['reportName']
        fetched = 0
        page = 1
        total_check = min(total, MAX_DEVICES_COUNT)

        pre = 'Get Report Assets: '

        logger.info(f'{pre}started fetch of {total} assets for report {report_name!r}')

        while fetched <= total_check:
            try:
                body_params = {
                    'id': report_id,
                    'columnFilter': '{"$and":[]}',
                    'pagination': {'limit': PAGE_SIZE, 'offset': fetched},
                }
                response = self._post(
                    f'plugin/products/asset/private/reports/{report_id}/query', body_params=body_params,
                )
                rows = response['rows']
                this_fetch = len(rows)
                fetched += this_fetch
                stats = f'page={page}, rows={this_fetch}, fetched=[{fetched}/{total}]'

                if not rows or not isinstance(rows, list):
                    logger.error(f'{pre}DONE no rows returned {response} {stats}')
                    break

                logger.debug(f'{pre}WAIT fetched {stats}')
                for row in rows:
                    asset_id = row['ci_item_id']
                    try:
                        asset = self._get(f'plugin/products/asset/v1/assets/{asset_id}')
                        yield asset['data']
                    except Exception as exc:
                        raise RESTException(f'{pre}ERROR fetching asset {asset_id} for report {report_name!r}: {exc}')

                if fetched >= total_check:
                    logger.info(f'{pre}DONE all assets fetched {stats}')
                    break

                page += 1
            except Exception as exc:
                raise RESTException(f'{pre}ERROR during fetch page={page}, fetched={fetched}: {exc}')
