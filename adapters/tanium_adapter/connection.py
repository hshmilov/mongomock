import base64
import logging
import xml.etree.ElementTree as ET

from axonius.clients.rest.connection import RESTConnection, RESTException
from tanium_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class TaniumConnection(RESTConnection):

    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         url_base_prefix='/',
                         headers={'Content-Type': 'text/xml; charset=utf-8', 'Accept': '*/*'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No user name or password')
        connection_dict = {'username': base64.b64encode(self._username.encode('utf-8')).decode('utf-8'),
                           'password': base64.b64encode(self._password.encode('utf-8')).decode('utf-8')}
        self._session_headers = connection_dict
        self._session_token = self._post('auth', body_params=connection_dict, use_json_in_response=False)
        self._session_headers = {'session': self._session_token}
        xml_str = self._post('soap', use_json_in_response=False, use_json_in_body=False,
                             body_params=consts.GET_DEVICES_BODY_PARAMS)
        if '403 Forbidden' in str(xml_str):
            raise RESTException('Insufficient privilege to get devices')

    def get_device_list_paginated(self):
        total = 0
        offset = 0
        for data_type, data in self.get_device_list_paginated_by_offset(offset=offset):
            if data_type == 'device':
                yield data
            elif data_type == 'total':
                total = int(data)
        offset += consts.DEVICE_PER_PAGE
        while offset < total:
            try:
                for data_type, data in self.get_device_list_paginated_by_offset(offset=offset):
                    if data_type == 'device':
                        yield data
                offset += consts.DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem with offset {offset}')
                break

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def get_device_list_paginated_by_offset(self, offset):
        body_params = consts.GET_DEVICES_BODY_PARAMS_PAGINTAED.format(offset,
                                                                      consts.DEVICE_PER_PAGE,
                                                                      consts.CACHE_EXPIRATION)
        xml = ET.fromstring(self._post('soap', use_json_in_response=False, use_json_in_body=False,
                                       body_params=body_params))
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
                    yield 'device', device_raw
                elif client_xml.tag == 'cache_info':
                    for property_xml in client_xml:
                        if property_xml.tag == 'cache_row_count':
                            total_count = property_xml.text
                            yield 'total', total_count
            except Exception:
                logger.exception(f'Problem getting xml in Tanium')

    # pylint: disable=arguments-differ
    def get_device_list(self, do_pagination=False):
        if do_pagination:
            yield from self.get_device_list_paginated()
            return
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
