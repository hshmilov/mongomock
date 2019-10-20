import logging
import xml.etree.ElementTree as ET

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from ca_spectrum_adapter.consts import THROTTLESIZE_MAX, THROTTLESIZE_MIN

logger = logging.getLogger(f'axonius.{__name__}')


class CaSpectrumConnection(RESTConnection):
    """ rest client for CaSpectrum adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='spectrum/restful',
                         headers={},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._get('devices?'
                  'attr=0x1006e&attr=0x12d7f&attr=0x10032&attr=0x110df&attr=0x23000e&'
                  'attr=0x23000c&attr=0x23000d&attr=0x1102a&attr=0x10030&attr=0x10052&'
                  f'throttlesize={THROTTLESIZE_MIN}',
                  do_basic_auth=True,
                  use_json_in_response=False)

    def get_device_list(self):
        xml_response = ET.fromstring(self._get('devices?'
                                               'attr=0x1006e&attr=0x12d7f&attr=0x10032&attr=0x110df&attr=0x23000e&'
                                               'attr=0x23000c&attr=0x23000d&attr=0x1102a&attr=0x10030&attr=0x10052&'
                                               f'throttlesize={THROTTLESIZE_MAX}',
                                               do_basic_auth=True,
                                               use_json_in_response=False))
        if xml_response.tag != 'model-response-list' or xml_response[0].tag != 'model-responses':
            raise RESTException('Bad XML Response')
        yield from xml_response[0]
