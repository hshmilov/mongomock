import logging
from time import sleep

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from carbonblack_response_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class CarbonblackResponseConnection(RESTConnection):
    def __init__(self, *args, inactive_filter_days: int = 0, **kwargs):
        super().__init__(*args, **kwargs)
        self.__inactive_filter_days = inactive_filter_days

    def _connect(self):
        if self._username and self._password:
            self._get('auth', do_digest_auth=True)
        elif self._apikey:
            self._permanent_headers['X-Auth-Token'] = self._apikey
        else:
            raise RESTException('No user name or password')

        url_params = {'inactive_filter_days': self.__inactive_filter_days} if self.__inactive_filter_days else None
        self._get('v1/sensor', url_params=url_params)

    # pylint: disable=arguments-differ
    def get_device_list(self, inactive_filter_days: int = 0):
        self.__inactive_filter_days = inactive_filter_days
        url_params = {'inactive_filter_days': self.__inactive_filter_days} if self.__inactive_filter_days else None
        yield from self._get('v1/sensor', url_params=url_params)

    def update_isolate_status(self, device_id, do_isolate):
        device_json = self._get(f'v1/sensor/{device_id}')
        device_json['is_isolating'] = do_isolate
        device_json['network_isolation_enabled'] = do_isolate
        self._put(f'v1/sensor/{device_id}', body_params=device_json, use_json_in_response=False)
        number_of_sleeps = 0
        while device_json.get('is_isolating') != do_isolate and number_of_sleeps < consts.MAX_NUMBER_OF_SLEEPS:
            number_of_sleeps += 1
            sleep(consts.TIME_TO_SLEEP)
            device_json = self._get(f'v1/sensor/{device_id}')
        if number_of_sleeps == consts.MAX_NUMBER_OF_SLEEPS:
            raise RESTException(f'Cant isolate device id {device_id} got json {device_json}')
        return device_json
