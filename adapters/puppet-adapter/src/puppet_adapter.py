"""puppetplugin.py: Implementation of the Puppet Adapter."""
# TODO ofir: Change the return values protocol

__author__ = "Ofri Shur"

from axonius.device import Device, MAC_FIELD
from axonius.adapter_base import AdapterBase
from axonius.adapter_exceptions import ClientConnectionException
import exceptions
from puppetserverconnection import PuppetServerConnection


class PuppetAdapter(AdapterBase):
    """ A class containing all the Puppet Servers capabilities.

    Check AdapterBase documentation for additional params and exception details.

    """

    class MyDevice(Device):
        pass

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        self.logger.error("_parse_correlation_results is not implemented for puppet adapter")
        raise NotImplementedError("_parse_correlation_results is not implemented for puppet adapter")

    def _get_client_id(self, client_config):
        return client_config["puppet_server_name"]

    def _connect_client(self, client_config):
        try:
            return PuppetServerConnection(
                self.logger,
                client_config['puppet_server_name'],
                bytes(client_config['ca_file']),
                bytes(client_config['cert_file']),
                bytes(client_config['private_key']))
        except exceptions.PuppetException as e:
            message = "Error getting information from puppet server {0}. reason: {1}".format(
                client_config["puppet_server_name"],
                str(e))
            self.logger.exception(message)
        except KeyError as e:
            if "puppet_server_name" in client_config:
                message = f"Key error for Puppet {0}. details: {1}".format(client_config["puppet_server_name"], str(e))
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
                "puppet_server_name": {
                    "type": "string"
                },
                "ca_file": {
                    "type": "array",
                    "title": "The binary contents of the ca_file",
                    "description": "bytes",
                    "items": {
                        "type": "integer",
                        "default": 0,
                    }
                },
                "cert_file": {
                    "type": "array",
                    "title": "The binary contents of the cert_file",
                    "description": "bytes",
                    "items": {
                        "type": "integer",
                        "default": 0,
                    }
                },
                "private_key": {
                    "type": "array",
                    "title": "The binary contents of the private_key",
                    "description": "bytes",
                    "items": {
                        "type": "integer",
                        "default": 0,
                    }
                }
            },
            "required": [
                "puppet_server_name",
                "ca_file",
                "cert_file",
                "private_key"
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
        return list(client_data.get_device_list())

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._new_device()
            device.name = device_raw['hostname']
            device.figure_os(' '.join([device_raw["operatingsystem"],
                                       device_raw["architecture"],
                                       device_raw["kernel"]]))
            device.os.major = device_raw["os"]['release']['major']
            if 'minor' in device_raw['os']['release']:
                device.os.minor = device_raw["os"]['release']['minor']
            device.id = device_raw[u'certname']
            for inet in device_raw.get('networking', {}).get('interfaces', {}).values():
                device.add_nic(inet.get(MAC_FIELD, ''),
                               [x['address'] for x in inet.get('bindings', []) if x.get('address')] +
                               [x['address'] for x in inet.get('bindings6', []) if x.get('address')])
            device.set_raw(device_raw)
            yield device

    # Exported API functions - None for now
