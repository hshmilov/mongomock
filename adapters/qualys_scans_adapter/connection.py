import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from qualys_scans_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')
'''
In this connection we target the VM module (and probably PC later on).
These modules have a rate limit - by default of 2 connections through api v2.0 or 300 api requests an hour.
For the sake of the user - if the next api request is allowed within the next 30 seconds we wait and try again.
'''


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


class QualysScansConnection(RESTConnection):

    def __init__(self, request_timeout, chunk_size, devices_per_page, *args, date_filter=None, **kwargs):
        """ Initializes a connection to Illusive using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for Illusive
        """
        super().__init__(*args, session_timeout=(5, request_timeout), **kwargs)
        self._permanent_headers = {'X-Requested-With': 'Axonius Qualys Scans Adapter',
                                   'Accept': 'application/json'}
        self._date_filter = date_filter
        self._chunk_size = chunk_size
        self._devices_per_page = devices_per_page

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._get_device_count()

    def _prepare_get_hostassets_request_params(self, start_offset):
        params = {
            'ServiceRequest': {
                'preferences': {
                    'startFromOffset': start_offset,
                    'limitResults': self._devices_per_page
                },
            }
        }
        if self._date_filter:
            # filter by 'last_seen' greater then
            params['ServiceRequest']['filters'] = {
                'Criteria': [{
                    'field': 'lastVulnScan',
                    'operator': 'GREATER',
                    'value': self._date_filter,
                }],
            }
        return {'name': 'qps/rest/2.0/search/am/hostasset/',
                'body_params': params,
                'do_basic_auth': True}

    def _get_device_count(self):
        params = {
            'ServiceRequest': {
            }
        }
        if self._date_filter:
            # filter by 'last_seen' greater then
            params['ServiceRequest']['filters'] = {
                'Criteria': [{
                    'field': 'lastVulnScan',
                    'operator': 'GREATER',
                    'value': self._date_filter,
                }],
            }
        exception_count = 0
        while True:
            try:
                result = self._post('qps/rest/2.0/count/am/hostasset', body_params=params, do_basic_auth=True)
                if not (result.get('ServiceResponse') or {}).get('count'):
                    raise RuntimeError(f'Response is {result}')
                break
            except Exception as e:
                logger.warning(f'Exception {exception_count} while fetching count error :{e}')
                exception_count += 1
                if exception_count >= consts.FETCH_EXCEPTION_THRESHOLD:
                    raise

        return result['ServiceResponse']['count']

    def _get_hostassets_by_requests(self, requests):
        for request_id, response in enumerate(self._async_post(requests, chunks=self._chunk_size)):
            try:
                if isinstance(response, Exception):
                    logger.error(f'{request_id} - Got Exception: {response}')
                    continue

                service_response = response.get('ServiceResponse') or {}
                data = service_response.get('data')
                if not data:
                    logger.error(f'{request_id} - no data. Response is {service_response}')
                    continue

                yield (request_id, data)
                self._yielded_devices_count.add(len(data))
                self._yielded_devices_count.print_if_needed()
            except Exception:
                logger.exception(f'{request_id} - Failed to deliver: {response}')

    def _get_hostassets(self):
        logger.info('Starting to fetch')
        count = self._get_device_count()
        self._yielded_devices_count = IteratorCounter(f'Got {{count}} devices so far out of {count}', threshold=100)
        logger.info(f'device count is {count}')

        offsets = range(1, count + 1, self._devices_per_page)
        requests = [self._prepare_get_hostassets_request_params(offset) for offset in offsets]

        # we try to fetch each page max exception threshold.
        # if we got data back we remove it from the next round
        # if we got all responses back we stop

        for i in range(1, consts.FETCH_EXCEPTION_THRESHOLD + 1):
            logger.info(f'Aync round number {i}, sending {len(requests)} requests')
            success_indices = []
            for index, devices in self._get_hostassets_by_requests(requests):
                yield from devices
                success_indices.append(index)

            requests = [request for i, request in enumerate(requests) if i not in success_indices]
            if not requests:
                break
        else:
            logger.error(f'Lost {len(requests) * self._devices_per_page} devices')

    def get_device_list(self):
        try:
            for device_raw in self._get_hostassets():
                yield device_raw
        except Exception:
            logger.exception(f'Problem getting hostassets')
