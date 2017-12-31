"""puppetplugin.py: Implementation of the Puppet Adapter."""
# TODO ofir: Change the return values protocol

__author__ = "Ofri Shur"

from axonius.adapter_base import AdapterBase
from axonius.parsing_utils import figure_out_os
from axonius.adapter_exceptions import ClientConnectionException
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

    def _get_client_id(self, client_config):
        return client_config["puppet_server_name"]

    def _connect_client(self, client_config):
        try:
            return PuppetServerConnection(
                self.logger,
                client_config['puppet_server_name'],
                client_config['user_name'],
                client_config['password'])
        except exceptions.PuppetException as e:
            message = "Error getting information from puppet server {0}. reason: {1}".format(
                client_config["puppet_server_name"],
                str(e))
        except KeyError as e:
            if "puppet_server_name" in client_config:
                message = "Key error for Puppet {0}. details: {1}".format(
                    client_config["puppet_server_name"],
                    str(e))
            else:
                message = "Missing Puppet name for configuration line"
        self.logger.error(message)
        raise ClientConnectionException

    def _clients_schema(self):
        """
        The keys PuppetAdapter expects from configs.abs

        :return: list of tuples, First is the name of the variable, second is the type. 
                 For example [("puppet_server_name", "str"), ("password", "str")]
        """
        return {
            "properties": {
                "password": {
                    "type": "password"
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
