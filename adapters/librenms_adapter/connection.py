import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from librenms_adapter.consts import DATA_TYPES

logger = logging.getLogger(f'axonius.{__name__}')


class IteratorCounter:
    def __init__(self,
                 message,
                 start_value=0,
                 threshold=50):
        self._message = message
        self._count = start_value
        self._last_printed_value = self._count
        self._threshold = threshold

    def add(self, value=1):
        self._count += value

    def print_if_needed(self):
        if self._count - self._last_printed_value >= self._threshold:
            self._last_printed_value = self._count
            self.print()
            return True
        return False

    def print(self):
        logger.info(self._message.format(count=self._count))


def blockify(iter_, blksize):
    result = []
    for item in iter_:
        result.append(item)
        if len(result) == blksize:
            yield result
            result = []


class LibrenmsConnection(RESTConnection):
    """ rest client for Librenms adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v0',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._permanent_headers['X-Auth-Token'] = self._apikey

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')
        response = self._get('devices')
        if 'devices' not in response:
            raise RESTException(f'Bad response: {response}')

    def __get_extended_data_for_device(self, device_raw, data_types):
        for data_type in data_types:
            try:
                device_id = device_raw.get('device_id')
                device_raw[f'{data_type}_raw'] = self._get(f'devices/{device_id}/{data_type}')
            except Exception:
                logger.exception(f'Problem getting vlans data for {device_raw}')

    @staticmethod
    def __prepare_devices_requests(devices_ids):
        for device_id in devices_ids:
            for data_type in DATA_TYPES:
                yield {'name': f'devices/{device_id}/{data_type}'}

    @staticmethod
    def preapre_device_raw(device_raw, data_type_results):
        for data_type, data_type_result in zip(DATA_TYPES, data_type_results):
            if isinstance(data_type_result, Exception):
                logger.warning(f'Failed to fetch data type {data_type} for device id {device_raw["device_id"]}')
                continue
            if data_type_result.get('status') == 'error':
                message = data_type_result.get('message') or ''
                logger.debug(f'Device id {device_raw["device_id"]} data type {data_type} error message: {message}')
                continue
            device_raw[f'{data_type}_raw'] = data_type_result
        return device_raw

    def get_device_list(self):

        response = self._get('devices')

        if 'devices' not in response:
            raise RESTException(f'Bad response: {response}')

        devices_raw = [device_raw for device_raw in response['devices'] if device_raw.get('device_id')]
        devices_ids = [device_raw['device_id'] for device_raw in devices_raw]
        yielded_devices_count = IteratorCounter(f'Got {{count}} devices so far out of {len(devices_ids)}',
                                                threshold=100)
        async_gets = list(self.__prepare_devices_requests(devices_ids))
        for device_raw, data_type_results in zip(devices_raw,
                                                 blockify(self._async_get(async_gets),
                                                          len(DATA_TYPES))):
            device_raw = self.preapre_device_raw(device_raw, data_type_results)
            yielded_devices_count.add()
            yielded_devices_count.print_if_needed()
            yield device_raw
