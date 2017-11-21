"""puppetplugin.py: Implementation of the Puppet Adapter."""
# TODO ofir: Change the return values protocol

__author__ = "Ofri Shur"

from axonius.AdapterBase import AdapterBase
from axonius.ParsingUtils import figure_out_os
import exceptions
from puppetserverconnection import PuppetServerConnection


class PuppetAdapter(AdapterBase):
    """ A class containing all the Puppet Servers capabilities.

    Check AdapterBase documentation for additional params and exception details.

    """

    # Functions
    def __init__(self, **kargs):
        """Class initialization.

        Check AdapterBase documentation for additional params and exception details.
        """

        # Initialize the base plugin (will initialize http server)
        super().__init__(**kargs)

    def _parse_clients_data(self, clients_config):

        clients_dict = dict()
        for puppet_details in clients_config:
            try:
                clients_dict[puppet_details["puppet_server_name"]] = PuppetServerConnection(
                    self.logger,
                    puppet_details['puppet_server_name'],
                    puppet_details['user_name'],
                    puppet_details['password'])
            except exceptions.PuppetException as e:
                self.logger.error("Error getting information from puppet server {0}. reason: {1}".format(
                    puppet_details["puppet_server_name"],
                    str(e)))
            except KeyError as e:
                if "puppet_server_name" in puppet_details:
                    self.logger.error("Key error for Puppet {0}. details: {1}".format(
                        puppet_details["puppet_server_name"],
                        str(e)))
                else:
                    self.logger.error(
                        "Missing Puppet name for configuration line")

        return clients_dict

    def _clients_schema(self):
        """
        The keys PuppetAdapter expects from configs.abs

        :return: list of tuples, First is the name of the variable, second is the type. 
                 For example [("puppet_server_name", "str"), ("password", "str")]
        """
        return {
            "properties": {
                "password": {
                    "type": "string"
                },
                "user_name": {
                    "type": "string"
                },
                "puppet_server_name": {
                    "type": "string"
                }
            },
            "required": [
                "puppet_server_name",
                "user_name",
                "password"
            ],
            "type": "object"
        }

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Puppet Server

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a puppet server connection

        :return: A json with all the attributes returned from the Puppet Server
        """
        try:
            return client_data.get_device_list()
        except exceptions.PuppetException as e:
            self.logger.error(
                "Error while trying to get devices. Details: {0}", str(e))
            return str(e), 500

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device_parsed = dict()
            device_parsed['name'] = device_raw['hostname']
            device_parsed['os'] = figure_out_os(device_raw["operatingsystem"] +
                                                ' ' + device_raw["architecture"] +
                                                ' ' + device_raw["kernel"])
            device_parsed['os']['major'] = device_raw["os"]['release']['major']
            if 'minor' in device_raw['os']['release']:
                device_parsed['os']['minor'] = device_raw["os"]['release']['minor']
            device_parsed['id'] = device_raw[u'certname']
            device_parsed['raw'] = device_raw
            yield device_parsed

    # Exported API functions - None for now
