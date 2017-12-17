"""
AdapterBase is an abstract class all adapters should inherit from.
It implements API calls that are expected to be present in all adapters.
"""

import concurrent.futures

from axonius import AdapterExceptions
from axonius.PluginBase import PluginBase, add_rule, return_error
from abc import ABC, abstractmethod
from flask import jsonify, request
import json
from bson import ObjectId
from threading import RLock
from axonius.ConfigReader import AdapterConfig
from axonius.consts import AdapterConsts


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

        self._clients_lock = RLock()

        self._send_reset_to_ec()

        self._update_clients_schema_in_db(self._clients_schema())

        self._prepare_parsed_clients_config()

        self._thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=50)

    def _send_reset_to_ec(self):
        """ Function for notifying the EC that this Adapted has been reset.
        """
        self.request_remote_plugin('action_update/adapter_action_reset?unique_name={0}'.format(self.plugin_unique_name),
                                   plugin_unique_name='execution',
                                   method='POST')

    def _prepare_parsed_clients_config(self):
        with self._clients_lock:
            configured_clients = self._get_clients_config()

            # self._clients might be replaced at any moment when POST /clients is received
            # so it must be used cautiously
            self._clients = {}
            for client in configured_clients:
                # client id from DB not sent to verify it is updated
                self._add_client(client['client_config'])

    @add_rule('devices', methods=['GET'])
    def devices(self):
        """ /devices Query adapter to fetch all available devices.
        An "available" device is a device that is registered with the adapter source.

        Accepts:
           GET - Finds all available devices, and returns them
        """
        return jsonify(self._query_devices())

    @add_rule('devices_by_name', methods=['GET'])
    def devices_by_client(self):
        """ /devices_by_name?name= Query adapter to fetch all available devices from a specific client.
        An "available" device is a device that is registered with the adapter source.

        Accepts:
           GET - Finds all available devices from a specific client, and returns them
        """
        client_name = request.args.get('name')
        client = self._clients.get(client_name)
        if client is None:
            return return_error("Client does not exist", 404)

        try:
            raw_devices = self._query_devices_by_client(client_name, client)
            parsed_devices = list(self._parse_raw_data(raw_devices))
        except AdapterExceptions.CredentialErrorException as e:
            return_error(f"Credentials error for {client_name} on {self.plugin_unique_name}", 500)
        except AdapterExceptions.AdapterException as e:
            return_error(f"AdapterException for {client_name} on {self.plugin_unique_name}: {repr(e)}", 500)
        except Exception as e:
            self.logger.error(f"Error while trying to get devices for {client_name}. Details: {repr(e)}")
            return return_error(f"Unknown error for {client_name} on {self.plugin_unique_name}: {repr(e)}", 500)
        else:
            devices_list = {'raw': raw_devices,
                            'parsed': parsed_devices}

            return jsonify(devices_list)

    @add_rule('clients', methods=['GET', 'POST', 'PUT'])
    def clients(self):
        """ /clients Returns all available clients, e.g. all DC servers.

        Accepts:
           GET  - Returns all available clients
           POST - Triggers a refresh on all available clients from the DB and returns them
           PUT (expects client data) - Adds a new client, or updates existing one, according to given data.
                                       Uniqueness compared according to _get_client_id value.
        """
        with self._clients_lock:
            if self.get_method() == 'PUT':
                client_config = request.get_json(silent=True)
                if not client_config:
                    return return_error("Invalid client")
                try:
                    return self._add_client(client_config), 200
                except AdapterExceptions.ClientSaveException as e:
                    return return_error(str(e))
                except KeyError as e:
                    return return_error("Key error for client. details: {0}".format(str(e)))

            if self.get_method() == 'POST':
                self._prepare_parsed_clients_config()

            return jsonify(self._clients.keys())

    @add_rule('clients/<client_unique_id>', methods=['DELETE'])
    def update_client(self, client_unique_id):
        """
        Update config of or delete and existing client for the adapter, by their client id

        :param client_key:
        :return:
        """
        with self._clients_lock:
            client = self._get_collection('clients').find_one_and_delete({'_id': ObjectId(client_unique_id)})
            if client is None:
                return '', 204
            client_id = ''
            try:
                client_id = self._get_client_id(client['client_config'])
            except KeyError as e:
                self.logger.info("Problem creating client id, to remove from connected clients")
            try:
                del self._clients[client_id]
            except KeyError as e:
                self.logger.info("No connected client {0} to remove".format(client_id))
            return '', 200

    def _add_client(self, client_config):
        """
        Execute connection to client, according to given credentials, that follow adapter's client schema.
        Add created connection to adapter's clients dict, under generated key.

        :param client_config: Credential values representing a client of the adapter

        :type client_config: dict of objects, following structure stated by client schema

        :return: Mongo id of created \ updated document (updated should be the given client_unique_id)

        :raises AdapterExceptions.ClientSaveException: If there was a problem saving given client
        """
        client_id = self._get_client_id(client_config)
        status = "error"
        try:
            self._clients[client_id] = self._connect_client(client_config)
            # Got here only if connection succeeded
            status = "success"
        except AdapterExceptions.ClientConnectionException as e:
            pass
        except Exception as e:
            self.logger.error(f"Unknown exception: {str(e)}")

        result = self._get_collection('clients').replace_one({'client_id': client_id},
                                                             {
                                                                 'client_id': client_id,
                                                                 'client_config': client_config,
                                                                 'status': status
        }, upsert=True)
        if not result.modified_count:
            if not result.upserted_id:
                raise AdapterExceptions.ClientSaveException("Could not update client {0} in DB".format(client_id))
            else:
                return str(result.upserted_id)
        return ''

    @add_rule('correlation_cmds', methods=['GET'])
    def correlation_cmds(self):
        """ /correlation_cmds Get a dictionary between OS type and shell command that'll figure out the device ID
        refer to https://axonius.atlassian.net/wiki/spaces/AX/pages/90472522/Correlation+Implementation for more
        """
        return jsonify(self._correlation_cmds())

    @add_rule('parse_correlation_results', methods=['POST'])
    def parse_correlation_results(self):
        """ /parse_correlation_results Parses the given results (as string) into a device ID
        Assumes POST data has:
        {
            "result": "some text",
            "os": "Windows" # or Linux, or whatever else returned as a key from /correlation_cmds
        }
        :return: str
        """
        data = request.get_json(silent=True)
        if data is None:
            return return_error("No data received")
        if 'result' not in data or 'os' not in data:
            return return_error("Invalid data received")
        return jsonify(self._parse_correlation_results(data['result'], data['os']))

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
    def _get_client_id(self, client_config):
        """
        Given all details of a client belonging to the adapter, return consistent key representing it

        :param client_config: A dictionary with connection credentials for adapter's client, according to stated in
        the appropriate schema (all required and any of optional)

        :type client_config: dict of objects, following structure stated by client schema

        :return: unique key for the client, composed by given field values, according to adapter's definition
        """
        pass

    @abstractmethod
    def _connect_client(self, client_config):
        """
        Given all details of a client belonging to the adapter, tries connecting to it and creating a connection obj.
        If connection attempt failed, throws exception with the reason

        :param client_config: A dictionary with connection credentials for adapter's client, according to stated in
        the appropriate schema (all required and any of optional)

        :type client_config: dict of objects, following structure stated by client schema

        :returns: Adapter's connection object, if connection attempt succeeded with given credentials

        :raises AdapterExceptions.ClientConnectionException: In case of error connecting, return adapter's exception
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
        if len(self._clients) == 0:
            self.logger.info(f"{self.plugin_unique_name}: Trying to fetch devices but no clients found")
            return

        # Running query on each device
        for client_name, client in self._clients.items():
            try:
                raw_devices = self._query_devices_by_client(client_name, client)
                parsed_devices = list(self._parse_raw_data(raw_devices))
            except AdapterExceptions.CredentialErrorException as e:
                self.logger.warning(f"Credentials error for {client_name} on {self.plugin_unique_name}: {repr(e)}")
                self.create_notification(f"Credentials error for {client_name} on {self.plugin_unique_name}", repr(e))
            except AdapterExceptions.AdapterException as e:
                self.logger.error(f"Error for {client_name} on {self.plugin_unique_name}: {repr(e)}")
                self.create_notification(f"Error for {client_name} on {self.plugin_unique_name}", repr(e))
            except Exception as e:
                self.logger.error(f"Unknown error for {client_name} on {self.plugin_unique_name}: {repr(e)}")
            else:
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

    def _correlation_cmds(self):
        """
        To be implemented by inheritors, otherwise leave empty.
        Returns dict between OS type and shell, e.g.
        {
            "Linux": "curl http://169.254.169.254/latest/meta-data/instance-id",
            "Windows": "powershell -Command \"& Invoke-RestMethod -uri http://169.254.169.254/latest/meta-data/instance-id\""
        }
        :return: shell commands that help collerations
        """
        return {}

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        """
        To be implemented by inheritors, otherwise leave empty.
        :type correlation_cmd_result: str
        :param correlation_cmd_result: result of running cmd on a machine
        :type os_type: str
        :param os_type: the type of machine ran upon
        :return:
        """
        raise NotImplementedError()

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

    def _tag_device(self, adapter_id, wanted_tag):
        """ Function for tagging adapter devices.
        This function will tag a wanted device. The tag will be related only to this adapter
        :param adapter_id: The device id given by the current adapter
        :param wanted_tag: The tag we want to assign to this device
        :return:
        """
        tag_data = {'association_type': 'Tag',
                    'associated_adapter_devices': {
                        self.plugin_unique_name: adapter_id
                    },
                    "tagname": wanted_tag,
                    "tagvalue": wanted_tag}
        response = self.request_remote_plugin(
            'plugin_push', "aggregator", 'post', data=json.dumps(tag_data))
        if response != 200:
            self.logger.error(f"Couldnt tag device. Reason: {response.status_code}, {str(response.content)}")
            raise AdapterExceptions.TagDeviceError()

    @property
    def plugin_type(self):
        return "Adapter"

    def populate_register_doc(self, register_doc, config_file_path):
        config = AdapterConfig(config_file_path)
        register_doc[AdapterConsts.DEFAULT_SAMPLE_RATE] = int(config.default_sample_rate)
