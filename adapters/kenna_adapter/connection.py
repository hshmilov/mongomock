import logging
import time
from datetime import datetime, timedelta

from typing import Optional, Tuple
from gzip import decompress as gzip_decompress
from retrying import retry
from urllib3.util import parse_url

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException, RESTRequestException
from axonius.utils.json import from_json
from kenna_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class KennaRetryException(Exception):
    # HTTP Error code 429
    pass


class KennaConnection(RESTConnection):
    """ rest client for Kenna adapter """

    def __init__(self, api_token: str, *args,
                 use_export_api: bool=False, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._api_token = api_token
        self._use_export_api = use_export_api

    def _connect(self):
        if not self._api_token:
            raise RESTException('No API token')

        # Adjust url to the api subdomain, see:
        # https://apidocs.kennasecurity.com/reference#reference-getting-started
        api_url = consts.DOMAIN_RE.sub(consts.DOMAIN_TO_API_RE_REPLACE, self._url)
        if not consts.DOMAIN_RE.match(api_url):
            logger.warning(f'resulted api_url: {api_url}')
            raise RESTException('Invalid url given. must be https://mycompany.(eu.)kennasecurity.com.')
        self._url = str(parse_url(api_url))
        self._permanent_headers['X-Risk-Token'] = self._api_token

        # Now actually do something to see its working
        if self._use_export_api:
            asset_count = self._get_temp_export_count('asset')
            if asset_count == 0:
                raise RESTException(f'Got 0 assets when attemping Kenna assets export')
        else:
            for _ in self._get_endpoint_api('assets'):
                break

    # pylint: disable=arguments-differ
    @retry(stop_max_attempt_number=3,
           retry_on_exception=lambda exc: isinstance(exc, KennaRetryException))
    def _do_request(self, *args, **kwargs):
        return super()._do_request(*args, **kwargs)

    def _handle_response(self, response, *args, **kwargs):
        if response.status_code == 429:
            raise KennaRetryException()
        return super()._handle_response(response, *args, **kwargs)

    def _get_temp_export_count(self, model_type: str,
                               updated_since_time_specifier: Optional[str] = None,
                               export_additional_params: Optional[dict] = None) -> Optional[int]:
        export_result = self._generate_data_export(
            model_type,
            updated_since_time_specifier=updated_since_time_specifier,
            export_additional_params=export_additional_params)
        if not export_result:
            return None
        search_id, is_new_export, record_count = export_result

        if (is_new_export or
                (isinstance(record_count, int) and record_count == 0)):
            # best effort kill
            try:
                response = self._put('data_exports/kill', url_params={'export_id': search_id})
                logger.debug(f'Killed temporary search {search_id}: {response}')
            except Exception:
                logger.warning(f'Failed removing temporary {model_type} temp export of id {search_id}',
                               exc_info=True)

        return record_count

    def _get_endpoint_api(self, endpoint):
        logger.info(f'Fetching endpoint {endpoint}')
        print_total = True
        curr_page = 1
        # Note: initial value used only for initial while iteration
        total_pages = curr_page
        try:
            while curr_page <= total_pages:

                response = self._get(endpoint, url_params={'per_page': consts.DEVICE_PER_PAGE, 'page': curr_page})
                yield from (response.get(endpoint) or [])

                meta = response.get('meta') or {}
                if not meta:
                    logger.debug(f'No "meta" found, halting pagination after {curr_page}/{total_pages}')
                    return

                try:
                    curr_page = int(meta.get('page'))
                    if curr_page % 10 == 0:
                        logger.info(f'Got to page {curr_page} of endpoint {endpoint}')
                    total_pages = int(meta.get('pages'))
                    if print_total:
                        print_total = False
                        logger.info(f'Got {total_pages} pages for {endpoint}')
                except (ValueError, TypeError):
                    logger.exception(f'Received invalid meta values {meta} after/on {curr_page}/{total_pages}')
                    return

                curr_page = curr_page + 1
        except Exception:
            logger.exception(f'Failed paginated request after {curr_page}/{total_pages}')

    def _generate_data_export(self, model_type: str,
                              updated_since_time_specifier: Optional[str] = None,
                              export_additional_params: Optional[dict] = None) -> Optional[Tuple[str, bool, int]]:
        """

        :param model_type: supported types: 'asset', 'vulnerability', 'fix'
        :param updated_since_time_specifier: updated_since_time_specifier may be relative 'now-1h' or absolute isoformat
        :param export_additional_params: additional body_params for export
        :return: (search_id - result id
                  is_new_search - True if new search or False if existing one,
                  record_count - expected result count)
        """
        # Search IDs are valid for 30 days after the initial request is made.

        if not isinstance(export_additional_params, dict):
            export_additional_params = dict()

        if isinstance(updated_since_time_specifier, str):
            export_additional_params.setdefault('records_updated_since', updated_since_time_specifier)

        body_params = {
            **export_additional_params,
            'export_settings': {
                'format': 'json',
                'model': model_type,
                'slim': True,
            }
        }

        # start data export
        logger.info(f'Starting data export for {model_type}')
        response = self._post('data_exports',
                              body_params=body_params,
                              raise_for_status=False,
                              use_json_in_response=False,
                              return_response_raw=True)

        is_new_export = (response.status_code != consts.EXPORT_ERROR_EXISTING)
        response = self._handle_response(
            response,
            use_json_in_response=True,
            # raise only if we cannot proceed
            raise_for_status=(response.status_code not in consts.EXPORT_VALID_ERROR_CODES))
        if not (isinstance(response, dict) and response.get('search_id')):
            logger.error(f'Invalid response got from data export: {response}')
            return None

        search_id = response.get('search_id')
        record_count = response.get('record_count')
        logger.info(f'Found search: {search_id}, is_new: {is_new_export},'
                    f' expecting {record_count} {model_type} records')

        return search_id, is_new_export, record_count

    def _get_export_results(self, search_id, result_field: str):

        url_params = {
            'search_id': search_id,
        }

        response = None
        logger.info(f'Fetching export for search {search_id}')
        end_time = datetime.utcnow() + timedelta(seconds=consts.MAX_EXPORT_EXECUTION_TIME)
        while datetime.utcnow() < end_time:
            response = self._get('data_exports',
                                 url_params=url_params,
                                 use_json_in_response=False,
                                 return_response_raw=True)
            try:
                # During export execution, results are JSON
                response = self._handle_response(response, use_json_in_response=True)
            except RESTRequestException:
                # once export completed, the response will be GZIPed json,
                # thrown on JsonDecodeError in _handle_response
                try:
                    response = from_json(gzip_decompress(response.content).decode('utf-8'))
                except Exception:
                    logger.exception(f'Failed to parse gzip response')
                    return

            if not isinstance(response, dict):
                logger.error(f'Invalid response received from data exports: {response}')
                return

            if (isinstance(response.get('message'), str) and
                    consts.EXPORT_STATUS_RETRY.lower() in response.get('message').lower()):
                logger.info(f'Export still running, sleeping for {consts.EXPORT_SAMPLE_SLEEP_TIME} seconds.')
                time.sleep(consts.EXPORT_SAMPLE_SLEEP_TIME)
                continue

            logger.info(f'Export completed.')
            break

        if not (response and isinstance(response, dict)):
            logger.warning(f'no valid response received within the execution limit: {response}')
            return

        if not (response.get(result_field) and
                isinstance(response.get(result_field), list)):
            logger.warning(f'no or invalid {result_field}, type: {type(response.get(result_field))}')
            logger.debug(f'{response.get(result_field)}')
            return

        yield from response.get(result_field)

    def _list_vulnerabilites_by_asset_id(self):

        fixes_by_cve_id = self._list_fixes_by_cve_id()

        asset_vuln_dict = dict()
        for vuln_raw in self._get_endpoint_api('vulnerabilities'):
            if not vuln_raw.get('asset_id') or not vuln_raw.get('cve_id'):
                continue
            vuln_raw['fixes'] = fixes_by_cve_id.get(vuln_raw['cve_id']) or []
            if vuln_raw.get('asset_id') not in asset_vuln_dict:
                asset_vuln_dict[vuln_raw.get('asset_id')] = []
            asset_vuln_dict[vuln_raw.get('asset_id')].append(vuln_raw)

        return asset_vuln_dict

    def _list_vulnerabilites_by_asset_id_using_export(self, vuln_search_id, fixes_search_id):

        fixes_by_cve_id = self._list_fixes_by_cve_id_using_export(fixes_search_id)

        asset_vuln_dict = dict()

        for vuln_raw in self._get_export_results(vuln_search_id, 'vulnerabilities'):
            if not vuln_raw.get('asset_id') or not vuln_raw.get('cve_id'):
                continue
            vuln_raw['fixes'] = fixes_by_cve_id.get(vuln_raw['cve_id']) or []
            if vuln_raw.get('asset_id') not in asset_vuln_dict:
                asset_vuln_dict[vuln_raw.get('asset_id')] = []
            asset_vuln_dict[vuln_raw.get('asset_id')].append(vuln_raw)

        return asset_vuln_dict

    def _list_fixes_by_cve_id(self):
        fixes_by_cve_id = dict()
        try:
            for fix in self._get_endpoint_api('fixes'):
                for cve_id in (fix.get('cves') or []):
                    if cve_id not in fixes_by_cve_id:
                        fixes_by_cve_id[cve_id] = []
                    fixes_by_cve_id[cve_id].append(fix)
        except Exception:
            logger.exception(f'Problem with fixes')
        return fixes_by_cve_id

    def _list_fixes_by_cve_id_using_export(self, search_id):
        fixes_by_cve_id = dict()
        if not search_id:
            return fixes_by_cve_id
        try:

            for fix in self._get_export_results(search_id, 'fixes'):
                for cve_id in (fix.get('cves') or []):
                    if cve_id not in fixes_by_cve_id:
                        fixes_by_cve_id[cve_id] = []
                    fixes_by_cve_id[cve_id].append(fix)
        except Exception:
            logger.exception(f'Problem with fixes')
        return fixes_by_cve_id

    def _get_device_list_using_export(self):

        # start async export of the various model types, they will have 30 days lifespan
        # ASSETS
        assets_export = self._generate_data_export('asset',
                                                   export_additional_params={
                                                       'status': ['active'],
                                                       'exclude_child_filter': ['Include all assets'],
                                                   })
        if not assets_export:
            logger.info(f'No assets received')
            return
        assets_search_id, *_ = assets_export

        # Vulnerabilites
        vulnerabilites_export = self._generate_data_export('vulnerability',
                                                           export_additional_params={'status': ['open']})
        vuln_search_id = None
        if vulnerabilites_export:
            vuln_search_id, *_ = vulnerabilites_export
        else:
            logger.info(f'No vulnerabilities received')
            # fallthrough

        # Fixes
        fixes_search_id = None
        fixes_export = self._generate_data_export('fix')
        if fixes_export:
            fixes_search_id, *_ = fixes_export
        else:
            logger.info(f'No fixes received')
            # fallthrough

        vulnerabilities_by_asset_id = self._list_vulnerabilites_by_asset_id_using_export(
            vuln_search_id=vuln_search_id, fixes_search_id=fixes_search_id)

        for asset in self._get_export_results(assets_search_id, 'assets'):
            if not (isinstance(asset, dict) and asset.get('id')):
                continue
            asset_vulns = vulnerabilities_by_asset_id.get(asset['id']) or []
            yield asset, asset_vulns

    def get_device_list(self):
        if self._use_export_api:
            yield from self._get_device_list_using_export()
        else:
            vulnerabilities_by_asset_id = self._list_vulnerabilites_by_asset_id()
            for asset in self._get_endpoint_api('assets'):
                if not asset.get('id'):
                    continue
                asset_vulns = vulnerabilities_by_asset_id.get(asset['id']) or []
                yield asset, asset_vulns
