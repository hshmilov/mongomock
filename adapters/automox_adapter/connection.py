import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from automox_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class AutomoxConnection(RESTConnection):
    """ rest client for Automox adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API key')
        self._get('orgs',
                  url_params={'api_key': self._apikey})

    def _get_devices_from_org_id(self, org_id):
        page = 0
        while page * DEVICE_PER_PAGE < MAX_NUMBER_OF_DEVICES:
            try:
                response = self._get('servers',
                                     url_params={'api_key': self._apikey,
                                                 'o': org_id,
                                                 'l': DEVICE_PER_PAGE,
                                                 'p': page})
                if not isinstance(response, dict) or not response:
                    break
                if not response.get('results'):
                    break
                yield from response.get('results')
                page += 1
            except Exception:
                logger.exception(f'Problem with page {page}')
                break

    def get_device_list(self):
        response = self._get('orgs',
                             url_params={'api_key': self._apikey})
        org_ids = []
        for org_raw in response:
            if isinstance(org_raw, dict) and org_raw.get('id'):
                org_ids.append(org_raw.get('id'))
        for org_id in org_ids:
            try:
                yield from self._get_devices_from_org_id(org_id)
            except Exception:
                logger.exception(f'Problem with org ID {org_id}')
