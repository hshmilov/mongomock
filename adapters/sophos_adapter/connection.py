import logging

from sophos_adapter import consts
from axonius.clients.rest.connection import RESTConnection

logger = logging.getLogger(f'axonius.{__name__}')


class SophosConnection(RESTConnection):

    def __init__(self, authorization,  *args, **kwargs):
        super().__init__(*args, use_domain_path=True, **kwargs)
        if ' ' not in authorization:
            authorization = 'Basic ' + authorization
        self._permanent_headers = {'Content-Type': 'application/json',
                                   'Accept': 'application/json',
                                   'Authorization': authorization,
                                   'x-api-key':  self._apikey}

    def _connect(self):
        self._get('migration-tool/v1/endpoints')

    def get_device_list(self):
        response = self._get('migration-tool/v1/endpoints')
        yield from response['items']
        total_count = response['total']
        offset = consts.DEVICES_PER_PAGE
        while offset < min(consts.MAX_DEVICES, total_count):
            try:
                yield from self._get('migration-tool/v1/endpoints', url_params={'offset': offset})['items']
            except Exception:
                logger.exception(f'Problem getting offset {offset}')
            offset += consts.DEVICES_PER_PAGE
