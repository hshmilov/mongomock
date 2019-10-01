import logging
import xml.etree.ElementTree as ET


from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from cisco_ucm_adapter.consts import AXL_POST_BODY

logger = logging.getLogger(f'axonius.{__name__}')


class CiscoUcmConnection(RESTConnection):
    """ rest client for CiscoUcm adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-type': 'text/xml',
                                  'SOAPAction': 'CUCM:DB ver=8.5 listPhone'
                                  },
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._post('axl/', use_json_in_body=False, do_basic_auth=True,
                   use_json_in_response=False, body_params=AXL_POST_BODY)

    def get_device_list(self):
        response = self._post('axl/', use_json_in_body=False,
                              do_basic_auth=True,
                              use_json_in_response=False,
                              body_params=AXL_POST_BODY)
        root = ET.fromstring(response)
        for phone in root.iter('phone'):
            test_name = phone.find('name').text
            logger.info(f'Got Phone {test_name}')
            break
