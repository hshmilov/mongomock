import configparser
import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime
from multiprocessing.pool import ThreadPool

import docker.models
import pymongo
import requests
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger
from axonius.consts.plugin_subtype import PluginSubtype

from axonius.utils.threading import LazyMultiLocker
from docker.models.containers import Container

from axonius.mixins.triggerable import Triggerable, RunIdentifier
from flask import jsonify, request
from passlib.utils import generate_password
from requests.exceptions import ConnectionError, ReadTimeout, Timeout
from retry.api import retry_call

from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts.plugin_consts import (NODE_ID,
                                          NODE_INIT_NAME,
                                          NODE_NAME,
                                          NODE_USER_PASSWORD,
                                          PLUGIN_UNIQUE_NAME,
                                          HEAVY_LIFTING_PLUGIN_NAME,
                                          NODE_ID_PATH,
                                          NODE_ID_ENV_VAR_NAME,
                                          PLUGIN_NAME, AXONIUS_DNS_SUFFIX)
from axonius.mixins.configurable import Configurable
from axonius.plugin_base import (VOLATILE_CONFIG_PATH, PluginBase, add_rule,
                                 return_error)
from axonius.utils.files import get_local_config_file
from axonius.utils.mongo_administration import set_mongo_parameter
from core.exceptions import PluginNotFoundError

logger = logging.getLogger(f'axonius.{__name__}')

CHUNK_SIZE = 1024
MAX_INSTANCES_OF_SAME_PLUGIN = 100
MASTER_NODE_NAME = 'Master'


class CoreService(Triggerable, PluginBase, Configurable):
    def __init__(self, **kwargs):
        """ Initialize all needed configurations
        """
        # Get local configuration
        config = configparser.ConfigParser()
        config.read(get_local_config_file(__file__))
        plugin_unique_name = config['core_specific'][PLUGIN_UNIQUE_NAME]

        temp_config = configparser.ConfigParser()
        temp_config.read(VOLATILE_CONFIG_PATH)
        try:
            api_key = temp_config['registration']['api_key']
            node_id = temp_config['registration'][NODE_ID] or os.environ.get(NODE_ID_ENV_VAR_NAME, None)
        except KeyError:
            # We should generate a new api_key and save it
            api_key = uuid.uuid4().hex
            node_id = os.environ.get(NODE_ID_ENV_VAR_NAME, None) or uuid.uuid4().hex
            temp_config['registration'] = {}
            temp_config['registration']['api_key'] = api_key
            temp_config['registration'][NODE_ID] = node_id
        with open(VOLATILE_CONFIG_PATH, 'w') as temp_config_file:
            temp_config.write(temp_config_file)
        with open(NODE_ID_PATH, 'w') as node_id_file:
            node_id_file.write(node_id)

        # In order to avoid, deletion before initialization of adapter, we add this flag
        self.did_adapter_registered = False

        # Building doc data so we won't register on PluginBase (Core doesnt need to register)
        core_data = {
            "plugin_unique_name": plugin_unique_name,
            "api_key": api_key,
            "node_id": node_id or '',
            "status": "ok"
        }

        self.online_plugins = {}

        # Initialize the base plugin (will initialize http server)
        # No registration process since we are sending core_data
        super().__init__(get_local_config_file(__file__), core_data=core_data, **kwargs)
        self.core_configs_collection.replace_one(filter={
            PLUGIN_UNIQUE_NAME: plugin_unique_name,
        }, replacement={**core_data, **{
            PLUGIN_NAME: plugin_unique_name,
            'plugin_subtype': PluginSubtype.NotRunning.value
        }}, upsert=True)

        # Get the needed docker socket
        self.__docker_client = docker.from_env()

        weave_container = self.__docker_client.containers.list(all=True,
                                                               filters={
                                                                   'name': 'weave'
                                                               })
        if weave_container:
            # we're under weave
            logger.info('Running under weave')
            self.__docker_axonius_network = None

            # This is not used anymore
            self.__docker_client = None

        else:
            self.__docker_axonius_network: docker.models.networks.Network = \
                self.__docker_client.networks.list(names='axonius')
            if self.__docker_axonius_network:
                # if we found a network named 'axonius' it implies we're running without weave, so we have
                # to manually set up every container to be under the axonius network
                # This is the case for dev machines
                self.__docker_axonius_network = self.__docker_axonius_network[0]
                logger.info('Running under docker')
            else:
                # not running under weave, and still no 'axonius' network
                logger.error('No weave and no axonius network. AOD might have issues')
                self.__docker_axonius_network = None
                self.__docker_client = None

        self.adapters_lock = threading.Lock()

        # Create plugin cleaner thread
        executors = {'default': ThreadPoolExecutor(1)}
        self.cleaner_thread = LoggedBackgroundScheduler(executors=executors)
        self.cleaner_thread.add_job(func=self.clean_offline_plugins,
                                    trigger=IntervalTrigger(seconds=60 * 2),
                                    next_run_time=datetime.now(),
                                    name='clean_offline_plugins',
                                    id='clean_offline_plugins',
                                    max_instances=1,
                                    coalesce=True)
        self.cleaner_thread.start()

        # pool for global config updates
        self.__config_updater_pool = ThreadPool(30)

        connection = self._get_db_connection()
        # this makes sure we're consistent on the version we assume and run on
        connection['admin'].command({
            'setFeatureCompatibilityVersion': '4.0'
        })

        # this command sets mongo's query space to be larger default
        # which allows for faster queries using the RAM alone
        # set to max size mongo allows
        set_mongo_parameter(connection, 'internalQueryExecMaxBlockingSortBytes',
                            2 * 1024 * 1024 * 1024 - 1)

        # we want slightly more time for transactions
        set_mongo_parameter(connection, 'maxTransactionLockRequestTimeoutMillis', 20)

        # Deleting by name "Master", would delete the first "Master" appearance including if the real master name
        # was changed and a node was named "Master". The reason for this is because of a node_id and master
        # registration on export and deletion of volume on first boot.
        self._delete_node_name(MASTER_NODE_NAME)
        self._set_node_name(self.node_id, MASTER_NODE_NAME)

        self.__lazy_locker = LazyMultiLocker()

    def clean_offline_plugins(self):
        """Thread for cleaning offline plugin.

        This function will run forever as a thread. It will remove from the online list plugins that do not appear
        To be online anymore.
        Currently the sample rate is determined to be 20 seconds
        """
        try:
            with self.adapters_lock:
                # Copying the list so we wont have to lock for the whole cleaning process
                temp_list = self.online_plugins.copy()

            delete_list = []
            for plugin_unique_name in temp_list:
                plugin_is_debug = temp_list[plugin_unique_name].get('is_debug', False)
                should_delete = False
                if not plugin_is_debug:
                    for i in range(4):
                        should_delete = not self._check_plugin_online(plugin_unique_name)
                        if should_delete is False:
                            break
                if should_delete:
                    if self.did_adapter_registered:
                        # We need to wait a bit and then try to check if plugin exists again
                        self.did_adapter_registered = False
                        break
                    else:
                        # The plugin didnt answer, removing the plugin subscription
                        delete_list.append((plugin_unique_name, temp_list[plugin_unique_name]))

            with self.adapters_lock:
                for delete_key, delete_value in delete_list:
                    delete_candidate = self.online_plugins.get(delete_key)
                    if delete_candidate is delete_value:
                        logger.info("Plugin {0} didn't answer, deleting "
                                    "from online plugins list".format(delete_candidate))
                        del self.online_plugins[delete_key]
                        self.core_configs_collection.update_one({
                            PLUGIN_UNIQUE_NAME: delete_key
                        }, {
                            '$set': {
                                'status': 'down'
                            }
                        })

        except Exception as e:
            logger.critical("Cleaning plugins had an error. message: {0}", str(e))

    @add_rule('nodes/tags/<node_id>', methods=['GET', 'DELETE', 'POST'], should_authenticate=False)
    def node_tags(self, node_id):
        if request.method == 'GET':
            return jsonify(
                self._get_collection('nodes_metadata').find_one({'node_id': node_id}, projection={'_id': 0, 'tags': 1}))
        elif request.method == 'POST':
            data = self.get_request_data_as_object()
            self._get_collection('nodes_metadata').find_one_and_update({'node_id': node_id}, {
                '$set': {f'tags.{data["tags"]}': data["tags"]}}, upsert=True)
            return ''
        elif request.method == 'DELETE':
            data = self.get_request_data_as_object()
            self._get_collection('nodes_metadata').find_one_and_update({'node_id': node_id}, {
                '$unset': {f'tags.{data["tags"]}': data["tags"]}})
            return ''

    @add_rule('nodes/last_seen/<node_id>', methods=['GET'], should_authenticate=False)
    def get_node_status(self, node_id):
        x = self.core_configs_collection.find_one(filter={'node_id': node_id},
                                                  sort=[('last_seen', pymongo.DESCENDING)])
        return jsonify({
            'last_seen': x['last_seen']
        })

    @add_rule('find_plugin_unique_name/nodes/<node_id>/plugins/<plugin_name>', methods=['GET'],
              should_authenticate=False)
    def find_plugin_unique_name(self, node_id, plugin_name):
        if node_id != 'None':
            # Case of get plugin_unique_name (by node_id and plugin_name).
            config = self._get_config(node_id=node_id, plugin_name=plugin_name)
            if config is not None:
                return jsonify({'plugin_unique_name': config.get('plugin_unique_name')})
        else:
            # Case of get all plugin_unique_names (with the same plugin_name).
            config = self.core_configs_collection.find({
                PLUGIN_NAME: plugin_name
            }).sort('last_seen', pymongo.DESCENDING)
            return jsonify([current_plugin['plugin_unique_name'] for current_plugin in config])

        return ''

    @add_rule('node/<node_id>', methods=['POST', 'GET'], should_authenticate=False)
    def node_metadata(self, node_id):
        data = self.get_request_data_as_object()
        if request.method == 'POST':
            key = data.get('key', NODE_NAME)
            assert key in ['hostname', NODE_NAME, 'ips']
            self._set_node_metadata(node_id, key, data['value'])
            return ''
        else:
            # A node with this ID isn't registered (No adapters with that node_id).
            if self._get_collection("configs").find_one({NODE_ID: node_id}) is None:
                return return_error('Node is not connected.', 404)

            node_metadata = self._get_collection('nodes_metadata').find_one({'node_id': node_id})
            if node_metadata is None or node_metadata.get(NODE_USER_PASSWORD) is None:
                password = generate_password(32)
                self._set_node_metadata(node_id, NODE_USER_PASSWORD, password)
            else:
                password = node_metadata.get(NODE_USER_PASSWORD)

            return password

    def _set_node_metadata(self, node_id, key, value):
        self._get_collection('nodes_metadata').find_one_and_update({NODE_ID: node_id}, {
            '$set': {key: value}}, upsert=True)

    def _delete_node_name(self, node_name):
        self._get_collection('nodes_metadata').find_one_and_delete({NODE_NAME: node_name})

    def _set_node_name(self, node_id, node_name):
        self._set_node_metadata(node_id, NODE_NAME, node_name)

    def _get_config_by_plugin_unique_name(self, plugin_unique_name: str) -> dict:
        """
        Finds the plugin by the plugin unique name in the DB
        """
        return self.core_configs_collection.find_one({
            PLUGIN_UNIQUE_NAME: plugin_unique_name
        })

    def _get_config(self, **kwargs):
        # A common thing to do is to request a specific adapter on a specific node. But on some nodes, there are
        # multiple configurations of the same adapter due to bugs or or due to hard reset. this is why we return
        # the last one that communicated.
        result = list(self.core_configs_collection.find(kwargs).sort('last_seen', pymongo.DESCENDING))
        if len(result) > 1:
            logger.warning(f'Warning, found more than 1 unique name for a requested adapter: {result}')
        return result[0] if result else None

    @staticmethod
    def _request_plugin(resource, plugin_unique_name, method='get', **kwargs):
        url = f'https://{plugin_unique_name}.{AXONIUS_DNS_SUFFIX}/api/{resource}'
        return requests.request(method=method, url=url, timeout=10, **kwargs)

    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        """
        Job name is the start:plugin_unique_name or stop:plugin_unique_name
        """
        parsed_path = job_name.split(':')
        if len(parsed_path) != 2:
            raise RuntimeError('Wrong job_name')
        operation_type, plugin_unique_name = parsed_path
        if operation_type not in ['start', 'stop']:
            raise RuntimeError('Wrong job_name')
        del parsed_path

        with self.__lazy_locker.get_lock([plugin_unique_name]):
            plugin_entity = self.core_configs_collection.find_one({
                PLUGIN_UNIQUE_NAME: plugin_unique_name
            }, projection={
                '_id': True,
                PLUGIN_NAME: True,
                PLUGIN_UNIQUE_NAME: True,
                NODE_ID: True
            })
            if not plugin_entity:
                raise RuntimeError('Plugin not found')

            if self.__docker_axonius_network is not None:
                # Currently, AOD is disabled on dev machines :(
                return ''
                return self.__handle_plugin_up_down_dev(operation_type, plugin_entity)

            relevant_instance_control = self.core_configs_collection.find_one({
                PLUGIN_NAME: 'instance_control',
                NODE_ID: plugin_entity[NODE_ID]
            })
            if not relevant_instance_control:
                raise RuntimeError(f'Instance control for node {plugin_entity[NODE_ID]} '
                                   f'for plugin {plugin_unique_name} not found')
            response = self._trigger_remote_plugin(relevant_instance_control[PLUGIN_UNIQUE_NAME],
                                                   f'{operation_type}:{plugin_entity[PLUGIN_NAME]}',
                                                   reschedulable=False)
            response.raise_for_status()
            self.core_configs_collection.update_one({
                PLUGIN_UNIQUE_NAME: plugin_unique_name
            }, {
                '$set': {
                    'status': 'up' if operation_type == 'start' else 'down'
                }
            })
            return response.text

    def __handle_plugin_up_down_dev(self, operation_type: str, plugin_entity: dict):
        """
        Handles raising or stopping plugins when running under docker
        :param operation_type: 'up' or 'down'
        :param plugin_entity: the plugin entity from the DB
        :return: response
        """
        plugin_unique_name = plugin_entity[PLUGIN_UNIQUE_NAME]
        name_to_find = plugin_entity[PLUGIN_NAME].replace('_', '-')
        container = [x
                     for x
                     in self.__docker_client.containers.list(all=True,
                                                             filters={
                                                                 'name': name_to_find
                                                             }) if x.name == name_to_find]
        if len(container) != 1:
            logger.exception(', '.join(x.name for x in container))
            raise RuntimeError(
                f'Found a weird amount of containers {len(container)} for {plugin_entity[PLUGIN_NAME]}')
        container: Container = container[0]
        if operation_type == 'start':
            self.__raise_adapter_from_docker(plugin_unique_name, container)
            status = 'up'
        else:
            # assumed 'stop':
            self.__stop_adapter_from_docker(container)
            status = 'down'
            self.online_plugins.pop(plugin_unique_name, None)

        self.core_configs_collection.update_one({
            '_id': plugin_entity['_id']
        }, {
            '$set': {
                'status': status
            }
        })

        if status == 'up':
            self.online_plugins[plugin_unique_name] = self._get_config_by_plugin_unique_name(plugin_unique_name)
        return ''

    def __raise_adapter_from_docker(self, plugin_unique_name: str, container: Container) -> None:
        """
        Raises an adapter using the local docker instance
        """
        container.start()
        for i in range(30):  # retries
            if json.loads(next(container.stats()))['pids_stats'].get('current'):
                break
            time.sleep(1)
        else:
            # reached the end of the loop
            container.stop()
            raise RuntimeError('Failed waiting for docker to raise!')

        try:
            self.__docker_axonius_network.disconnect(container)
        except Exception:
            # Usually means that the docker is not connected to the network
            pass

        # Wait until the plugin is actually up
        def is_online():
            fqdn = f'{plugin_unique_name}.{AXONIUS_DNS_SUFFIX}'
            logger.info(f'Connecting to {fqdn}')
            self.__docker_axonius_network.connect(container, aliases=[fqdn])
            assert self._check_plugin_online(plugin_unique_name)

        retry_call(is_online, delay=1, tries=30)

    def __stop_adapter_from_docker(self, container: Container):
        """
        Stops an adapter using docker
        """
        container.stop()
        self.__docker_axonius_network.disconnect(container)

    def _check_plugin_online(self, plugin_unique_name):
        """ Function for checking if a plugin is online.

        May block for a maximum of 3 seconds.

        :param str plugin_unique_name: The name of the plugin

        :returns: True if the plugin is online, False otherwise
        """
        try:
            # Trying a simple GET request for the version
            check_response = self._request_plugin('version', plugin_unique_name)

            if check_response.status_code == 200:
                responder_name = check_response.json()[PLUGIN_UNIQUE_NAME]
                if responder_name == plugin_unique_name:
                    return True
                else:
                    logger.info(f"Bad plugin name while checking plugin online. "
                                f"Expected: {plugin_unique_name}, got: {responder_name}")
                    return False
            else:
                return False

        except (ConnectionError, ReadTimeout, Timeout, PluginNotFoundError) as e:
            logger.info("Got exception {} while trying to contact {}".format(e, plugin_unique_name))
            return False

        except Exception as e:
            logger.exception("Got unhandled exception {} while trying to contact {}".format(e, plugin_unique_name))
            return False

    def _check_registered_thread(self, *args, **kwargs):
        return  # No need to check on core itself

    @add_rule("register", methods=['POST', 'GET'], should_authenticate=False)
    def register(self):
        """Calling this function from the REST API will start the registration process.

        Accepts:
            GET - If the request is without the api-key in its headers than this function will return a list
                  Of the registered plugins. If the api-key is in the headers, and the plugin_unique_name is a parameter
                  Of the request. Then the function will return if this plugin is currently registered.
            POST - For registering. Should send the following data on the page:
                   {"plugin_name": <plugin_name>, "plugin_unique_name"(Optional):<plugin_unique_name>}
        """
        if self.get_method() == 'GET':
            api_key = self.get_request_header('x-api-key')
            unique_name = request.args.get('unique_name')
            if not api_key:
                if not unique_name:
                    # No api_key, Returning the current online plugins. This will be used by the aggregator
                    # To find out which adapters are available
                    return jsonify({
                        adapter[PLUGIN_UNIQUE_NAME]: adapter
                        for adapter
                        in self.core_configs_collection.find({
                            PLUGIN_UNIQUE_NAME: {
                                '$ne': self.plugin_unique_name  # hide core from results
                            }
                        }, projection={
                            '_id': False,
                            NODE_ID: True,
                            PLUGIN_NAME: True,
                            PLUGIN_UNIQUE_NAME: True,
                            'plugin_subtype': True,
                            'plugin_type': True,
                            'supported_features': True
                        })
                    })
                else:
                    return 'OK'
            else:
                # This is a registered check, we should get the plugin name (a parameter) and tell if it's
                # already registered
                plugin = self.core_configs_collection.find_one({
                    PLUGIN_UNIQUE_NAME: unique_name
                })
                if plugin:
                    if api_key == plugin['api_key']:
                        plugin['last_seen'] = datetime.utcnow()
                        self.core_configs_collection.update_one({
                            PLUGIN_UNIQUE_NAME: unique_name
                        }, {
                            '$set': {
                                'last_seen': plugin['last_seen']
                            }
                        })
                        return 'OK'
                    else:
                        # Probably a new node_connection.
                        return return_error('Non matching api_key', 409)
                elif unique_name == self.plugin_name:
                    return 'OK'
                # If we reached here than plugin is not registered, returning error
                return return_error('Plugin not registered', 404)

        # method == POST
        data = self.get_request_data_as_object()

        try:
            plugin_name = data['plugin_name']
            plugin_type = data['plugin_type']
            plugin_subtype = data['plugin_subtype']
            supported_features = data['supported_features']
            plugin_is_debug = data.get('is_debug', False)
            node_id = data[NODE_ID]
            node_init_name = data.get(NODE_INIT_NAME)
        except KeyError:
            logger.exception('Data is missing on register POST request. Registration Failed!')
            logger.info(f'data: {data}')
            raise

        logger.info(f"Got registration request : {data} from {request.remote_addr}")

        with self.adapters_lock:
            relevant_doc = None

            plugin_unique_name = data.get(PLUGIN_UNIQUE_NAME)

            if plugin_unique_name:
                # Plugin is trying to register with it's own name
                logger.info("Plugin request to register with it's own name: {0}".format(plugin_unique_name))

                # Trying to get the configuration of the current plugin
                relevant_doc = self._get_config_by_plugin_unique_name(plugin_unique_name)

                # plugin_unique_name and node_id match an existing plugin
                if relevant_doc:
                    if node_id != relevant_doc[NODE_ID]:
                        # new plugin from remote server.
                        relevant_doc = None
                        plugin_unique_name = self._generate_unique_name(plugin_name)
                        if node_init_name is not None:
                            # Setting node_init_name
                            logger.info(f'Setting new node name: {node_init_name}')
                            self._set_node_name(node_id, node_init_name)
                    else:
                        # Checking if this plugin already registered
                        if self.core_configs_collection.count_documents({
                            PLUGIN_UNIQUE_NAME: plugin_unique_name
                        }, limit=1):
                            # HEAVY_LIFTING_PLUGIN_NAME is allowed to have multiples, don't touch that
                            if plugin_unique_name != HEAVY_LIFTING_PLUGIN_NAME:
                                logger.warning(
                                    f"Already have instance of {plugin_unique_name}, re-registration detected")

                            self.online_plugins[plugin_unique_name] = relevant_doc
                            return jsonify(relevant_doc)
            else:
                plugin_unique_name = self._generate_unique_name(plugin_name)

            if not relevant_doc:
                # Create a new plugin line
                plugin_user, plugin_password = self.db_user, self.db_password
                doc = {
                    PLUGIN_UNIQUE_NAME: plugin_unique_name,
                    'plugin_name': plugin_name,
                    'plugin_type': plugin_type,
                    'plugin_subtype': plugin_subtype,
                    'supported_features': supported_features,
                    'api_key': uuid.uuid4().hex,
                    'db_addr': self.db_host,
                    'db_user': plugin_user,
                    'db_password': plugin_password,
                    'last_seen': datetime.utcnow(),
                    'status': 'up',
                    'hidden': False,
                    NODE_ID: node_id
                }

                if plugin_is_debug:
                    doc['is_debug'] = True
            else:
                # This is an existing plugin, we should update its data on the db (data that the plugin can change)
                doc = relevant_doc.copy()
                doc['plugin_subtype'] = plugin_subtype
                doc['plugin_type'] = plugin_type
                doc['supported_features'] = supported_features
                doc['last_seen'] = datetime.utcnow()
                doc['status'] = 'up'
                doc[NODE_ID] = node_id

            # Setting a new doc with the wanted configuration
            self.core_configs_collection.replace_one(filter={PLUGIN_UNIQUE_NAME: doc[PLUGIN_UNIQUE_NAME]},
                                                     replacement=doc,
                                                     upsert=True)

            # This time it must work since we entered the needed document
            relevant_doc = self._get_config_by_plugin_unique_name(plugin_unique_name)

            self.online_plugins[plugin_unique_name] = relevant_doc
            del relevant_doc['_id']  # We dont need the '_id' field
            self.did_adapter_registered = True
            logger.info("Plugin {0} registered successfully!".format(relevant_doc[PLUGIN_UNIQUE_NAME]))
            logger.debug(relevant_doc)
            return jsonify(relevant_doc)

    def _generate_unique_name(self, plugin_name):
        # New plugin. First, start with a name with no unique identifier. Then, continue to
        # ongoing numbers.
        for unique_name_suffix in [f"_{i}" for i in range(MAX_INSTANCES_OF_SAME_PLUGIN)]:
            # Try generating a unique name
            # TODO: Check that this name is also not in the DB
            plugin_unique_name = f'{plugin_name}{unique_name_suffix}'
            if not self._get_config_by_plugin_unique_name(plugin_unique_name):
                break
        else:
            # Looped through the whole for and couldn't hit the break..
            raise ValueError(f'Error, couldn\'t find a unique name for plugin {plugin_name}!')
        logger.info(f'Generated new plugin unique name for plugin {plugin_name}: {plugin_unique_name}')
        return plugin_unique_name

    def _on_config_update(self, config):
        logger.info(f"Loading core config: {config}")

        def update_plugin(plugin_name):
            try:
                self._request_plugin('update_config', plugin_name, method='post')
            except Exception as e:
                logger.exception(f"Failed to update config on {e} {plugin_name}")

        online_plugins = self.online_plugins.keys()
        if online_plugins:
            self.__config_updater_pool.map_async(update_plugin, online_plugins)

    @classmethod
    def _db_config_schema(cls) -> dict:
        return PluginBase.global_settings_schema()

    @classmethod
    def _db_config_default(cls):
        return PluginBase.global_settings_defaults()
