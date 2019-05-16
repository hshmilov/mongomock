import base64
import logging
import xml.etree.ElementTree as ET

from axonius.clients.rest.connection import RESTConnection, RESTException
from tanium_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class TaniumConnection(RESTConnection):

    def __init__(self, *args, **kwargs):
        super().__init__(url_base_prefix='/', *args, **kwargs)
        self._permanent_headers = {'Content-Type': 'text/xml; charset=utf-8', 'Accept': '*/*'}

    def _connect(self):
        if self._username is not None and self._password is not None:
            connection_dict = {'username': base64.b64encode(self._username.encode('utf-8')).decode('utf-8'),
                               'password': base64.b64encode(self._password.encode('utf-8')).decode('utf-8')}
            self._session_headers = connection_dict
            self._session_token = self._post('auth', body_params=connection_dict, use_json_in_response=False)
            self._session_headers = {'session': self._session_token}
            xml_str = self._post('soap', use_json_in_response=False, use_json_in_body=False,
                                 body_params=consts.GET_DEVICES_BODY_PARAMS)
            if '403 Forbidden' in xml_str:
                raise RESTException('Insufficient privilege to get devices')
        else:
            raise RESTException('No user name or password')

    def get_device_list(self):
        xml = ET.fromstring(self._post('soap', use_json_in_response=False, use_json_in_body=False,
                                       body_params=consts.GET_DEVICES_BODY_PARAMS))
        if not xml.tag.endswith('Envelope'):
            raise RESTException(f'Bad xml first tag is {xml.tag}')
        xml_second_block = xml[0]
        if not xml_second_block.tag.endswith('Body'):
            raise RESTException(f'Bad xml second tag is {xml_second_block.tag}')
        xml_third_block = xml_second_block[0]
        if not xml_third_block.tag.endswith('return'):
            raise RESTException(f'Bad xml third tag is {xml_third_block.tag}')
        clients_xml = []
        for inner_xml in xml_third_block:
            if inner_xml.tag == 'result_object':
                try:
                    if not inner_xml[0].tag == 'system_status':
                        raise RESTException(f'Bad xml forth tag is {inner_xml[0].tag}')
                    clients_xml = inner_xml[0]
                    break
                except Exception:
                    pass
        for client_xml in clients_xml:
            try:
                if client_xml.tag == 'client_status':
                    device_raw = dict()
                    for property_xml in client_xml:
                        device_raw[property_xml.tag] = property_xml.text
                    yield device_raw
            except Exception:
                logger.exception(f'Problem getting xml in Tanium')
