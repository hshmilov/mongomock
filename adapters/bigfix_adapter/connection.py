import xml.etree.ElementTree as ET
from axonius.clients.rest.exception import RESTException
from axonius.clients.rest.connection import RESTConnection


class BigfixConnection(RESTConnection):

    def _connect(self):

        if self._username is not None and self._password is not None:
            self._get("computers", do_basic_auth=True, use_json_in_response=False)
        else:
            raise RESTException("No user name or password")

    def get_device_list(self, **kwargs):
        xml_computers = ET.fromstring(self._get("computers", use_json_in_response=False))
        for computer_node in xml_computers:
            if computer_node.tag == 'Computer':
                computer_resource = computer_node.attrib.get('Resource')
                if computer_resource:
                    yield self._get(computer_resource, force_full_url=True, use_json_in_response=False)
