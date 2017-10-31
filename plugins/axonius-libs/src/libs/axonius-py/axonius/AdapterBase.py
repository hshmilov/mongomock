"""
AdapterBase is an abstract class all adapters should inherit from.
It implements API calls that are expected to be present in all adapters.
"""

__author__ = "Mark Segal"

from axonius.PluginBase import PluginBase, add_rule
from abc import ABC, abstractmethod
from flask import jsonify


class AdapterBase(PluginBase, ABC):
    """
    Base abstract class for all adapters
    Terminology:
        "Adapter Source" - The source for data for this plugin. For example, a Domain Controller or AWS
        "Available Device" - A device that the adapter source knows and reports its existence.
                             Doesn't necessary means that the device is turned on or connected.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_clients_schema_in_db(self._clients_schema()) # TODO: implement this

        self._clients = self._get_parsed_clients_config()

    def _get_parsed_clients_config(self):
        clients_config = self._get_clients_config()

        # self._clients might be replaced at any moment when POST /clients is received
        # so it must be used cautiously
        return self._parse_clients_data(clients_config)

    @add_rule('devices', methods=['GET'])
    def devices(self):
        """ /devices Query adapter to fetch all available devices.
        An "available" device is a device that is registered with the adapter source.

        Accepts:
           GET - Finds all available devices, and returns them
        """
        return jsonify(self._query_devices())

    @add_rule('clients', methods=['GET', 'POST'])
    def clients(self):
        """ /clients Returns all available clients, e.g. all DC servers.

        Accepts:
           GET  - Returns all available clients
           POST - Triggers a refresh on all available clients from the DB and returns them
        """
        if self.get_method() == 'POST':
            self._clients = self._get_parsed_clients_config()

        return jsonify(self._clients.keys())

    @abstractmethod
    def _parse_clients_data(self, clients_config):
        """Abstract method for retreiving clients data as dictionary from the raw clients data (fetched from config)

        :param dict clients_config: The clients config as received from the configuration db

        :return dict: Each key of the dict is the client name, and the data is whatever the 
                      Adapter use in order to connect to the client.
        """
        pass

    @abstractmethod
    def _query_devices_by_client(self, client_name, client_data):
        """
        To be implemented by inheritors.
        Returns all devices from a specific client.
        Refer to devices(client) docs for the return type.

        :param client_name: str # valid values are from self._get_clients
        :param client_data: The data of the client, as returned from the _parse_clients_data function
        :return: adapter dependant
        """
        pass

    def _query_devices(self):
        """
        Synchronously returns all available devices from all clients.

        :return: iterator([client_name, devices])
        """
        # Running query on each device
        for client_name, client in self._clients.items():
            raw_devices = self._query_devices_by_client(client_name, client)
            parsed_devices = self._parse_raw_data(raw_devices)
            devices_list = {'raw': raw_devices,
                            'parsed': parsed_devices}

            yield [client_name, devices_list]

    @abstractmethod
    def _clients_schema(self):
        """
        To be implemented by inheritors
        Represents the set of keys the plugin expects from clients config

        :return: JSON Schema to, check out https://jsonschema.net/#/editor
        """
        pass

    @abstractmethod
    def _parse_raw_data(self, raw_data):
        """
        To be implemented by inheritors
        Will convert 'raw data' of one device (as the inheritor pleases to refer to it) to 'parsed' 
        Data that has to adhere to certain restrictions, namely to have (at least) the following schema:
        {
          "properties": {
            "name": {
              "type": "string"
            },
            "os": {
              "type": "string"
            },
            "id": {
              "type": "string"
            }
          },
          "required": [
            "name",
            "os",
            "id"
          ],
          "type": "object"
        }

        :param raw_data: raw data as received by /devices/client, i.e. without the client->data association
        :return: parsed data
        """
        pass

    def _get_clients_config(self):
        """Returning the data inside 'clients' Collection on <unique_plugin_name> db.
        """
        return self._get_db_connection(True)[self.unique_plugin_name]['clients'].find()

    def _update_clients_schema_in_db(self, schema):
        """
        Every adapter has to update the DB about the scheme it expects for its clients.
        This logic is ran when the adapter starts
        :return:
        """
        with self._get_db_connection(True) as db_connection:
            collection = db_connection[self.unique_plugin_name]['adapter_schema']
            collection.replace_one(filter={'adapter_name': self.unique_plugin_name,
                                           'adapter_version': self.version},
                                   replacement={
                                       'adapter_name': self.unique_plugin_name,
                                       'adapter_version': self.version,
                                       'schema': schema
                                   }, upsert=True)

    @property
    def plugin_type(self):
        return "Adapter"
