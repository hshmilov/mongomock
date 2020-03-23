import logging
from functools import partialmethod
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
        _ = list(self._iter_assets(1))

    #pylint: disable=arguments-differ
    @retry(stop_max_attempt_number=3,
           retry_on_exception=lambda exc: isinstance(exc, KennaRetryException))
    def _do_request(self, *args, **kwargs):
        return super()._do_request(*args, **kwargs)

    def _handle_response(self, response, *args, **kwargs):
        if response.status_code == 429:
            raise KennaRetryException()
        return super()._handle_response(response, *args, **kwargs)

    def _paginated_request(self, *args, **kwargs):
        url_params = kwargs.setdefault('url_params', {})
        url_params.setdefault('per_page', consts.DEVICE_PER_PAGE)
        curr_page = url_params.setdefault('page', 1)  # 1-indexed based
        # Note: initial value used only for initial while iteration
        total_pages = curr_page
        try:
            while curr_page <= total_pages:

                url_params['page'] = curr_page
                response = self._do_request(*args, **kwargs)
                yield response

                meta = response.get('meta') or {}
                if not meta:
                    logger.debug(f'No "meta" found, halting pagination after {curr_page}/{total_pages}')
                    return

                try:
                    curr_page = int(meta.get('page'))
                    total_pages = int(meta.get('pages'))
                except (ValueError, TypeError):
                    logger.exception(f'Received invalid meta values {meta} after/on {curr_page}/{total_pages}')
                    return

                curr_page = curr_page + 1
        except Exception:
            logger.exception(f'Failed paginated request after {curr_page}/{total_pages}')

    def _paginated_request_iter(self, *args, iteration_field: str,
                                limit: int = consts.MAX_NUMBER_OF_DEVICES, **kwargs):
        total_count = 0
        count_so_far = 0
        for response in self._paginated_request(*args, **kwargs):
            iteration_value = response.get(iteration_field)
            if not isinstance(iteration_value, list):
                logger.error(f'Received invalid "{iteration_field}" for response: {response}')
                return

            iteration_value_len = len(iteration_value)
            count_so_far += iteration_value_len
            if response.get('total_count') and (total_count != response.get('total_count')):
                try:
                    total_count = int(response.get('total_count'))
                except Exception:
                    logger.exception(f'encountered invalid total_count {response.get("total_count")}')

            logger.debug(f'Yielding {iteration_value_len} "{iteration_field}" ({count_so_far} incl./{total_count})')
            yield from iteration_value

            if count_so_far >= min(total_count, limit):
                logger.debug(f'Done yielding {total_count} "{iteration_field}"')
                return

    _paginated_get_iter = partialmethod(_paginated_request_iter, 'GET')
    _paginated_post_iter = partialmethod(_paginated_request_iter, 'POST')

    def _iter_vulnerabilites(self):
        yield from self._paginated_get_iter('vulnerabilities', iteration_field='vulnerabilities')

    def _list_vulnerabilites_by_asset_id(self, include_fixes=True):

        fixes_by_cve_id = {} if not include_fixes else self._list_fixes_by_cve_id()

        def _adjust_vuln(vuln):
            if not vuln.get('asset_id'):
                # no asset to hold this vuln
                return None

            if include_fixes and vuln.get('cve_id'):
                # Note: injected list
                vuln['fixes'] = fixes_by_cve_id.get(vuln['cve_id']) or []

            return vuln

        return {vuln['asset_id']: vuln for vuln in map(_adjust_vuln, self._iter_vulnerabilites())
                if vuln}

    def _iter_assets(self, limit=consts.MAX_NUMBER_OF_DEVICES):
        yield from self._paginated_get_iter('assets', iteration_field='assets', limit=limit)

    def _iter_fixes(self):
        yield from self._paginated_get_iter('fixes', iteration_field='fixes')

    def _list_fixes_by_cve_id(self):
        fixes_by_cve_id = {}
        for fix in self._iter_fixes():
            for cve_id in (fix.get('cves') or []):
                fixes_by_cve_id.setdefault(cve_id, []).append(fix)
        return fixes_by_cve_id

    def get_device_list(self):
        vulnerabilities_by_asset_id = self._list_vulnerabilites_by_asset_id(include_fixes=True)
        yield from ((asset, vulnerabilities_by_asset_id.get(asset['id']) or [])
                    for asset in self._iter_assets()
                    if asset.get('id'))

        # yield from zip(self._iter_assets(), repeat()
