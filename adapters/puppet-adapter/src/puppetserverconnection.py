"""puppetserverconnection.py: Logic for connecting to a Puppet Server."""

import requests
import exceptions
import puppetconfig as config
import tempfile


def create_temp_file(data: bytes):
    """
    Creates a temporary file with some data, that can be read from
    :param data: data to write
    :return:
    """
    file = tempfile.NamedTemporaryFile()
    file.write(data)
    file.flush()
    return file


def _parse_json_request(response):
    """ This function check the response of the query and parse the normal respond to a json.
        :raises a PuppetException if a problems occurs in the response from the server.
    """
    if response.ok:
        return response.json()
    else:
        raise exceptions.PuppetException(f"Query failed: {response.status_code}")


class PuppetServerConnection:

    def __init__(self, logger, puppet_server_address: str, ca_file_data: bytes, cert_file: bytes, private_key: bytes):
        """
        :param obj logger: Logger object of the system
        :param str puppet_server_address: Server address
        """
        self.puppet_server_address = puppet_server_address
        self.logger = logger

        self.__ca_file = create_temp_file(ca_file_data)
        self.__cert_file = create_temp_file(cert_file)
        self.__private_key_file = create_temp_file(private_key)

        self._session = requests.Session()
        self._session.cert = (self.__cert_file.name,
                              self.__private_key_file.name)
        self._session.verify = self.__ca_file.name

        self.__base_puppet_url = f"{config.PUPPET_CONNECTION_METHOD}{self.puppet_server_address}" + \
                                 config.PUPPET_PORT_STRING

    def get_device_list(self):
        """ This function returns a json with all the data about all the devices in the server.
             :raises a PuppetException if a problems occurs in the response from the server or if ssh problems.
        """
        try:
            query_response = self._session.get(f"{self.__base_puppet_url}{config.PUPPET_API_PREFIX}/nodes")
        except requests.RequestException as err:
            self.logger.exception("Error in querying the nodes from the puppet server." +
                                  " Error information:{0}".format(str(err)))
            raise

        parsed_query_nodes_json = _parse_json_request(query_response)
        devices_count = 0
        num_of_devices = len(parsed_query_nodes_json)
        for json_node in parsed_query_nodes_json:
            try:
                devices_count += 1
                if devices_count % 1000 == 0:
                    self.logger.info(f"Got {devices_count} devices out of {num_of_devices}")
                yield self._query_fact_device(json_node)
            except exceptions.PuppetException as err:
                self.logger.exception(f"Error in getting information about node:{str(json_node)}. Error:{str(err)}")

    def _query_fact_device(self, basic_json_node=None):
        """ This function gets a json with basic information about a node (or nothing if not needed),
            and query all the facts about the node and returns it as a json.
            :param dict basic_json_node A dictionary with basic puppet information about the device
            :raises a PuppetException if a problems occurs in the response from the server or if ssh problems.
            :return device: a dict with all the facts on this device
        """
        device = dict(basic_json_node or {})

        try:
            url = f"{self.__base_puppet_url }{config.PUPPET_API_PREFIX}/nodes/{basic_json_node[u'certname']}/facts"
            query_response = self._session.get(url)
        except requests.RequestException as err:
            raise exceptions.PuppetException(str(err))

        parsed_query_facts = _parse_json_request(query_response)
        device.update({x['name']: x['value'] for x in parsed_query_facts})
        return device
