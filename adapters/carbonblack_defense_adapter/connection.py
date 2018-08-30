import logging

from axonius.clients.rest.connection import RESTConnection
from carbonblack_defense_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class CarbonblackDefenseConnection(RESTConnection):

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
