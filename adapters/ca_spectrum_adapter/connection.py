import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.xml.connection import parse_xml_from_string
from ca_spectrum_adapter.consts import THROTTLESIZE_MIN

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
        xml_response = parse_xml_from_string(
            self._get('devices?'
                      'attr=0x1006e&attr=0x12d7f&attr=0x10032&attr=0x110df&attr=0x23000e&'
                      'attr=0x23000c&attr=0x23000d&attr=0x1102a&attr=0x10030&attr=0x10052&'
                      f'throttlesize={THROTTLESIZE_MIN}',
                      do_basic_auth=True,
                      use_json_in_response=False))
        if 'model-response-list' not in xml_response.tag or 'model-responses' not in xml_response[0].tag:
            raise RESTException('Bad XML Response')
        total_models = int(xml_response.attrib.get('total-models'))
        logger.info(f'Total models {total_models}')

    def get_device_list(self):
        xml_response = parse_xml_from_string(
            self._get('devices?'
                      'attr=0x1006e&attr=0x12d7f&attr=0x10032&attr=0x110df&attr=0x23000e&'
                      'attr=0x23000c&attr=0x23000d&attr=0x1102a&attr=0x10030&attr=0x10052&'
                      f'throttlesize={THROTTLESIZE_MIN}',
                      do_basic_auth=True,
                      use_json_in_response=False))
        if 'model-response-list' not in xml_response.tag or 'model-responses' not in xml_response[0].tag:
            raise RESTException('Bad XML Response')
        total_models = int(xml_response.attrib.get('total-models'))
        logger.info(f'Total models {total_models}')
        xml_response = parse_xml_from_string(
            self._get('devices?'
                      'attr=0x1006e&attr=0x12d7f&attr=0x10032&attr=0x110df&attr=0x23000e&'
                      'attr=0x23000c&attr=0x23000d&attr=0x1102a&attr=0x10030&attr=0x10052&'
                      f'throttlesize={total_models}',
                      do_basic_auth=True,
                      use_json_in_response=False))
        yield from xml_response[0]
