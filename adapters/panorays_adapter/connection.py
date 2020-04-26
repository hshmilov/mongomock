import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from panorays_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class PanoraysConnection(RESTConnection):
    """ rest client for Panorays adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._permanent_headers['Authorization'] = f'Bearer {self._apikey}'

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')

        self._get('assets')

    def _paginated_get(self, endpoint):
        try:
            skip = 0
            while skip < MAX_NUMBER_OF_DEVICES:
                try:
                    if skip == 0:
                        skip = None
                    response = self._get(endpoint, url_params={'skip': skip,
                                                               'limit': DEVICE_PER_PAGE})
                    if not skip:
                        skip = 0
                    yield from response
                    if len(response) < DEVICE_PER_PAGE:
                        break
                    skip += DEVICE_PER_PAGE
                except Exception:
                    logger.exception(f'Problem with count {skip}')
                    if skip == 0:
                        return
                    raise
        except Exception:
            logger.exception(f'Invalid request made while paginating devices')
            raise

    def get_device_list(self):
        try:
            findings_dict = dict()
            try:
                for finding_raw in self._paginated_get('findings'):
                    if not isinstance(finding_raw, dict) or not finding_raw.get('asset_name'):
                        continue
                    if finding_raw.get('asset_name') not in findings_dict:
                        findings_dict[finding_raw.get('asset_name')] = []
                    findings_dict[finding_raw.get('asset_name')].append(finding_raw)
            except Exception:
                logger.exception(f'Problem getting findings')
            for device_raw in self._paginated_get('assets'):
                yield device_raw, findings_dict
        except RESTException as err:
            logger.exception(str(err))
            raise
