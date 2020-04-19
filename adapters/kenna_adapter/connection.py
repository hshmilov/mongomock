import logging
from retrying import retry
from urllib3.util import parse_url

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from kenna_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class KennaRetryException(Exception):
    # HTTP Error code 429
    pass


class KennaConnection(RESTConnection):
    """ rest client for Kenna adapter """

    def __init__(self, api_token: str, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._api_token = api_token

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

    def get_device_list(self):
        vulnerabilities_by_asset_id = self._list_vulnerabilites_by_asset_id()
        for asset in self._get_endpoint_api('assets'):
            if not asset.get('id'):
                continue
            asset_vulns = vulnerabilities_by_asset_id.get(asset['id']) or []
            yield asset, asset_vulns
