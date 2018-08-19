"""
AdapterBase is an abstract class all adapters should inherit from.
It implements API calls that are expected to be present in all adapters.
"""
import json
import logging
import sys
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta, timezone
from enum import Enum, auto
from threading import Event, RLock, Thread
from typing import Any, Dict, Iterable, List, Tuple

from bson import ObjectId
from flask import jsonify, request

from axonius import adapter_exceptions
from axonius.config_reader import AdapterConfig
from axonius.consts import adapter_consts
from axonius.consts.plugin_consts import (AGGREGATOR_PLUGIN_NAME, PLUGIN_NAME,
                                          PLUGIN_UNIQUE_NAME)
from axonius.devices.device_adapter import LAST_SEEN_FIELD, DeviceAdapter
from axonius.mixins.configurable import Configurable
from axonius.mixins.feature import Feature
from axonius.plugin_base import EntityType, PluginBase, add_rule, return_error
from axonius.thread_pool_executor import LoggedThreadPoolExecutor
from axonius.thread_stopper import stoppable
from axonius.users.user_adapter import UserAdapter
from axonius.utils.json import to_json
from axonius.utils.parsing import get_exception_string

logger = logging.getLogger(f'axonius.{__name__}')


def is_plugin_adapter(plugin_type: str) -> bool:
    """
    Whether or not a plugin is an adapter, according to the plugin_type
    :param plugin_type:
    :return:
    """
    return plugin_type == adapter_consts.ADAPTER_PLUGIN_TYPE


class AdapterProperty(Enum):
    """
    Possible properties of the adapter
    """

    def _generate_next_value_(name, *args):
        return name

    # Naming scheme: Underscore is replaced with space for the facade, so "Antivirus_System" will show
    # as "Antivirus System" (see above _generate_next_value_)
    # Otherwise - provide a name: `AVSystem = "Antivirus System"`
    # TODO: Make the GUI actually support this
    Agent = auto()
    Endpoint_Protection_Platform = auto()
    Network = auto()
    Firewall = auto()
    Manager = auto()
    Vulnerability_Assessment = auto()
    Assets = auto()
    UserManagement = auto()


class AdapterBase(PluginBase, Configurable, Feature, ABC):
    """
    Base abstract class for all adapters
    Terminology:
        "Adapter Source" - The source for data for this plugin. For example, a Domain Controller or AWS
        "Available Device" - A device that the adapter source knows and reports its existence.
                             Doesn't necessary means that the device is turned on or connected.
    """
    DEFAULT_LAST_SEEN_THRESHOLD_HOURS = 24 * 365 * 5
    DEFAULT_LAST_FETCHED_THRESHOLD_HOURS = 24 * 2
    DEFAULT_USER_LAST_SEEN = None
    DEFAULT_USER_LAST_FETCHED = None
    DEFAULT_MINIMUM_TIME_UNTIL_NEXT_FETCH = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._clients_lock = RLock()
        self._clients = {}

        self._index_lock = RLock()
        self._index = 0

        self._send_reset_to_ec()

        self._update_clients_schema_in_db(self._clients_schema())

        self._prepare_parsed_clients_config(False)

        self._thread_pool = LoggedThreadPoolExecutor(max_workers=50)

        self.__last_fetch_time = None

    def _on_config_update(self, config):
        logger.info(f"Loading AdapterBase config: {config}")

        # Devices older then the given deltas will be deleted:
        # Either by:
        self._last_seen_timedelta = timedelta(hours=config['last_seen_threshold_hours']) if \
            config['last_seen_threshold_hours'] else None
        # this is the delta used for "last_seen" field from the adapter (if provided)

        # Or by:
        self._last_fetched_timedelta = timedelta(hours=config['last_fetched_threshold_hours']) if \
            config['last_fetched_threshold_hours'] else None
        # this is the delta used for comparing "accurate_for_datetime" - i.e. the last time the devices was fetched

        self.__user_last_seen_timedelta = timedelta(hours=config['user_last_seen_threshold_hours']) if \
            config['user_last_seen_threshold_hours'] else None
        self.__user_last_fetched_timedelta = timedelta(hours=config['user_last_fetched_threshold_hours']) if \
            config['user_last_fetched_threshold_hours'] else None

        self.__next_fetch_timedelta = timedelta(hours=config['minimum_time_until_next_fetch']) if \
            config['minimum_time_until_next_fetch'] else None

    @classmethod
    def specific_supported_features(cls) -> list:
        return ["Adapter"]

    def _send_reset_to_ec(self):
        """ Function for notifying the EC that this Adapted has been reset.
        """
        self.request_remote_plugin('action_update/adapter_action_reset?unique_name={0}'.format(self.plugin_unique_name),
                                   plugin_unique_name='execution',
                                   method='POST')

    def _prepare_parsed_clients_config(self, blocking=True):
        configured_clients = self._get_clients_config()
        event = Event()

        def refresh():
            with self._clients_lock:
                event.set()
                try:
                    # self._clients might be replaced at any moment when POST /clients is received
                    # so it must be used cautiously
                    self._clients = {}
                    for client in configured_clients:
                        # client id from DB not sent to verify it is updated
                        self._add_client(client['client_config'], str(client['_id']))
                except Exception:
                    logger.exception('Error while loading clients from config')
                    if blocking:
                        raise

        if blocking:
            refresh()
        else:
            thread = Thread(target=refresh)
            thread.start()
            event.wait()

    def __find_old_axonius_entities(self, entity_age_cutoff: Tuple[date, date], entity_db):
        """
        Scans the DB for axonius devices that have at least one old entity or are pending to be deleted
        :return: entity cursor
        """
        last_seen_cutoff, last_fetched_cutoff = entity_age_cutoff

        dates_for_device = [
            {
                'accurate_for_datetime': {
                    "$lt": last_fetched_cutoff
                }
            },
            {
                f'data.{LAST_SEEN_FIELD}': {
                    "$lt": last_seen_cutoff
                }
            }
        ]
        dbfilter = {
            '$or':
                [
                    {
                        'adapters':
                            {
                                '$elemMatch': {
                                    "$and": [
                                        {
                                            "$or": dates_for_device
                                        },
                                        {
                                            # and the device must be from this adapter
                                            PLUGIN_NAME: self.plugin_name
                                        }
                                    ]
                                }
                            }
                    },
                    {
                        'adapters':
                            {
                                '$elemMatch': {
                                    "$and": [
                                        {
                                            "pending_delete": True
                                        },
                                        {
                                            # and the device must be from this adapter
                                            PLUGIN_NAME: self.plugin_name
                                        }
                                    ]
                                }
                            }
                    }
                ]
        }
        return entity_db.find(dbfilter)

    def __archive_axonius_device(self, plugin_unique_name, device_id, db_to_use):
        """
        Finds the axonius device with the given plugin_unique_name and device id,
        assumes that the axonius device has only this single adapter device.

        writes the device to the archive db, then deletes it
        """
        axonius_device = db_to_use.find_one_and_delete({
            'adapters': {
                '$elemMatch': {
                    PLUGIN_UNIQUE_NAME: plugin_unique_name,
                    'data.id': device_id
                }
            }
        })
        if axonius_device is None:
            logger.error(f"Tried to archive nonexisting device: {plugin_unique_name}: {device_id}")
            return False

        axonius_device['archived_at'] = datetime.utcnow()
        self.aggregator_db_connection['old_device_archive'].insert_one(axonius_device)
        return True

    def __clean_entity(self, age_cutoff, entity_type: EntityType):
        """
        Removes entities from given type from a given age cutoff
        :return:
        """
        db_to_use = self._entity_db_map.get(entity_type)
        deleted_entities_count = 0
        for axonius_entity in self.__find_old_axonius_entities(age_cutoff, db_to_use):
            old_adapter_entities = self.__extract_old_entities_from_axonius_device(axonius_entity,
                                                                                   age_cutoff)

            deleted_entities_count += self.__unlink_and_delete_entity(axonius_entity,
                                                                      db_to_use,
                                                                      entity_type,
                                                                      old_adapter_entities)

        return deleted_entities_count

    def __unlink_and_delete_entity(self, axonius_entity, db_to_use, entity_type,
                                   adapter_entities_to_delete):
        counter = 0
        for index, entity_to_remove in enumerate(adapter_entities_to_delete):
            if index < len(axonius_entity['adapters']) - 1:
                logger.info(f"Unlinking entity {entity_to_remove}")
                # if the above condition isn't met it means
                # that the current entity is the last one (or even the only one)
                # if it is in fact the only one there's no Unlink to do: the whole axonius device is gone
                response = self.request_remote_plugin('plugin_push', AGGREGATOR_PLUGIN_NAME, 'post', json={
                    "plugin_type": "Plugin",
                    "data": {
                        'Reason': 'The device is too old so it is going to be deleted'
                    },
                    "associated_adapters": [
                        entity_to_remove
                    ],
                    "association_type": "Unlink",
                    "entity": entity_type.value
                })
                if response.status_code != 200:
                    logger.error(f"Unlink failed for {entity_to_remove}," +
                                 "not removing the device for consistency." +
                                 f"Error: {response.status_code}, {str(response.content)}")

                    continue

            logger.info(f"Deleting axonius device {entity_to_remove}")
            if self.__archive_axonius_device(*entity_to_remove, db_to_use):
                counter += 1
        return counter

    def clean_db(self):
        """
        Figures out which devices are too old and removes them from the db.
        Unlinks devices first if necessary.
        :return: Amount of deleted devices
        """
        device_age_cutoff = self.__device_time_cutoff()
        user_age_cutoff = self.__user_time_cutoff()
        logger.info(f"Cleaning devices and users that are before {device_age_cutoff}, {user_age_cutoff}")
        devices_cleaned = self.__clean_entity(device_age_cutoff, EntityType.Devices)
        users_cleaned = self.__clean_entity(user_age_cutoff, EntityType.Users)
        logger.info(f"Cleaned {devices_cleaned} devices and {users_cleaned} users")
        return {EntityType.Devices.value: devices_cleaned, EntityType.Users.value: users_cleaned}

    @stoppable
    @add_rule("clean_devices", methods=["POST"])
    def clean_devices(self):
        """
        Find and delete devices that are old and remove them.
        This should only be called when fetching is not in progress.
        :return:
        """
        return to_json(self.clean_db())

    @add_rule('devices', methods=['GET'])
    def devices_callback(self):
        """ /devices Query adapter to fetch all available devices.
        An "available" device is a device that is registered with the adapter source.

        Accepts:
           GET - Finds all available devices, and returns them
        """
        return jsonify(dict(self._query_data(EntityType.Devices)))

    @add_rule('devices_by_name', methods=['GET'])
    def devices_by_client(self):
        """ /devices_by_name?name= Query adapter to fetch all available devices from a specific client.
        An "available" device is a device that is registered with the adapter source.

        Accepts:
           GET - Finds all available devices from a specific client, and returns them
        """
        client_name = request.args.get('name')
        return to_json(self._get_data_by_client(client_name, EntityType.Devices))

    # Users
    @add_rule('users', methods=['GET'])
    def users(self):
        """ /users Query adapter to fetch all available users.
        An "available" users is a device that is registered with the adapter source.

        Accepts:
           GET - Finds all available devices, and returns them
        """
        return to_json(dict(self._query_data(EntityType.Users)))

    def _query_users_by_client(self, key, data):
        """

        :param key: the client key
        :param data: the client data
        :return: refer to users()
        """

        # This needs to be implemented by the adapter. However, if it is not implemented, don't
        # crash the system.
        return []

    def _parse_users_raw_data_hook(self, raw_users):
        """
        A hook before we call the real parse users.
        :param raw_users: the raw data.
        :return: a list of parsed user objects
        """

        skipped_count = 0
        users_ids = []

        cutoff_last_seen, _ = self.__user_time_cutoff()

        for parsed_user in self._parse_users_raw_data(raw_users):
            assert isinstance(parsed_user, UserAdapter)

            # There is no such thing as scanners for users, so we always check for id here.
            parsed_user_id = parsed_user.id  # we must have an id
            if parsed_user_id in users_ids:
                logger.error(f"Error! user with id {parsed_user_id} already yielded! skipping")
                continue
            users_ids.append(parsed_user_id)

            parsed_user = parsed_user.to_dict()
            parsed_user = self._remove_big_keys(parsed_user, parsed_user.get('id', 'unidentified user'))
            if self.__is_entity_old_by_last_seen(parsed_user, cutoff_last_seen):
                skipped_count += 1
                continue

            yield parsed_user

        if skipped_count > 0:
            logger.info(f"Skipped {skipped_count} old users")
        else:
            logger.warning("No old users filtered (did you choose ttl period on the config file?)")

        self._save_field_names_to_db(EntityType.Users)

    def _parse_users_raw_data(self, user):
        """
        This needs to be implemented by the Adapter itself.
        :return:
        """

        return []

    @add_rule('users_by_name', methods=['GET'])
    def users_by_name(self):
        """ /users_by_name?name= Query adapter to fetch all available users from a specific client.
        An "available" users is a device that is registered with the adapter source.

        Accepts:
           GET - Finds all available users from a specific client, and returns them
        """
        client_name = request.args.get('name')
        return to_json(self._get_data_by_client(client_name, EntityType.Users))

    # End of users

    @stoppable
    @add_rule('insert_to_db', methods=['PUT'])
    def insert_data_to_db(self):
        """
        /insert_to_db?client_name=(None or Client name)

        Will insert entities from the given client name (or all clients if None) into DB
        :return:
        """
        current_time = datetime.utcnow()
        # Checking that it's either the first time since a new client was added.
        # Or that the __next_fetch_timedelta has passed since last fetch.
        if self.__last_fetch_time is not None and self.__next_fetch_timedelta is not None \
                and current_time - self.__last_fetch_time < self.__next_fetch_timedelta:
            logger.info(f"{self.plugin_unique_name}: The minimum time between fetches hasn't been reached yet.")
            if self.__user_last_fetched_timedelta < self.__next_fetch_timedelta:
                self.create_notification("Bad Adapter Configuration (\"Old user last fetched threshold hours\")",
                                         f"Please note that \"Old user last fetched threshold hours\" is smaller than \"Minimum time until next fetch entities\" for {self.plugin_name} adapter.",
                                         "warning")

            if self._last_fetched_timedelta < self.__next_fetch_timedelta:
                self.create_notification("Bad Adapter Configuration (\"Old device last fetched threshold hours\")",
                                         f"Please note that \"Old device last fetched threshold hours\" is smaller than \"Minimum time until next fetch entities\" for {self.plugin_name} adapter.",
                                         "warning")
            return to_json({"devices_count": 0, "users_count": 0})

        self.__last_fetch_time = current_time

        client_name = request.args.get('client_name')
        if client_name:
            devices_count = self._save_data_from_plugin(
                client_name, self._get_data_by_client(client_name, EntityType.Devices), EntityType.Devices)
            users_count = self._save_data_from_plugin(
                client_name, self._get_data_by_client(client_name, EntityType.Users), EntityType.Users)
        else:
            devices_count = sum(
                self._save_data_from_plugin(*data, EntityType.Devices) for data in self._query_data(EntityType.Devices))
            users_count = sum(
                self._save_data_from_plugin(*data, EntityType.Users) for data in self._query_data(EntityType.Users))

        return to_json({"devices_count": devices_count, "users_count": users_count})

    def _get_data_by_client(self, client_name: str, data_type: EntityType) -> dict:
        """
        Get all devices, both raw and parsed, from the given client name
        data_type is devices/users.
        """
        logger.info(f"Trying to query {data_type} from client {client_name}")
        with self._clients_lock:
            if client_name not in self._clients:
                logger.error(f"client {client_name} does not exist")
                raise Exception("Client does not exist")
        try:
            time_before_query = datetime.now()
            raw_data, parsed_data = self._try_query_data_by_client(client_name, data_type)
            query_time = datetime.now() - time_before_query
            logger.info(f"Querying {client_name} took {query_time.seconds} seconds - {data_type}")
        except adapter_exceptions.CredentialErrorException as e:
            logger.exception(f"Credentials error for {client_name} on {self.plugin_unique_name}")
            raise adapter_exceptions.CredentialErrorException(
                f"Credentials error for {client_name} on {self.plugin_unique_name}")
        except adapter_exceptions.AdapterException as e:
            logger.exception(f"AdapterException for {client_name} on {self.plugin_unique_name}: {repr(e)}")
            raise adapter_exceptions.AdapterException(
                f"AdapterException for {client_name} on {self.plugin_unique_name}: {repr(e)}")
        except Exception as e:
            logger.exception(f"Error while trying to get {data_type} for {client_name}. Details: {repr(e)}")
            raise Exception(f"Error while trying to get {data_type} for {client_name}. Details: {repr(e)}")
        else:
            data_list = {'raw': [],  # AD-HOC: Not returning any raw values
                         'parsed': parsed_data}

            return data_list

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
                    return return_error("Could not save client with given config", 400)
                self.__last_fetch_time = None
                return jsonify(add_client_result), 200

            if self.get_method() == 'POST':
                self._prepare_parsed_clients_config()

            return jsonify(self._clients.keys())

    @add_rule('clients/<client_unique_id>', methods=['DELETE'])
    def update_client(self, client_unique_id):
        """
        Update config of or delete an existing client for the adapter, by their client id

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
                logger.info("Problem creating client id, to remove from connected clients")
            try:
                del self._clients[client_id]
            except KeyError as e:
                logger.info("No connected client {0} to remove".format(client_id))
            return '', 200

    def _write_client_to_db(self, client_id, client_config, status, error_msg):
        if client_id is not None:
            logger.info(f"Setting {client_id} status to {status}")
            return self._get_collection('clients').replace_one({'client_id': client_id},
                                                               {'client_id': client_id,
                                                                'client_config': client_config,
                                                                'status': status,
                                                                'error': error_msg},
                                                               upsert=True)
        else:
            return None

    def _add_client(self, client_config: dict, object_id=None):
        """
        Execute connection to client, according to given credentials, that follow adapter's client schema.
        Add created connection to adapter's clients dict, under generated key.

        :param client_config: Credential values representing a client of the adapter
        :param object_id: The mongo object id
        :return: Mongo id of created \ updated document (updated should be the given client_unique_id)

        assumes self._clients_lock is locked by the current thread
        """
        client_id = None
        status = "warning"
        error_msg = None

        try:
            client_id = self._get_client_id(client_config)
            self._write_client_to_db(client_id, client_config, status, error_msg)  # Writing initial client to db
            status = "error"  # Default is error
            self._clients[client_id] = self._connect_client(client_config)
            # Got here only if connection succeeded
            status = "success"
        except (adapter_exceptions.ClientConnectionException, KeyError, Exception) as e:
            error_msg = str(e.args[0] if e.args else '')
            id_for_log = client_id if client_id else (object_id if object_id else '')
            logger.exception(f"Got error while handling client {id_for_log} - possibly compliance problem with schema.")
            if client_id in self._clients:
                del self._clients[client_id]

        result = self._write_client_to_db(client_id, client_config, status, error_msg)
        if result is None and object_id is not None:
            # Client id was not found due to some problem in given config data
            # If id of an existing document is given, update its status accordingly
            result = self._get_collection('clients').update_one(
                {'_id': ObjectId(object_id)}, {'$set': {'status': status}})
        elif result is None:
            # No way of updating other than logs and no return value
            logger.error("Not updating client since no DB id and no client id exist")
            return {}

        # Verifying update succeeded and returning the matched id and final status
        if result.modified_count:
            object_id = self._get_collection('clients').find_one({'client_id': client_id}, projection={'_id': 1})['_id']
            return {"id": str(object_id), "client_id": client_id, "status": status, "error": error_msg}

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

    # This should never be stoppable!! Or else we might stop execution while it happens, which makes
    # it possible for us to have files left on the diks
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
        self._update_action_data(action_id,
                                 status="started",
                                 output={"result": "In Progress", "product": "In Progress"})

        try:
            # Running the function, it should block until action is finished
            result = func(device_data, **kwargs)
        except Exception:
            logger.exception(f"Failed running actionid {action_id}")
            self._update_action_data(action_id, status="failed", output={
                "result": "Failure", "product": get_exception_string()})
            return

        # Sending the result to the issuer
        if str(result.get('result')).lower() == 'success':
            status = "finished"
        else:
            status = "failed"
        self._update_action_data(action_id, status=status, output=result)

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

        if action_type not in ['get_files', 'put_files', 'execute_binary', 'execute_shell', 'execute_wmi_smb',
                               'delete_files', 'execute_axr']:
            return return_error("Invalid action type", 400)

        if action_type not in self.supported_execution_features():
            return return_error("Operation not implemented yet", 501)  # 501 -> Not implemented

        needed_action_function = getattr(self, action_type)

        logger.info("Got action type {0}. Request data is {1}".format(action_type, request_data))

        self._create_action_thread(
            device_data, needed_action_function, action_id, **request_data)
        return ''

    def supported_execution_features(self):
        return []

    def put_files(self, device_data, files_path, files_content):
        raise RuntimeError("Not implemented yet")

    def get_files(self, device_data, files_path):
        raise RuntimeError("Not implemented yet")

    def execute_binary(self, device_data, binary_file_path, binary_params):
        raise RuntimeError("Not implemented yet")

    def execute_shell(self, device_data, shell_commands):
        raise RuntimeError("Not implemented yet")

    def execute_axr(self, device_data, axr_commands):
        raise RuntimeError("Not implemented yet")

    def execute_wmi_smb(self, device_data, wmi_smb_commands=None):
        raise RuntimeError("Not implemented yet")

    def delete_files(self, device_data, files_path):
        raise RuntimeError("Not implemented yet")

    @abstractmethod
    def _get_client_id(self, client_config):
        """
        Given all details of a client belonging to the adapter, return consistent key representing it.
        This key must be "unclassified" - not contain any sensitive information as it is disclosed to the user.

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

    def _query_devices_by_client(self, client_name, client_data):
        """
        Returns all devices from a specific client.
        Refer to devices(client) docs for the return type.

        :param client_name: str # valid values are from self._get_clients
        :param client_data: The data of the client, as returned from the _parse_clients_data function
        :return: adapter dependant
        """
        return []

    def __is_old_entity(self, parsed_entity, cutoff: Tuple[date, date]) -> bool:
        """ Check if the entity is considered "old".

        :param parsed_entity: A parsed data of the entity
        :return: If the entity is old or not.
        """
        seen_cutoff, fetched_cutoff = cutoff
        return self.__is_entity_old_by_last_fetched(parsed_entity, fetched_cutoff) or \
            self.__is_entity_old_by_last_seen(parsed_entity['data'], seen_cutoff)

    @staticmethod
    def __is_entity_old_by_last_seen(parsed_entity_data, seen_cutoff: date):
        if not seen_cutoff:
            return False
        if LAST_SEEN_FIELD in parsed_entity_data:
            return parsed_entity_data[LAST_SEEN_FIELD].astimezone(seen_cutoff.tzinfo) < seen_cutoff
        return False

    @staticmethod
    def __is_entity_old_by_last_fetched(parsed_entity, fetched_cutoff: date):
        if not fetched_cutoff:
            return False
        if 'accurate_for_datetime' in parsed_entity:
            return parsed_entity['accurate_for_datetime'].astimezone(fetched_cutoff.tzinfo) < fetched_cutoff
        return False

    def _is_adapter_old_by_last_seen(self, adapter_device, device_age_cutoff=None):
        seen_cutoff = device_age_cutoff or self.__device_time_cutoff()[0]
        return self.__is_entity_old_by_last_seen(adapter_device, seen_cutoff)

    def __extract_old_entities_from_axonius_device(self, axonius_device, entity_age_cutoff: Tuple[date, date]) \
            -> Iterable[Tuple[str, str]]:
        """
        Finds all entities that are old in an axonius device
        """
        for adapter in axonius_device['adapters']:
            if adapter[PLUGIN_NAME] == self.plugin_name:
                if self.__is_old_entity(adapter, entity_age_cutoff) or adapter.get('pending_delete') is True:
                    yield adapter[PLUGIN_UNIQUE_NAME], adapter['data']['id']

    def _remove_big_keys(self, key_to_check, entity_id):
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
            key_to_check = {key: self._remove_big_keys(value, entity_id) for key, value in key_to_check.items()}

        if type(key_to_check) == list:
            key_to_check = [self._remove_big_keys(val, entity_id) for val in key_to_check]

        # Checking if the key is small enough after the filtering big sub-keys
        if sys.getsizeof(key_to_check) < 1e5:  # Key smaller than ~100kb
            # Key is smaller now, we can return it
            return key_to_check
        else:
            # Data type not recognized or can't filter key, deleting the too big key
            logger.warning(f"Found too big key on entity (Device/User) {entity_id}. Deleting")
            return {'AXON_TOO_BIG_VALUE': sys.getsizeof(key_to_check)}

    def _parse_devices_raw_data_hook(self, raw_devices):
        """
        :param raw_devices: raw devices as fetched by adapter
        :return: iterator of processed raw device entries
        """
        skipped_count = 0
        last_seen_cutoff, _ = self.__device_time_cutoff()
        devices_ids = []
        should_check_for_unique_ids = self.plugin_subtype == adapter_consts.DEVICE_ADAPTER_PLUGIN_SUBTYPE

        for parsed_device in self._parse_raw_data(raw_devices):
            assert isinstance(parsed_device, DeviceAdapter)

            # All scanners should have this automatically
            if self.plugin_subtype == adapter_consts.SCANNER_ADAPTER_PLUGIN_SUBTYPE:
                parsed_device.scanner = True

            if should_check_for_unique_ids:
                parsed_device_id = parsed_device.id  # we must have an id (its definitely not a scanner)
                if parsed_device_id in devices_ids:
                    logger.error(f"Error! device with id {parsed_device_id} already yielded! skipping")
                    continue
                devices_ids.append(parsed_device_id)

            parsed_device = parsed_device.to_dict()
            parsed_device = self._remove_big_keys(parsed_device, parsed_device.get('id', 'unidentified device'))
            if self._is_adapter_old_by_last_seen(parsed_device, last_seen_cutoff):
                skipped_count += 1
                continue

            yield parsed_device

        if skipped_count > 0:
            logger.info(f"Skipped {skipped_count} old devices")
        else:
            logger.warning("No old devices filtered (did you choose ttl period on the config file?)")

        self._save_field_names_to_db(EntityType.Devices)

    @stoppable
    def _try_query_data_by_client(self, client_id, entity_type: EntityType, use_cache=True):
        """
        Try querying data for given client. If fails, try reconnecting to client.
        If successful, try querying data with new connection to the original client, up to 3 times.

        This is an attempt to resolve problems with fetching data that may be caused by an outdated connection
        or to discover a real problem fetching devices, despite a working connection.

        :return: Raw and parsed data list if fetched successfully, whether immediately or with fresh connection
        :raises Exception: If client connection or client data query errored 3 times
        """

        def _update_client_status(status, error_msg=None):
            """
            Update client document matching given match object with given status, to indicate method's result

            :param client_id: Mongo ObjectId
            :param status: String representing current status
            :return:
            """
            with self._clients_lock:
                if error_msg:
                    result = clients_collection.update_one({'client_id': client_id},
                                                           {'$set': {'status': status, 'error': error_msg}})
                else:
                    result = clients_collection.update_one({'client_id': client_id}, {'$set': {'status': status}})

                if not result or result.matched_count != 1:
                    raise adapter_exceptions.CredentialErrorException(
                        f"Could not update client {client_id} with status {status}")

        clients_collection = self._get_collection('clients')
        try:
            if entity_type == EntityType.Devices:
                raw_data = self._query_devices_by_client(client_id, self._clients[client_id])
                parsed_data = self._parse_devices_raw_data_hook(raw_data)
            elif entity_type == EntityType.Users:
                raw_data = self._query_users_by_client(client_id, self._clients[client_id])
                parsed_data = self._parse_users_raw_data_hook(raw_data)
            else:
                raise ValueError(f"expected {entity_type} to be devices/users.")
        except Exception as e:
            with self._clients_lock:
                current_client = clients_collection.find_one({'client_id': client_id})
                if not current_client or not current_client.get("client_config"):
                    # No credentials to attempt reconnection
                    raise adapter_exceptions.CredentialErrorException(
                        "No credentials found for client {0}. Reason: {1}".format(client_id, str(e)))
            try:
                with self._clients_lock:
                    self._clients[client_id] = self._connect_client(current_client["client_config"])
            except Exception as e2:
                # No connection to attempt querying
                self.create_notification("Connection error to client {0}.".format(client_id), str(e2))
                logger.exception(
                    "Problem establishing connection for client {0}. Reason: {1}".format(client_id, str(e2)))
                _update_client_status("error", str(e2))
                raise
            else:
                try:
                    if entity_type == EntityType.Devices:
                        raw_data = self._query_devices_by_client(client_id, self._clients[client_id])
                        parsed_data = self._parse_devices_raw_data_hook(raw_data)
                    elif entity_type == EntityType.Users:
                        raw_data = self._query_users_by_client(client_id, self._clients[client_id])
                        parsed_data = self._parse_users_raw_data_hook(raw_data)
                    else:
                        raise ValueError(f"expected {entity_type} to be devices/users.")
                except Exception as e3:
                    # No devices despite a working connection
                    logger.exception(f"Problem querying {entity_type} for client {client_id}")
                    _update_client_status("error", str(e3))
                    raise
        _update_client_status("success", '')
        return [], parsed_data  # AD-HOC: Not returning any raw values

    def _query_data(self, entity_type: EntityType) -> Iterable[Tuple[Any, Dict[str, Any]]]:
        """
        Synchronously returns all available data types (devices/users) from all clients.
        """
        with self._clients_lock:
            if len(self._clients) == 0:
                logger.info(f"{self.plugin_unique_name}: Trying to fetch devices but no clients found")
                return
            clients = self._clients.copy()

        # Running query on each device
        for client_name in clients:
            try:
                raw_data, parsed_data = self._try_query_data_by_client(client_name, entity_type)
            except adapter_exceptions.CredentialErrorException as e:
                logger.warning(f"Credentials error for {client_name} on {self.plugin_unique_name}: {repr(e)}")
                self.create_notification(f"Credentials error for {client_name} on {self.plugin_unique_name}", repr(e))
                raise
            except adapter_exceptions.AdapterException as e:
                logger.exception(f"Error for {client_name} on {self.plugin_unique_name}: {repr(e)}")
                self.create_notification(f"Error for {client_name} on {self.plugin_unique_name}", repr(e))
                raise
            except Exception as e:
                logger.exception(f"Unknown error for {client_name} on {self.plugin_unique_name}: {repr(e)}")
                raise
            else:
                data_list = {'raw': raw_data,
                             'parsed': parsed_data}

                yield (client_name, data_list)

    @abstractmethod
    def _clients_schema(self):
        """
        To be implemented by inheritors
        Represents the set of keys the plugin expects from clients config

        :return: JSON Schema to, check out https://jsonschema.net/#/editor
        """
        pass

    def _parse_raw_data(self, devices_raw_data) -> Iterable[DeviceAdapter]:
        """
        To be implemented by inheritors
        Will convert 'raw data' of one device (as the inheritor pleases to refer to it) to 'parsed'

        :param devices_raw_data: raw data as received by /devices/client, i.e. without the client->data association
        :return: parsed data as iterable Device collection
        """
        return []

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
        raise adapter_exceptions.AdapterException('Not Supported')

    def _get_clients_config(self):
        """Returning the data inside 'clients' Collection on <plugin_unique_name> db.
        """
        return self._get_collection('clients').find()

    def _update_clients_schema_in_db(self, schema):
        """
        Every adapter has to update the DB about the scheme it expects for its clients.
        This logic is ran when the adapter starts
        :return:
        """
        with self._get_db_connection() as db_connection:
            collection = db_connection[self.plugin_unique_name]['adapter_schema']
            collection.replace_one(filter={'adapter_name': self.plugin_unique_name,
                                           'adapter_version': self.version},
                                   replacement={
                                       'adapter_name': self.plugin_unique_name,
                                       'adapter_version': self.version,
                                       'schema': schema},
                                   upsert=True)

    def _create_axonius_entity(self, client_name, data, entity_type: EntityType):
        """
        See doc for super class
        """
        parsed_to_insert = super()._create_axonius_entity(client_name, data, entity_type)
        if entity_type == EntityType.Devices:
            parsed_to_insert['adapter_properties'] = [x.name for x in self.adapter_properties()]
        return parsed_to_insert

    @property
    def plugin_type(self):
        return adapter_consts.ADAPTER_PLUGIN_TYPE

    @property
    def plugin_subtype(self):
        return adapter_consts.DEVICE_ADAPTER_PLUGIN_SUBTYPE

    def __device_time_cutoff(self) -> Tuple[date, date]:
        """
        Gets a cutoff date (last_seen, last_fetched) that represents the oldest a device can be
        until it is considered "old"
        """
        now = datetime.now(timezone.utc)
        return (now - self._last_seen_timedelta if self._last_seen_timedelta else None,
                now - self._last_fetched_timedelta if self._last_fetched_timedelta else None)

    def __user_time_cutoff(self) -> Tuple[date, date]:
        """
        Gets a cutoff date (last_seen, last_fetched) that represents the oldest a device can be
        until it is considered "old"
        """
        now = datetime.now(timezone.utc)
        return (now - self.__user_last_seen_timedelta if self.__user_last_seen_timedelta else None,
                now - self.__user_last_fetched_timedelta if self.__user_last_fetched_timedelta else None)

    def populate_register_doc(self, register_doc, config_file_path):
        config = AdapterConfig(config_file_path)

    @classmethod
    @abstractmethod
    def adapter_properties(cls) -> List[AdapterProperty]:
        """
        Returns a list of all properties of the adapter, they will be displayed in GUI
        """
        pass

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            "items": [
                {
                    "name": "last_seen_threshold_hours",
                    "title": "Old device last seen field threshold hours",
                    "type": "number"
                },
                {
                    "name": "last_fetched_threshold_hours",
                    "title": "Old device last fetched threshold hours",
                    "type": "number"
                },
                {
                    "name": "user_last_seen_threshold_hours",
                    "title": "Old user last seen field threshold hours",
                    "type": "number"
                },
                {
                    "name": "user_last_fetched_threshold_hours",
                    "title": "Old user last fetched threshold hours",
                    "type": "number",
                },
                {
                    "name": "minimum_time_until_next_fetch",
                    "title": "Minimum time until next fetch entities",
                    "type": "number",
                }
            ],
            "required": [
            ],
            "pretty_name": "Adapter Configuration",
            "type": "array"
        }

    @classmethod
    def _db_config_default(cls):
        return {
            "last_seen_threshold_hours": cls.DEFAULT_LAST_SEEN_THRESHOLD_HOURS,
            "last_fetched_threshold_hours": cls.DEFAULT_LAST_FETCHED_THRESHOLD_HOURS,
            "user_last_seen_threshold_hours": cls.DEFAULT_USER_LAST_SEEN,
            "user_last_fetched_threshold_hours": cls.DEFAULT_USER_LAST_FETCHED,
            "minimum_time_until_next_fetch": cls.DEFAULT_MINIMUM_TIME_UNTIL_NEXT_FETCH
        }
