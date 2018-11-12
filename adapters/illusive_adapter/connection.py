import time
import logging

from axonius.clients.rest.connection import RESTConnection
from illusive_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class IllusiveConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        """ Initializes a connection to Illusive using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for Illusive
        """
        super().__init__(url_base_prefix='api/v1', *args, **kwargs)
        self._permanent_headers = {'Authorization': self._apikey}

    def _connect(self):
        """ Connects to the service """
        self._get('monitoring/hosts', url_params={'limit': consts.DEVICE_PER_PAGE, 'offset': 0})

    def get_device_list(self):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses Illusive's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        response = self._get('monitoring/hosts', url_params={'limit': consts.DEVICE_PER_PAGE, 'offset': 0})
        yield from response['content']
        total_count = response['totalQueryResults']
        offset = consts.DEVICE_PER_PAGE
        sleep_count = 0
        while offset <= min(total_count, consts.MAX_DEVICES_COUNT) and sleep_count < 4:
            try:
                yield from self._get('monitoring/hosts',
                                     url_params={'limit': consts.DEVICE_PER_PAGE,
                                                 'offset': offset})['content']
                offset += consts.DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem at offset {offset}')
                sleep_count += 1
                time.sleep(15 * 60)
