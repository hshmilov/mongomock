import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.xml.connection import parse_xml_from_string

logger = logging.getLogger(f'axonius.{__name__}')


class BigfixConnection(RESTConnection):

    def _connect(self):

        if not self._username or not self._password:
            raise RESTException('No user name or password')
        self._get('computers', do_basic_auth=True, use_json_in_response=False)

    # pylint: disable=too-many-nested-blocks
    def get_query_data_per_device_list(self, query_object):
        xml_response = parse_xml_from_string(
            self._post(
                'query',
                body_params='relevance=(id of computer of it, values of it) of results of bes properties whose '
                            f'(name of it contains "{query_object}")',
                use_json_in_body=False,
                use_json_in_response=False)
        )
        computer_id_to_query_object = dict()
        for root_data_node in xml_response:
            if root_data_node.tag == 'Query':
                for query_data_node in root_data_node:
                    if query_data_node.tag == 'Result':
                        for result_data_node in query_data_node:
                            if result_data_node.tag == 'Tuple':
                                try:
                                    computer_id = str(result_data_node[0].text)
                                    query_object_data = result_data_node[1].text
                                    if not computer_id or not query_object_data:
                                        continue
                                    if computer_id not in computer_id_to_query_object:
                                        computer_id_to_query_object[computer_id] = []
                                    computer_id_to_query_object[computer_id].append(query_object_data)
                                except Exception:
                                    logger.exception(f'Exception while parsing query object {query_object}')

        return computer_id_to_query_object

    def get_device_list(self):
        xml_computers = parse_xml_from_string(self._get('computers', use_json_in_response=False))
        async_requests = []

        for computer_node in xml_computers:
            if computer_node.tag == 'Computer':
                computer_resource = computer_node.attrib.get('Resource')
                if computer_resource:
                    # This is not by the protocol. Instead of authing once we are making a do_basic_auth each
                    # time again and again. who said its gonna work on all bigfix versions?
                    async_requests.append(
                        {
                            'name': computer_resource,
                            'force_full_url': True,
                            'do_basic_auth': True,
                            'use_json_in_response': False
                        }
                    )

        yield from self._async_get_only_good_response(async_requests)
