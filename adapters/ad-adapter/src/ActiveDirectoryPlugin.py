"""ActiveDirectoryPlugin.py: Implementation of the ActiveDirectory Adapter."""
# TODO ofir: Change the return values protocol

__author__ = "Ofir Yefet"

from axonius.AdapterBase import AdapterBase
from axonius.ParsingUtils import figure_out_os
from LdapConnection import LdapConnection

import exceptions

# Plugin Version (Should be updated with each new version)
AD_VERSION = '1.0.0'
PLUGIN_TYPE = 'ad_adapter'


class ActiveDirectoryPlugin(AdapterBase):
    """ A class containing all the Active Directory capabilities.

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
        # Each client inside _clients will hold an open LDAP connection object
        clients_dict = dict()
        for dc_details in clients_config:
            try:
                clients_dict[dc_details["dc_name"]] = LdapConnection(dc_details['dc_name'],
                                                                     dc_details['domain_name'],
                                                                     dc_details['query_user'], 
                                                                     dc_details['query_password'])
            except exceptions.LdapException as e:
                self.logger.error("Error in ldap process for dc {0}. reason: {1}".format(dc_details["dc_name"], str(e)))
            except KeyError as e:
                if "dc_name" in dc_details:
                    self.logger.error("Key error for dc {0}. details: {1}".format(dc_details["dc_name"], str(e)))
                else:
                    self.logger.error("Missing dc name for configuration line")
        return clients_dict

    def _clients_schema(self):
        """
        The keys AdAdapter expects from configs.abs

        :return: json schema
        """
        return {
            "properties": {
                "admin_password": {
                    "type": "string"
                },
                "admin_user": {
                    "type": "string"
                },
                "dc_name": {
                    "type": "string"
                },
                "domain_name": {
                    "type": "string"
                },
                "query_password": {
                    "type": "string"
                },
                "query_user": {
                    "type": "string"
                }
            },
            "required": [
                "dc_name",
                "query_user",
                "admin_user",
                "query_password",
                "domain_name",
                "admin_password"
            ],
            "type": "object"
        }

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Dc

        :param str client_name: The name of the client
        :param str client_data: The data of the client

        :return: iter(dict) with all the attributes returned from the DC per client
        """
        try:
            return client_data.get_device_list()
        except exceptions.LdapException as e:
            self.logger.error("Error while trying to get devices. Details: {0}", str(e))
            return str(e), 500

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            yield{
                'name': device_raw['name'],
                'os': figure_out_os(device_raw['operatingSystem']),
                'id': device_raw['distinguishedName'],
                'raw': device_raw}

    # Exported API functions - None for now
