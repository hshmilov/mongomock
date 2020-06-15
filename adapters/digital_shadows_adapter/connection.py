import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from digital_shadows_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES, OBJECT_NAMES

logger = logging.getLogger(f'axonius.{__name__}')


class DigitalShadowsConnection(RESTConnection):
    """ rest client for DigitalShadows adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _find_object_data(self, obj_name):
        offset = 0
        body_params = {'pagination': {'size': DEVICE_PER_PAGE, 'offset': offset}}
        response = self._post(f'{obj_name}/find', body_params=body_params, do_basic_auth=True)
        yield from response['content']
        total = response['total']
        offset = DEVICE_PER_PAGE
        while offset < min(MAX_NUMBER_OF_DEVICES, total):
            try:
                body_params = {'pagination': {'size': DEVICE_PER_PAGE, 'offset': offset}}
                response = self._post(f'{obj_name}/find', body_params=body_params, do_basic_auth=True)
                yield from response['content']
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem with offset {offset}')
                break

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No API Key or Secret')
        offset = 0
        body_params = {'pagination': {'size': DEVICE_PER_PAGE, 'offset': offset}}
        self._post(f'ip-ports/find', body_params=body_params, do_basic_auth=True)

    def get_device_list(self):
        ips_dict = dict()
        for obj_name in OBJECT_NAMES:
            try:
                for obj_data in self._find_object_data(obj_name):
                    if not isinstance(obj_data, dict) or not obj_data.get('ipAddress'):
                        continue
                    if not ips_dict.get(obj_data['ipAddress']):
                        ips_dict[obj_data['ipAddress']] = []
                    ips_dict[obj_data['ipAddress']].append((obj_name, obj_data))
            except Exception:
                logger.exception(f'Problem with objects name {obj_name}')
        for ip, data in ips_dict.items():
            yield ip, data
