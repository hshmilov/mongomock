import logging
from time import sleep

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.limacharlie.consts import TOKEN_URL, MAX_NUMBER_OF_SLEEPS, TIME_TO_SLEEP

logger = logging.getLogger(f'axonius.{__name__}')


class LimacharlieConnection(RESTConnection):
    """ rest client for Limacharlie adapter """

    def __init__(self, *args, org_id, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._org_id = org_id

    def _connect(self):
        response = self._post(TOKEN_URL, body_params={'secret': self._apikey, 'oid': self._org_id})
        if not response.get('jwt'):
            raise RESTException(f'Bad Auth request')
        self._token = response['jwt']
        self._session_headers['Authorization'] = f'Bearer {self._token}'

    def get_device_list(self):
        sensors = self._get(f'v1/sensors/{self._org_id}')['sensors']
        if not isinstance(sensors, list):
            sensors = []
        for sensor in sensors:
            try:
                device_id = sensor['sid']
                yield self._get(f'v1/{device_id}')
            except Exception:
                logger.exception(f'Problem with sensor {sensor}')

    def update_isolate_status(self, sid, do_isolate):
        if do_isolate:
            self._post(f'v1/{sid}/isolation')
        else:
            self._delete(f'v1/{sid}/isolation')
        number_of_sleeps = 0
        while number_of_sleeps < MAX_NUMBER_OF_SLEEPS:
            response = self._get(f'v1/{sid}')
            if response.get('info') and response['info'].get('is_isolated') == do_isolate:
                return response
            number_of_sleeps += 1
            sleep(TIME_TO_SLEEP)
        if number_of_sleeps == MAX_NUMBER_OF_SLEEPS:
            raise RESTException(f'Cant isolate/unisolate device id {sid}')
