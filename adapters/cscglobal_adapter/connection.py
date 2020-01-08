import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException, RESTConnectionError

logger = logging.getLogger(f'axonius.{__name__}')


class CscglobalConnection(RESTConnection):
    """ rest client for Cscglobal adapter """

    def __init__(self, *args,
                 bearer: str = None,
                 apikey: str = None,
                 zone_name: str = None,
                 **kwargs):
        super().__init__(*args, url_base_prefix='/dbs/api/v2',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._apikey = apikey
        self._bearer = bearer
        self._zone_name = zone_name

    def _connect(self):
        # if not self._username or not self._password:
        #     raise RESTException('No username or password')
        if not self._apikey or not self._bearer:
            raise RESTException('No APIKey or Bearer token.')
        if not self._zone_name:
            raise RESTException('Missing Zone Name.')
        self._session_headers['Authorization'] = f'Bearer {self._bearer}'
        self._session_headers['apikey'] = self._apikey
        try:
            self._get(f'zones/{self._zone_name}')
        except RESTException as e:
            message = f'Failed to fetch zone information for Zone {self._zone_name}. The error was: {str(e)}'
            raise RESTConnectionError(message)

    @staticmethod
    def _build_zone_dict(response):
        return {
            'zoneName': response.get('zoneName') or '',
            'hostingType': response.get('hostingType') or '',
            'cname': response.get('cname') or [],
            'txt': response.get('txt') or [],
            'mx': response.get('mx') or [],
            'ns': response.get('ns') or [],
            'srv': response.get('srv') or [],
            'soa': response.get('soa') or {}
        }

    def get_device_list(self):
        try:
            response = self._get(f'zones/{self._zone_name}')
        except RESTException as e:
            message = f'Failed to fetch zone information for Zone {self._zone_name}. The error was: {str(e)}'
            logger.exception(message)
            return
        zone_dict = self._build_zone_dict(response)
        for a_rec in response.get('a'):
            if not isinstance(a_rec, dict):
                message = f'Error fetching A record for zone {self._zone_name}. Expected dict, got {a_rec} instead.'
                logger.error(message)
                continue
            yield {'a': a_rec, 'zone_info': zone_dict}
        for aaaa_rec in response.get('aaaa'):
            if not isinstance(aaaa_rec, dict):
                message = f'Error fetching A record for zone {self._zone_name}. Expected dict, got {aaaa_rec} instead.'
                logger.error(message)
                continue
            yield {'aaaa': aaaa_rec, 'zone_info': zone_dict}
