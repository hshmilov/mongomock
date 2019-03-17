import logging

from axonius.clients.rest.connection import RESTConnection
from carbonblack_protection_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class CarbonblackProtectionConnection(RESTConnection):
    def __init__(self, *args, devices_per_page, **kwargs):
        super().__init__(*args, url_base_prefix='api/bit9platform/v1/', **kwargs)
        self._permanent_headers = {'Content-Type': 'application/json',
                                   'Accept': 'application/json',
                                   'X-Auth-Token': self._apikey}
        self.__devices_per_page = devices_per_page

    def _connect(self):
        self._get('computer', url_params={'offset': 0, 'limit': 1})

    # pylint: disable=W0221
    def get_device_list(self, devices_per_page=None):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses CarbonblackProtection's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        # I keep the default value from init, and allowing to change it during different runs
        if devices_per_page:
            self.__devices_per_page = devices_per_page
        offset = 0
        raw_count = self._get('computer', url_params={'limit': -1})
        total_count = raw_count['count']
        logger.info(f'CarbonBlack protection API Returned a count of {total_count} devices')
        if total_count < 0:
            # Negetive total_count means the server can't evaluate the amout of devices.
            #  In such case we will query for a list 50,000 more device. The
            logger.info(f'Got negetive devices count {total_count}')
            total_count *= -1
            total_count += consts.MORE_DEVICE_IN_NEG_CASE

        while offset <= min(total_count, consts.MAX_DEVICES_COUNT):
            try:
                yield from self._get('computer', url_params={'limit': str(self.__devices_per_page),
                                                             'offset': str(offset)})
            except Exception:
                logger.exception(f'Problem getting device in offset: {offset}')
            offset += self.__devices_per_page
