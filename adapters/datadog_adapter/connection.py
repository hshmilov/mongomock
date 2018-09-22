import logging

from axonius.clients.rest.connection import RESTConnection
from datadog_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class DatadogConnection(RESTConnection):
    def __init__(self, *args, appkey: str = '', **kwargs):
        """ Initializes a connection to datadog using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for datadog
        """
        self._appkey = appkey
        super().__init__(url_base_prefix='api/v1', *args, **kwargs)
        self._permanent_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    def _connect(self):
        """ Connects to the service """
        self._get('hosts', url_params={'api_key': self._apikey,
                                       'application_key': self._appkey})

    def get_device_list(self):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses datadog's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        total_active = self._get('hosts/totals', url_params={'api_key': self._apikey,
                                                             'application_key': self._appkey})['total_active']
        start = 0
        while start < total_active and start < consts.MAX_DEVICES:
            try:
                yield from self._get('hosts', url_params={'api_key': self._apikey,
                                                          'application_key': self._appkey,
                                                          'start': start,
                                                          'count': consts.DEVICE_PER_PAGE})['host_list']
            except Exception:
                logger.exception(f'Problem getting offset {start}')
            start += consts.DEVICE_PER_PAGE
