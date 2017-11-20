"""
AdapterBase is an abstract class all adapters should inherit from.
It implements API calls that are expected to be present in all adapters.
"""

__author__ = "Mark Segal"

import concurrent.futures

from axonius.PluginBase import PluginBase, add_rule
from abc import ABC, abstractmethod
from flask import jsonify
import json
from base64 import standard_b64decode


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

        self._send_reset_to_ec()

        self._update_clients_schema_in_db(self._clients_schema())

        self._clients = self._get_parsed_clients_config()

        self._thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=50)

    def _send_reset_to_ec(self):
        """ Function for notifying the EC that this Adapted has been reset.
        """
        self.request_remote_plugin('action_update/adapter_action_reset?unique_name={0}'.format(self.plugin_unique_name),
                                   plugin_unique_name='execution',
                                   method='POST')

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

    def _update_action_data(self, action_id, status, output={}):
        """ A function for updating the EC on new action status.

        This function will initiate an POST request to the EC notifying on the new action status.

        :param str action_id: The action id of the related update
        :param str status: The new status of the action
        :param dict output: The output of the action (in case finished or error)
        """
        self.request_remote_plugin('action_update/{0}'.format(action_id),
                                   plugin_unique_name='execution',
                                   method='POST',
                                   data=json.dumps({"status": status, "output": output}))
        # TODO: Think of a better way to implement status

    def _run_action_thread(self, func, device_data, action_id, **kwargs):
        """ Function for running new action.

        This function should run as a new thread an handle the running of the wanted action.
        It will call the correct abstract action function implemented by the adapter and wait for it
        To finish. This function assumes that the adapter action function is blocking until the action
        Is finished.

        :param func func: A pointer to the action function (according to the action type requested)
        :param json device_data: The raw device data for running the action
        :param str action_id: The id of the current action
        :param **kwargs: Another parameters needed for this specific action (retrieved from the request body)
        """
        # Sending update that this action has started
        self._update_action_data(action_id, status="started")

        try:
            # Running the function, it should block until action is finished
            result = func(device_data, **kwargs)
        except Exception as e:
            self._update_action_data(action_id, status="failed", output={
                                     "result": "Failure", "product": str(e)})

        # Sending the result to the issuer
        self._update_action_data(action_id, status="finished", output=result)

    def _create_action_thread(self, device, func, action_id, **kargs):
        """ Function for creating action thread.
        """
        # Getting action id
        self._thread_pool.submit(
            self._run_action_thread, func, device, action_id, **kargs)

    @add_rule('action/<action_type>', methods=['POST'])
    def rest_new_action(self, action_type):
        # Getting action id from the URL
        action_id = self.get_url_param('action_id')
        request_data = self.get_request_data_as_object()
        device_data = request_data.pop('device_data')

        if action_type not in ['get_file', 'put_file', 'execute_binary', 'execute_shell', 'delete_file']:
            return return_error("Invalid action type", 400)

        needed_action_function = getattr(self, action_type)

        self._create_action_thread(
            device_data, needed_action_function, action_id, **request_data)
        return ''

    def put_file(self, device_data, file_buffer, dst_path):
        return_error("Not implemented yet", 400)

    def get_file(self, device_data, file_path):
        return_error("Not implemented yet", 400)

    def execute_binary(self, device_data, binary_buffer):
        return_error("Not implemented yet", 400)

    def execute_shell(self, device_data, shell_command):
        return_error("Not implemented yet", 400)

    def delete_file(self, device_data, file_path):
        return_error("Not implemented yet", 400)

    @abstractmethod
    def _parse_clients_data(self, clients_config):
        """Abstract method for retrieving clients data as dictionary from the raw clients data (fetched from config)

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
            raw_devices = list(
                self._query_devices_by_client(client_name, client))
            parsed_devices = list(self._parse_raw_data(raw_devices))
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
        """Returning the data inside 'clients' Collection on <plugin_unique_name> db.
        """
        return self._get_db_connection(True)[self.plugin_unique_name]['clients'].find()

    def _update_clients_schema_in_db(self, schema):
        """
        Every adapter has to update the DB about the scheme it expects for its clients.
        This logic is ran when the adapter starts
        :return:
        """
        with self._get_db_connection(True) as db_connection:
            collection = db_connection[self.plugin_unique_name]['adapter_schema']
            collection.replace_one(filter={'adapter_name': self.plugin_unique_name,
                                           'adapter_version': self.version},
                                   replacement={
                                       'adapter_name': self.plugin_unique_name,
                                       'adapter_version': self.version,
                                       'schema': schema
            }, upsert=True)

    @property
    def plugin_type(self):
        return "Adapter"
