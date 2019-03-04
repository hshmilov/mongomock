import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from carbonblack_defense_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class CarbonblackDefenseConnection(RESTConnection):

    def __init__(self, *args, connector_id: str = None, **kwargs):
        self._connector_id = connector_id
        super().__init__(*args, url_base_prefix='integrationServices/v3/',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json',
                                  }, **kwargs)
        self._permanent_headers['X-Auth-Token'] = f'{self._apikey}/{self._connector_id}'

    def _connect(self):
        self._get('device')

    def get_device_list(self):
        row_number = 1
        raw_results = self._get('device', url_params={'rows': str(consts.DEVICES_PER_PAGE), 'start': str(row_number)})
        total_count = raw_results['totalResults']
        logger.info(f'Carbonblack Defense API returned a count of {total_count} devices')
        yield from raw_results['results']
        try:
            while row_number + consts.DEVICES_PER_PAGE <= total_count and row_number <= consts.MAX_NUMBER_OF_DEVICES:
                row_number += consts.DEVICES_PER_PAGE
                yield from self._get('device', url_params={'rows': str(consts.DEVICES_PER_PAGE),
                                                           'start': str(row_number)})['results']
        except Exception:
            logger.exception(f'Problem getting device in row number: {row_number}')

    def change_policy(self, device_id, policy_name):
        response = self._patch(f'device/{device_id}',
                               body_params={'policyName': policy_name})
        if not response.get('success') is True:
            raise RESTException(f'Bad response for policy change: {response[:300]}')
        return response.get('deviceInfo')
