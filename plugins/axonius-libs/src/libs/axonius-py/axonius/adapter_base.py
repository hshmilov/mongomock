"""
AdapterBase is an abstract class all adapters should inherit from.
It implements API calls that are expected to be present in all adapters.
"""
from typing import Iterable

from axonius import adapter_exceptions
from axonius.device import Device, LAST_SEEN_FIELD
from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.parsing_utils import get_exception_string
from axonius.thread_pool_executor import LoggedThreadPoolExecutor
from abc import ABC, abstractmethod
from flask import jsonify, request
import json
from bson import ObjectId
from threading import RLock
from axonius.config_reader import AdapterConfig
from axonius.consts import adapter_consts
from axonius.mixins.feature import Feature
from datetime import datetime
from datetime import timedelta
from enum import Enum, auto
import sys


def is_plugin_adapter(plugin_type: str) -> bool:
    """
    Whether or not a plugin is an adapter, according to the plugin_type
    :param plugin_type:
    :return:
    """
    return plugin_type in (adapter_consts.ADAPTER_PLUGIN_TYPE, adapter_consts.SCANNER_ADAPTER_PLUGIN_TYPE)


class DeviceRunningState(Enum):
    """
    Defines the state of device. i.e. if it is turned on or not
    """

    def _generate_next_value_(name, *args):
        return name

    """
    Device is on
    """
    TurnedOn = auto()
    """
    Device is off
    """
    TurnedOff = auto()
    """
    Device is suspended, i.e. hibenate
    """
    Suspended = auto()
    """
    Device is in the process of shutting down
    """
    ShuttingDown = auto()
    """
    State is unknown
    """
    Unknown = auto()


class AdapterBase(PluginBase, Feature, ABC):
    """
    Base abstract class for all adapters
    Terminology:
        "Adapter Source" - The source for data for this plugin. For example, a Domain Controller or AWS
        "Available Device" - A device that the adapter source knows and reports its existence.
                             Doesn't necessary means that the device is turned on or connected.
    """
    MyDevice = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        device_alive_thresh = self.config["DEFAULT"].getfloat(adapter_consts.DEFAULT_DEVICE_ALIVE_THRESHOLD_HOURS, -1)

        self.logger.info(f"Setting last seen threshold to {device_alive_thresh}")

        self.last_seen_timedelta = timedelta(hours=device_alive_thresh)

        self._clients_lock = RLock()

        self._send_reset_to_ec()

        self._update_clients_schema_in_db(self._clients_schema())

        self._prepare_parsed_clients_config()

        self._thread_pool = LoggedThreadPoolExecutor(self.logger, max_workers=50)

        self._fields_set = set()  # contains an Adapter specific list of field names.
        self._raw_fields_set = set()  # contains an Adapter specific list of raw-fields names.
        self._last_fields_count = (0, 0)  # count of _fields_set and _raw_fields_set when performed the last save to DB
        self._first_fields_change = True
        self._fields_db_lock = RLock()

    @classmethod
    def specific_supported_features(cls) -> list:
        return ["Adapter"]

    def _save_field_names_to_db(self):
        """ Saves fields_set and raw_fields_set to the Adapter's DB """
        with self._fields_db_lock:
            last_fields_count, last_raw_fields_count = self._last_fields_count
            if len(self._fields_set) == last_fields_count and len(self._raw_fields_set) == last_raw_fields_count:
                return  # Optimization

            fields = list(self._fields_set)  # copy
            raw_fields = list(self._raw_fields_set)  # copy

            # Upsert new fields
            fields_collection = self._get_db_connection(True)[self.plugin_unique_name]['fields']
            fields_collection.update({'name': 'fields'}, {'$addToSet': {'specific': {'$each': fields}}}, upsert=True)
            fields_collection.update({'name': 'fields'}, {'$addToSet': {'raw': {'$each': raw_fields}}}, upsert=True)
            if self._first_fields_change:
                fields_collection.update({'name': self.plugin_name},
                                         {'name': self.plugin_name, 'schema': self.MyDevice.get_fields_info()},
                                         upsert=True)
                self._first_fields_change = False

            # Save last update count
            self._last_fields_count = len(fields), len(raw_fields)

    def _new_device(self) -> Device:
        """ Returns a new empty device associated with this adapter. """
        if self.MyDevice is None:
            raise ValueError('class MyDevice(Device) class was not declared inside this Adapter class')
        return self.MyDevice(self._fields_set, self._raw_fields_set)

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
                self._add_client(client['client_config'], str(client['_id']))

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
        self.logger.info(f"Trying to query devices from client {client_name}")
        if client_name not in self._clients:
            self.logger.error(f"client {client_name} does not exist")
            return return_error("Client does not exist", 404)
        try:
            time_before_query = datetime.now()
            raw_devices, parsed_devices = self._try_query_devices_by_client(client_name)
            query_time = datetime.now() - time_before_query
            self.logger.info(f"Querying {client_name} took {query_time.seconds} seconds and "
                             f"returned {len(parsed_devices)} devices")
            self.logger.info("Querying devices on ")
        except adapter_exceptions.CredentialErrorException as e:
            self.logger.exception(f"Credentials error for {client_name} on {self.plugin_unique_name}")
            return return_error(f"Credentials error for {client_name} on {self.plugin_unique_name}", 500)
        except adapter_exceptions.AdapterException as e:
            self.logger.exception(f"AdapterException for {client_name} on {self.plugin_unique_name}: {repr(e)}")
            return return_error(f"AdapterException for {client_name} on {self.plugin_unique_name}: {repr(e)}", 500)
        except Exception as e:
            self.logger.exception(f"Error while trying to get devices for {client_name}. Details: {repr(e)}")
            return return_error(f"Error while trying to get devices for {client_name}. Details: {repr(e)}")
            # TODO raise the error, after verifying all adapter return an expected error
        else:
            devices_list = {'raw': raw_devices,
                            'parsed': parsed_devices}

            return jsonify(devices_list)

    @add_rule('users', methods=['GET'])
    def users(self):
        """
        Some adapters can get a list of users (serve not only as inventory). Get a list of users.
        # TODO Avidor: This has to be a well-defined format. currently there is no scheme for that,
        # so i define my own here.
        :return: an object in the following format

        {
        "client_id_1":
            {
            "user_id_1":{
                        "some_parsed_key_name": "some_parsed_key_value"
                        "raw": {}
                        }
            }
        }

        """

        current_clients = self._clients.copy()
        users_object = {}
        try:
            for key, value in current_clients.items():
                data = self._query_users_by_client(key, value)
                users_object[key] = data
        except NotImplementedError:
            return_error("/users is not implemented in this adapter.", 400)

        return jsonify(users_object)

    def _query_users_by_client(self, key, data):
        """

        :param key: the client key
        :param data: the client data
        :return: refer to users()
        """

        return NotImplementedError()

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
                add_client_result = self._add_client(client_config)
                if len(add_client_result) == 0:
                    return_error("Could not save client with given config", 400)
                return jsonify(add_client_result), 200

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

    def _add_client(self, client_config, id=None):
        """
        Execute connection to client, according to given credentials, that follow adapter's client schema.
        Add created connection to adapter's clients dict, under generated key.

        :param client_config: Credential values representing a client of the adapter

        :type client_config: dict of objects, following structure stated by client schema

        :return: Mongo id of created \ updated document (updated should be the given client_unique_id)

        :raises AdapterExceptions.ClientSaveException: If there was a problem saving given client
        """
        client_id = None
        status = "error"
        try:
            client_id = self._get_client_id(client_config)
            self._clients[client_id] = self._connect_client(client_config)
            # Got here only if connection succeeded
            status = "success"
        except (adapter_exceptions.ClientConnectionException, KeyError, Exception) as e:
            id_for_log = client_id if client_id else (id if id else '')
            self.logger.exception(
                f"Got error while handling client {id_for_log} - \
                possibly compliance problem with schema. Details: {repr(e)}")
            if client_id in self._clients:
                del self._clients[client_id]

        if client_id is not None:
            # Updating DB according to the axiom that client_id is a unique field across clients
            self.logger.info(f"Setting {client_id} status to {status}")
            result = self._get_collection('clients').replace_one({'client_id': client_id},
                                                                 {
                                                                     'client_id': client_id,
                                                                     'client_config': client_config,
                                                                     'status': status
            }, upsert=True)
        elif id is not None:
            # Client id was not found due to some problem in given config data
            # If id of an existing document is given, update its status accordingly
            result = self._get_collection('clients').update_one({'_id': ObjectId(id)}, {'$set': {'status': status}})
        else:
            # No way of updating other than logs and no return value
            self.logger.error("Not updating client since no DB id and no client id exist")
            return {}

        # Verifying update succeeded and returning the matched id and final status
        if not result.modified_count and result.upserted_id:
            return {"id": str(result.upserted_id), "status": status}

        return {}

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
        except Exception:
            self.logger.exception(f"Failed running actionid {action_id}")
            self._update_action_data(action_id, status="failed", output={
                "result": "Failure", "product": get_exception_string()})
            return

        # Sending the result to the issuer
        self._update_action_data(action_id, status="finished", output=result)

    def _create_action_thread(self, device, func, action_id, **kwargs):
        """ Function for creating action thread.
        """
        # Getting action id
        self._thread_pool.submit(self._run_action_thread, func, device, action_id, **kwargs)

    @add_rule('action/<action_type>', methods=['POST'])
    def rest_new_action(self, action_type):
        # Getting action id from the URL
        action_id = self.get_url_param('action_id')
        request_data = self.get_request_data_as_object()
        device_data = request_data.pop('device_data')

        if action_type not in ['get_file', 'put_file', 'execute_binary', 'execute_shell', 'execute_wmi_queries',
                               'delete_file']:
            return return_error("Invalid action type", 400)

        needed_action_function = getattr(self, action_type)

        self.logger.info("Got action type {0}. Request data is {1}".format(action_type, request_data))

        self._create_action_thread(
            device_data, needed_action_function, action_id, **request_data)
        return ''

    def put_file(self, device_data, file_buffer, dst_path):
        raise RuntimeError("Not implemented yet")

    def get_file(self, device_data, file_path):
        raise RuntimeError("Not implemented yet")

    def execute_binary(self, device_data, binary_buffer):
        raise RuntimeError("Not implemented yet")

    def execute_shell(self, device_data, shell_command):
        raise RuntimeError("Not implemented yet")

    def execute_wmi_queries(self, device_data, wmi_queries):
        raise RuntimeError("Not implemented yet")

    def delete_file(self, device_data, file_path):
        raise RuntimeError("Not implemented yet")

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

    def is_old_device(self, parsed_device):
        """ Checking if a device has not seen for a long time

        :param parsed_device: A parsed data of the device
        :return: True if device was not seen for the wanted period of time
        """
        if LAST_SEEN_FIELD in parsed_device:
            device_time = parsed_device[LAST_SEEN_FIELD]
            # Getting the time zone from the original device
            now = datetime.now(tz=device_time.tzinfo)

            return self.last_seen_timedelta.days != -1 and now - device_time > self.last_seen_timedelta
        else:
            return False

    def _remove_big_keys(self, key_to_check, device_id):
        """ Function for removing big elements in data chanks.

        Function will recursively pass over known data types and remove big values

        :param key_to_check: A key to check size for
        :return: A key with no big data fields
        """
        if sys.getsizeof(key_to_check) < 1e5:  # Key smaller than ~100kb
            # Return small devices immediately
            return key_to_check

        # If we reached here it means that the key is too big, trying to clean known data types
        if type(key_to_check) == dict:
            key_to_check = {key: self._remove_big_keys(value, device_id) for key, value in key_to_check.items()}

        if type(key_to_check) == list:
            key_to_check = [self._remove_big_keys(val, device_id) for val in key_to_check]

        # Checking if the key is small enough after the filtering big sub-keys
        if sys.getsizeof(key_to_check) < 1e5:  # Key smaller than ~100kb
            # Key is smaller now, we can return it
            return key_to_check
        else:
            # Data type not recognized or can't filter key, deleting the too big key
            self.logger.warning(f"Found too big key on device {device_id}. Deleting")
            return {'AXON_TOO_BIG_VALUE': sys.getsizeof(key_to_check)}

    def parse_raw_data_hook(self, raw_devices):
        """
        :param raw_devices: raw devices as fetched by adapter
        :return: iterator of processed raw device entries
        """
        skipped_count = 0
        for parsed_device in self._parse_raw_data(raw_devices):
            assert isinstance(parsed_device, Device)
            parsed_device = parsed_device.to_dict()
            parsed_device = self._remove_big_keys(parsed_device, parsed_device.get('id', 'unidentified device'))
            if self.is_old_device(parsed_device):
                skipped_count += 1
                continue

            yield parsed_device

        self._save_field_names_to_db()

        if skipped_count > 0:
            self.logger.info(f"Skipped {skipped_count} old devices")
        else:
            self.logger.warning("No old devices filtered (did you choose ttl period on the config file?)")

    def _try_query_devices_by_client(self, client_id):
        """
        Try querying devices for given client. If fails, try reconnecting to client.
        If successful, try querying devices with new connection to the original client, up to 3 times.

        This is an attempt to resolve problems with fetching devices that may be caused by an outdated connection
        or to discover a real problem fetching devices, despite a working connection.

        :return: Raw and parsed devices list if fetched successfully, whether immediately or with fresh connection
        :raises Exception: If client connection or client devices query errored 3 times
        """

        def _update_client_status(status):
            """
            Update client document matching given match object with given status, to indicate method's result

            :param client_id: Mongo ObjectId
            :param status: String representing current status
            :return:
            """
            with self._clients_lock:
                result = clients_collection.update_one({'client_id': client_id}, {'$set': {'status': status}})
                if not result or result.matched_count != 1:
                    raise adapter_exceptions.CredentialErrorException(
                        f"Could not update client {client_id} with status {status}")

        clients_collection = self._get_db_connection(True)[self.plugin_unique_name]["clients"]
        try:
            raw_devices = self._query_devices_by_client(client_id, self._clients[client_id])
            parsed_devices = list(self.parse_raw_data_hook(raw_devices))
        except Exception as e:
            with self._clients_lock:
                current_client = clients_collection.find_one({'client_id': client_id})
                if not current_client or not current_client.get("client_config"):
                    # No credentials to attempt reconnection
                    raise adapter_exceptions.CredentialErrorException(
                        "No credentials found for client {0}. Reason: {1}".format(client_id, str(e)))
            try:
                self._clients[client_id] = self._connect_client(current_client["client_config"])
            except Exception as e2:
                # No connection to attempt querying
                self.create_notification("Connection error to client {0}.".format(client_id), str(e2))
                self.logger.exception(
                    "Problem establishing connection for client {0}. Reason: {1}".format(client_id, str(e2)))
                _update_client_status("error")
                raise
            else:
                try:
                    raw_devices = self._query_devices_by_client(client_id, self._clients[client_id])
                    parsed_devices = list(self.parse_raw_data_hook(raw_devices))
                except:
                    # No devices despite a working connection
                    self.logger.exception("Problem querying devices for client {0}".format(client_id))
                    _update_client_status("error")
                    raise
        _update_client_status("success")
        return raw_devices, parsed_devices

    def _query_devices(self):
        """
        Synchronously returns all available devices from all clients.

        :return: iterator([client_name, devices])
        """
        if len(self._clients) == 0:
            self.logger.info(f"{self.plugin_unique_name}: Trying to fetch devices but no clients found")
            return

        # Running query on each device
        for client_name in self._clients:
            try:
                raw_devices, parsed_devices = self._try_query_devices_by_client(client_name)
            except adapter_exceptions.CredentialErrorException as e:
                self.logger.warning(f"Credentials error for {client_name} on {self.plugin_unique_name}: {repr(e)}")
                self.create_notification(f"Credentials error for {client_name} on {self.plugin_unique_name}", repr(e))
            except adapter_exceptions.AdapterException as e:
                self.logger.exception(f"Error for {client_name} on {self.plugin_unique_name}: {repr(e)}")
                self.create_notification(f"Error for {client_name} on {self.plugin_unique_name}", repr(e))
            except Exception as e:
                self.logger.exception(f"Unknown error for {client_name} on {self.plugin_unique_name}: {repr(e)}")
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
    def _parse_raw_data(self, devices_raw_data) -> Iterable[Device]:
        """
        To be implemented by inheritors
        Will convert 'raw data' of one device (as the inheritor pleases to refer to it) to 'parsed' 

        :param devices_raw_data: raw data as received by /devices/client, i.e. without the client->data association
        :return: parsed data as iterable Device collection
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

    @property
    def plugin_type(self):
        return adapter_consts.SCANNER_ADAPTER_PLUGIN_TYPE

    def populate_register_doc(self, register_doc, config_file_path):
        config = AdapterConfig(config_file_path)
        register_doc[adapter_consts.DEFAULT_SAMPLE_RATE] = int(config.default_sample_rate)
