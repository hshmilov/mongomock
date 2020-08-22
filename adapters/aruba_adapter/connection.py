import logging
import xml.etree.ElementTree as ET

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class ArubaConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._permanent_headers = {'Content-Type': 'application/xml', 'Accept': 'application/xml'}

    def _connect(self):
        destination = '/'
        next_action = ''
        params = {'credential_0': self._username,
                  'credential_1': self._password,
                  'login': 'Log In',
                  'destination': destination,
                  'next_action': next_action}
        self._post('LOGIN', url_params=params, use_json_in_response=False)

    def get_device_list(self):
        for byte in ['%.02X' % i for i in range(0x100)]:
            try:
                logger.info(f'Getting byte {byte}')
                yield from self.get_device_list_from_query_byte(byte)
            except Exception:
                logger.exception(f'Got exception at byte {byte} stopping')
                # Ofri: I think it is better to stop in the case of Aruba from the field experience
                break

    def get_device_list_from_query_byte(self, byte):
        xml_raw = self._get('client_search.xml',
                            url_params={'query': byte},
                            use_json_in_response=False)
        xml_obj = ET.fromstring(xml_raw)
        if 'amp_client_search' not in xml_obj.tag:
            raise RESTException(f'Bad xml with tag {xml_obj.tag}')
        for record in xml_obj:
            try:
                device_raw = {}
                for xml_property in record:
                    if xml_property.getchildren():
                        device_raw[xml_property.tag] = [child.text for child in xml_property.getchildren()
                                                        if child.tag == 'content']
                    else:
                        device_raw[xml_property.tag] = xml_property.text
                yield device_raw
            except Exception:
                logger.exception(f'Problem at record')


class ArubaOsCxConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='rest/v10.04',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        try:
            self._post('login',
                       url_params={'username': self._username, 'password': self._password},
                       use_json_in_response=False)
        except Exception as e:
            if 'session limit' in str(e):
                raise RESTException('Got to session limit')
            if '401' in str(e):
                raise RESTException('Bad Credentials')
            raise
        self._get('system/vlans')

    def get_device_list(self):
        try:
            self._post('login',
                       url_params={'username': self._username, 'password': self._password},
                       use_json_in_response=False)
        except Exception as e:
            if 'session limit' in str(e):
                raise RESTException('Got to session limit')
            if '401' in str(e):
                raise RESTException('Bad Credentials')
            raise
        vlans = list(self._get('system/vlans').keys())
        for vlan in vlans:
            try:
                macs_raw = self._get(f'system/vlans/{vlan}/macs?attributes=*')
                for mac_raw in macs_raw:
                    try:
                        yield self._get(f'system/vlans/{vlan}/macs/{mac_raw}')
                    except Exception:
                        logger.exception(f'Problem with mac {mac_raw}')
            except Exception:
                logger.exception(f'Problem with vlan {vlan}')
        self._post('logout', use_json_in_response=False)

    def close(self):
        try:
            self._post('logout', use_json_in_response=False)
        except Exception:
            pass
        self._session = None
