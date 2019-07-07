import configparser
import logging
import os
import threading
import uuid
from datetime import datetime
from multiprocessing.pool import ThreadPool

import pymongo
import requests
import uritools
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger
from flask import jsonify, request
from passlib.utils import generate_password
from pymongo import ReturnDocument
from requests.exceptions import ConnectionError, ReadTimeout, Timeout

from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts.plugin_consts import (NODE_ID,
                                          NODE_INIT_NAME,
                                          NODE_NAME,
                                          NODE_USER_PASSWORD,
                                          PLUGIN_UNIQUE_NAME,
                                          HEAVY_LIFTING_PLUGIN_NAME,
                                          NODE_ID_PATH,
                                          NODE_ID_ENV_VAR_NAME, PLUGIN_NAME)
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


class CoreService(PluginBase, Configurable):
    def __init__(self, **kwargs):
        """ Initialize all needed configurations
        """
        # Get local configuration
        config = configparser.ConfigParser()
        config.read(get_local_config_file(__file__))
        plugin_unique_name = config['core_specific'][PLUGIN_UNIQUE_NAME]
        db_addr = config['core_specific']['db_addr']
        db_user = config['core_specific']['db_user']
        db_password = config['core_specific']['db_password']

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
        core_data = {"plugin_unique_name": plugin_unique_name,
                     "db_addr": db_addr,
                     "db_user": db_user,
                     "db_password": db_password,
                     "api_key": api_key,
                     "node_id": node_id or '',
                     "status": "ok"}

        self.online_plugins = {}

        # Initialize the base plugin (will initialize http server)
        # No registration process since we are sending core_data
        super().__init__(get_local_config_file(__file__), core_data=core_data, **kwargs)

        # Get the needed docker socket
        # self.docker_client = docker.APIClient(base_url='unix://var/run/docker.sock')

        self._setup_images()  # TODO: Check if we should move it to another function
        # (so we wont get register request before initializing the server here)

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
                with self.adapters_lock:
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

        except Exception as e:
            logger.critical("Cleaning plugins had an error. message: {0}", str(e))

    def _setup_images(self):
        """ Setting up needed images
        """
        # TODO: Implement this
        pass

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
        return jsonify({'last_seen': self._get_collection('configs').find_one(filter={'node_id': node_id}, sort=[
            ('last_seen', pymongo.DESCENDING)])['last_seen']})

    @add_rule('find_plugin_unique_name/nodes/<node_id>/plugins/<plugin_name>', methods=['GET'],
              should_authenticate=False)
    def find_plugin_unique_name(self, **kwargs):
        if kwargs.get(NODE_ID) != 'None':
            # Case of get plugin_unique_name (by node_id and plugin_name).
            config = self._get_config(**kwargs)
            if config is not None:
                return jsonify({'plugin_unique_name': config.get('plugin_unique_name')})
        else:
            # Case of get all plugin_unique_names (with the same plugin_name).
            kwargs.pop(NODE_ID)
            config = self._get_config(**kwargs)
            if config is not None:
                return jsonify([current_plugin['plugin_unique_name'] for current_plugin in config])

        return ''

    @add_rule('node/<node_id>', methods=['POST', 'GET'], should_authenticate=False)
    def node_metadata(self, node_id):
        data = self.get_request_data_as_object()
        if request.method == 'POST':
            self._set_node_name(node_id, data['node_name'])
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
            '$set': {key: value}}, upsert=True, return_document=ReturnDocument.AFTER)

    def _delete_node_name(self, node_name):
        self._get_collection('nodes_metadata').find_one_and_delete({NODE_NAME: node_name})

    def _set_node_name(self, node_id, node_name):
        self._set_node_metadata(node_id, NODE_NAME, node_name)

    def _get_config(self, **kwargs):
        # Checking to see if we're searching by plugin_name alone
        if kwargs.get('plugin_name') is not None and kwargs.get('plugin_unique_name') is None and kwargs.get(
                NODE_ID) is None:
            return self._get_collection('configs').find(kwargs)

        # A common thing to do is to request a specific adapter on a specific node. But on some nodes, there are
        # multiple configurations of the same adapter due to bugs or or due to hard reset. this is why we return
        # the last one that communicated.
        result = list(self._get_collection('configs').find(kwargs).sort('last_seen', pymongo.DESCENDING))
        if len(result) > 1:
            logger.warning(f'Warning, found more than 1 unique name for a requested adapter: {result}')
        return result[0] if result else None

    def _request_plugin(self, resource, plugin_unique_name, method='get', **kwargs):
        data = self._translate_url(plugin_unique_name + f"/{resource}")
        final_url = uritools.uricompose(scheme='https', host=data['plugin_ip'], port=data['plugin_port'],
                                        path=data['path'])

        return requests.request(method=method, url=final_url, timeout=10, **kwargs)

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
                    online_devices = self._get_online_plugins()
                    return jsonify(online_devices)
                else:
                    return 'OK'
            else:
                # This is a registered check, we should get the plugin name (a parameter) and tell if its
                # In our online list
                if unique_name in self.online_plugins:
                    plugin = self.online_plugins[unique_name]
                    if api_key == plugin['api_key']:
                        plugin['last_seen'] = datetime.utcnow()
                        self._get_collection('configs').update_one({PLUGIN_UNIQUE_NAME: unique_name},
                                                                   {'$set': {'last_seen': plugin['last_seen']}})
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
            plugin_port = data['plugin_port']
            supported_features = data['supported_features']
            plugin_is_debug = data.get('is_debug', False)
            node_id = data[NODE_ID]
            node_init_name = data.get(NODE_INIT_NAME)
        except KeyError:
            logger.exception('Data is missing on register POST request. Registration Failed!')
            logger.info(f'data: {data}')
            raise

        logger.info(f"Got registration request : {data} from {request.remote_addr}")

        with self.adapters_lock:  # Locking the adapters list, in case "register" will get called from 2 plugins
            relevant_doc = None

            plugin_unique_name = data.get(PLUGIN_UNIQUE_NAME)

            if plugin_unique_name:
                # Plugin is trying to register with his own name
                logger.info("Plugin request to register with his own name: {0}".format(plugin_unique_name))

                # Trying to get the configuration of the current plugin
                relevant_doc = self._get_config(plugin_unique_name=plugin_unique_name, node_id=node_id)

                if 'api_key' in data and relevant_doc is not None:
                    api_key = data['api_key']
                    # Checking that this plugin has the correct api key
                    if api_key != relevant_doc['api_key']:
                        if data[NODE_ID] != self.node_id:
                            # This is not the correct api key, decline registration
                            return return_error('Duplicate plugin unique name.', 409)
                        return return_error('Wrong API key', 400)
                else:
                    # TODO: prompt message to gui that an unrecognized plugin is trying to connect
                    logger.warning("Plugin {0} request to register with "
                                   "unique name but with no api key".format(plugin_unique_name))

                # Checking if this plugin already online for some reason
                if plugin_unique_name in self.online_plugins:
                    duplicated = self.online_plugins[plugin_unique_name]

                    # HEAVY_LIFTING_PLUGIN_NAME is allowed to have multiples, don't touch that
                    if plugin_unique_name == HEAVY_LIFTING_PLUGIN_NAME:
                        return jsonify(relevant_doc)

                    if request.remote_addr == duplicated['plugin_ip'] and plugin_port == duplicated['plugin_port']:
                        logger.warn("Pluging {} restarted".format(plugin_unique_name))
                        del self.online_plugins[plugin_unique_name]
                    else:
                        if node_id == duplicated['node_id']:
                            logger.warn(f"Already have instance of {plugin_unique_name}, trying to check if alive")
                            if self._check_plugin_online(plugin_unique_name):
                                # There is already a running plugin with the same name
                                logger.error("Plugin {0} trying to register but already online")
                                return return_error("Error - {0} is trying to register but already "
                                                    "online".format(plugin_unique_name), 400)
                            else:
                                # The old plugin should be deleted
                                del self.online_plugins[plugin_unique_name]
                        else:
                            # new plugin from remote server.
                            relevant_doc = None
                            plugin_unique_name = self._generate_unique_name(plugin_name)
                            if node_init_name is not None:
                                # Setting node_init_name
                                logger.info(f'Setting new node name: {node_init_name}')
                                self._set_node_name(node_id, node_init_name)

            else:
                plugin_unique_name = self._generate_unique_name(plugin_name)

            if not relevant_doc:
                # Create a new plugin line
                # TODO: Ask the gui for permission to register this new plugin
                plugin_user, plugin_password = self.db_user, self.db_password
                doc = {
                    PLUGIN_UNIQUE_NAME: plugin_unique_name,
                    'plugin_name': plugin_name,
                    'plugin_ip': request.remote_addr,
                    'plugin_port': plugin_port,
                    'plugin_type': plugin_type,
                    'plugin_subtype': plugin_subtype,
                    'supported_features': supported_features,
                    'api_key': uuid.uuid4().hex,
                    'db_addr': self.db_host,
                    'db_user': plugin_user,
                    'db_password': plugin_password,
                    'last_seen': datetime.utcnow(),
                    'status': 'ok',
                    NODE_ID: node_id
                }

                if plugin_is_debug:
                    doc['is_debug'] = True
            else:
                # This is an existing plugin, we should update its data on the db (data that the plugin can change)
                doc = relevant_doc.copy()
                doc['plugin_name'] = plugin_name
                doc['plugin_ip'] = request.remote_addr
                doc['plugin_port'] = plugin_port
                doc['plugin_subtype'] = plugin_subtype
                doc['plugin_type'] = plugin_type
                doc['supported_features'] = supported_features
                doc[NODE_ID] = node_id

            # The next section is trying to find plugins with same ip address and port. If there are such we have
            # a major problem since the core cant access both of the plugins.
            # In most cases, if there are plugins with the same IP they are probably offline (and docker just used
            # their IP for the next plugin)
            same_ip_plugins = [same_ip_name for same_ip_name, same_ip_doc in self.online_plugins.items()
                               if (same_ip_doc['plugin_ip'] == doc['plugin_ip'] and
                                   same_ip_doc['plugin_port'] == doc['plugin_port'])]

            for same_ip_plugin in same_ip_plugins:
                # If we have reached here it means that we have another registered plugin with the same IP and port
                if self._check_plugin_online(same_ip_plugin):
                    logger.error(f"Found two online plugins with same IP. "
                                 f"({same_ip_plugin}, {plugin_unique_name})")
                    return return_error(f"Already have plugin with this ip: {same_ip_plugin}")
                else:
                    # The older plugin is no longer online, removing it from the onine_plugins list
                    logger.info(f"Removing {same_ip_plugin} from online since other "
                                f"{plugin_unique_name} got registered with same ip")
                    del self.online_plugins[same_ip_plugin]

            # Setting a new doc with the wanted configuration
            collection = self._get_collection('configs')
            collection.replace_one(filter={PLUGIN_UNIQUE_NAME: doc[PLUGIN_UNIQUE_NAME]},
                                   replacement=doc,
                                   upsert=True)

            # This time it must work since we entered the needed document
            relevant_doc = self._get_config(plugin_unique_name=plugin_unique_name)

            self.online_plugins[plugin_unique_name] = relevant_doc
            del relevant_doc['_id']  # We dont need the '_id' field
            self.did_adapter_registered = True
            logger.info("Plugin {0} registered successfuly!".format(relevant_doc[PLUGIN_UNIQUE_NAME]))
            return jsonify(relevant_doc)

    def _generate_unique_name(self, plugin_name):
        # New plugin. First, start with a name with no unique identifier. Then, continue to
        # ongoing numbers.
        for unique_name_suffix in [f"_{i}" for i in range(MAX_INSTANCES_OF_SAME_PLUGIN)]:
            # Try generating a unique name
            # TODO: Check that this name is also not in the DB
            plugin_unique_name = f"{plugin_name}{unique_name_suffix}"
            if not self._get_config(
                    plugin_unique_name=plugin_unique_name) and plugin_unique_name not in self.online_plugins:
                break
        else:
            # Looped through the whole for and couldn't hit the break..
            raise ValueError(f"Error, couldn't find a unique name for plugin {plugin_name}!")
        return plugin_unique_name

    def _get_online_plugins(self):
        online_devices = dict()
        for plugin_unique_name, plugin in self.online_plugins.items():
            online_devices[plugin_unique_name] = {
                'plugin_type': plugin['plugin_type'],
                'plugin_subtype': plugin['plugin_subtype'],
                PLUGIN_UNIQUE_NAME: plugin[PLUGIN_UNIQUE_NAME],
                PLUGIN_NAME: plugin[PLUGIN_NAME],
                'supported_features': plugin['supported_features'],
                NODE_ID: plugin[NODE_ID]
            }

        return online_devices

    def _translate_url(self, full_url):
        (plugin, *url) = full_url.split('/')

        address_dict = self._get_plugin_addr(plugin.lower())

        address_dict['path'] = '/api/' + '/'.join(url)

        return address_dict

    def _get_plugin_addr(self, plugin_unique_name):
        """ Get the plugin address from its unique_name/name.

        Looks in the online plugins list.
        At first, it will try to find the plugin by his unique name. If one cant find a matching unique name,
        It will try to search for a plugin with the same name (For example, Execution)

        :param str plugin_unique_name: The unique_name/name of the plugin

        :return dict: Dictionary containing plugin ip, plugin port and api key to use.
        """
        candidate_plugin = self.online_plugins.get(plugin_unique_name)
        if not candidate_plugin:
            # Try to find plugin by name and not by unique name
            candidate_plugin = next((plugin for plugin in self.online_plugins.values()
                                     if plugin['plugin_name'] == plugin_unique_name), None)
            if not candidate_plugin:
                # Plugin is not in the online list
                raise PluginNotFoundError()

        unique_plugin = candidate_plugin[PLUGIN_UNIQUE_NAME]

        relevant_doc = self._get_config(plugin_unique_name=unique_plugin)

        if not relevant_doc:
            logger.warning("No online plugin found for {0}".format(plugin_unique_name))
            raise PluginNotFoundError()

        return {"plugin_ip": relevant_doc["plugin_ip"],
                "plugin_port": str(relevant_doc["plugin_port"]),
                "api_key": relevant_doc["api_key"]}

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
