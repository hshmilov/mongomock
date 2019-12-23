import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from carbonblack_defense_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class CarbonblackDefenseV6Connection(RESTConnection):

    def __init__(self, *args, connector_id: str = None, org_key=None, **kwargs):
        self._connector_id = connector_id
        super().__init__(*args, url_base_prefix=f'appservices/v6/orgs/{org_key}',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json',
                                  }, **kwargs)
        self._permanent_headers['X-Auth-Token'] = f'{self._apikey}/{self._connector_id}'
        self._org_key = org_key

    def _connect(self):
        if not self._org_key or not self._apikey or not self._connector_id:
            raise RESTException('No API Key or Connector ID or Organization Key')
        self._post('devices/_search', body_params={'rows': str(consts.DEVICES_PER_PAGE), 'start': str(0)})

    def get_device_list(self):
        for device_raw in self.get_device_list_v6():
            yield device_raw, consts.V6_DEVICE

    def get_device_list_v6(self):
        row_number = 0
        raw_results = self._post('devices/_search',
                                 body_params={'rows': str(consts.DEVICES_PER_PAGE), 'start': str(row_number)})
        num_found = raw_results['num_found']
        row_number += consts.DEVICES_PER_PAGE
        logger.info(f'Carbonblack Defense API V6 returned a count of {num_found} devices')
        yield from raw_results['results']
        try:
            while row_number <= min(num_found, consts.MAX_NUMBER_OF_DEVICES):
                yield from self._post('devices/_search',
                                      body_params={'rows': str(consts.DEVICES_PER_PAGE),
                                                   'start': str(row_number)})['results']
                row_number += consts.DEVICES_PER_PAGE

        except Exception:
            logger.exception(f'Problem getting device v6 in row number: {row_number}')

    def _return_device_data(self, device_id):
        return self._get(f'devices/{device_id}')

    def quarantine(self, device_id, toggle):
        if toggle not in ['ON', 'OFF']:
            raise RESTException(f'Bad toggle option: {toggle}')
        self._post('device_actions', body_params={'device_id': [device_id],
                                                  'action_type': 'QUARANTINE',
                                                  'options': {'toggle': toggle}})
        return self._return_device_data(device_id), consts.V6_DEVICE
