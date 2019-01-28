import logging
import xml.etree.cElementTree as ET

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from paloalto_panorama_adapter.consts import GET_ALL_DEVICES_XML, FIREWALL_DEVICE_TYPE, ARP_TYPE, GET_ARP_XML

logger = logging.getLogger(f'axonius.{__name__}')


class PaloaltoPanoramaConnection(RESTConnection):
    """ rest client for PaloaltoPanorama adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api', headers={'Content-Type': 'application/xml',
                                                                'Accept': 'application/xml'}, **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        xml_token = ET.fromstring(self._get('', url_params={'type': 'keygen',
                                                            'user': self._username,
                                                            'password': self._password},
                                            use_json_in_response=False))
        if 'response' not in xml_token.tag:
            raise RESTException('Unknown XML format from server')
        if xml_token.attrib['status'] != 'success' or 'result' not in xml_token[0].tag \
                or 'key' not in xml_token[0][0].tag:
            error_msg = xml_token.attrib['status']
            raise RESTException(f'Connection Failed: {error_msg}')
        self._apikey = xml_token[0][0].text

    def get_device_list(self):
        xml_response = ET.fromstring(self._get('', use_json_in_response=False,
                                               url_params={'key': self._apikey,
                                                           'type': 'op',
                                                           'cmd': GET_ALL_DEVICES_XML}))
        if 'response' not in xml_response.tag or xml_response.attrib['status'] != 'success' or 'result' \
                not in xml_response[0].tag or 'devices' not in xml_response[0][0].tag:
            error_msg = xml_response.attrib['status']
            raise RESTException(f'Got bad request response {error_msg}')
        devices_xml = xml_response[0][0]
        for device_entry_xml in devices_xml:
            yield device_entry_xml, FIREWALL_DEVICE_TYPE

        xml_response = ET.fromstring(self._get('', use_json_in_response=False,
                                               url_params={'key': self._apikey,
                                                           'type': 'op',
                                                           'cmd': GET_ARP_XML}))
        if 'response' not in xml_response.tag or xml_response.attrib['status'] != 'success' or 'result' \
                not in xml_response[0].tag:
            error_msg = xml_response.attrib['status']
            raise RESTException(f'Got bad request response {error_msg}')
        xml_arp_entries = []
        for xml_entity in xml_response[0]:
            if 'entries' in xml_entity.tag:
                xml_arp_entries = xml_entity
        for arp_xml_entry in xml_arp_entries:
            yield arp_xml_entry, ARP_TYPE
