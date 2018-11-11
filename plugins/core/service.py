import urllib3
import logging

from axonius.mixins.configurable import Configurable

logger = logging.getLogger(f'axonius.{__name__}')
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
import configparser
from datetime import datetime
from flask import jsonify, request, Response
import requests
from requests.exceptions import ReadTimeout, Timeout, ConnectionError
import threading
import uritools
import uuid
from multiprocessing.pool import ThreadPool

from axonius.plugin_base import PluginBase, add_rule, return_error, VOLATILE_CONFIG_PATH
from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME, X_UI_USER, X_UI_USER_SOURCE, PROXY_SETTINGS, PROXY_USER, \
    PROXY_PASSW, PROXY_ADDR, PROXY_PORT
from axonius.utils.files import get_local_config_file
from core.exceptions import PluginNotFoundError

CHUNK_SIZE = 1024
MAX_INSTANCES_OF_SAME_PLUGIN = 100


def set_mongo_parameter(connection, name, value):
    connection['admin'].command({
        'setParameter': 1,
        name: value
    })


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
        log_addr = config['core_specific']['log_addr']

        temp_config = configparser.ConfigParser()
        temp_config.read(VOLATILE_CONFIG_PATH)
        try:
            api_key = temp_config['core_specific']['api_key']
        except KeyError:
            # We should generate a new api_key and save it
            api_key = uuid.uuid4().hex
            temp_config['registration'] = {}
            temp_config['registration']['api_key'] = api_key
        with open(VOLATILE_CONFIG_PATH, 'w') as temp_config_file:
            temp_config.write(temp_config_file)

        # In order to avoid, deletion before initialization of adapter, we add this flag
        self.did_adapter_registered = False

        # Building doc data so we won't register on PluginBase (Core doesnt need to register)
        core_data = {"plugin_unique_name": plugin_unique_name,
                     "db_addr": db_addr,
                     "db_user": db_user,
                     "db_password": db_password,
                     "log_addr": log_addr,
                     "api_key": api_key,
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
                                    trigger=IntervalTrigger(seconds=20),
                                    next_run_time=datetime.now(),
                                    name='clean_offline_plugins',
                                    id='clean_offline_plugins',
                                    max_instances=1)
        self.cleaner_thread.start()

        # pool for global config updates
        self.__config_updater_pool = ThreadPool(30)

        with self._get_db_connection() as connection:
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
                        should_delete = not self._check_plugin_online(plugin_unique_name)
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

    def _get_config(self, plugin_unique_name):
        collection = self._get_collection('configs')
        return collection.find_one({"plugin_unique_name": plugin_unique_name})

    def _request_plugin(self, resource, plugin_unique_name, method='get', **kwargs):
        data = self._translate_url(plugin_unique_name + f"/{resource}")
        final_url = uritools.uricompose(scheme='https', host=data['plugin_ip'], port=data['plugin_port'],
                                        path=data['path'])

        return requests.request(method=method, url=final_url, timeout=5, **kwargs)

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
            logger.fatal("Got unhandled exception {} while trying to contact {}".format(e, plugin_unique_name))
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
            if not api_key:
                # No api_key, Returning the current online plugins. This will be used by the aggregator
                # To find out which adapters are available
                online_devices = self._get_online_plugins()
                return jsonify(online_devices)
            else:
                # This is a registered check, we should get the plugin name (a parameter) and tell if its
                # In our online list
                unique_name = request.args.get('unique_name')
                if unique_name in self.online_plugins:
                    actual_api_key = self.online_plugins[unique_name]['api_key']
                    if api_key == actual_api_key:
                        return 'OK'
                    else:
                        logger.error(f'Plugin {unique_name} gave wrong API key - {api_key} != {actual_api_key}')
                else:
                    logger.error(f'Plugin does not exist - {unique_name}')
                # If we reached here than plugin is not registered, returning error
                return return_error('Plugin not registered', 404)

        # method == POST
        data = self.get_request_data_as_object()

        plugin_name = data['plugin_name']
        plugin_type = data['plugin_type']
        plugin_subtype = data['plugin_subtype']
        plugin_port = data['plugin_port']
        supported_features = data['supported_features']
        plugin_is_debug = data.get('is_debug', False)

        logger.info(f"Got registration request : {data} from {request.remote_addr}")

        with self.adapters_lock:  # Locking the adapters list, in case "register" will get called from 2 plugins
            relevant_doc = None

            if PLUGIN_UNIQUE_NAME in data:
                # Plugin is trying to register with his own name
                plugin_unique_name = data[PLUGIN_UNIQUE_NAME]
                logger.info("Plugin request to register with his own name: {0}".format(plugin_unique_name))

                # Trying to get the configuration of the current plugin
                relevant_doc = self._get_config(plugin_unique_name)

                if 'api_key' in data and relevant_doc is not None:
                    api_key = data['api_key']
                    # Checking that this plugin has the correct api key
                    if api_key != relevant_doc['api_key']:
                        # This is not the correct api key, decline registration
                        return return_error('Wrong API key', 400)
                else:
                    # TODO: prompt message to gui that an unrecognized plugin is trying to connect
                    logger.warning("Plugin {0} request to register with "
                                   "unique name but with no api key".format(plugin_unique_name))

                # Checking if this plugin already online for some reason
                if plugin_unique_name in self.online_plugins:
                    duplicated = self.online_plugins[plugin_unique_name]
                    if request.remote_addr == duplicated['plugin_ip'] and plugin_port == duplicated['plugin_port']:
                        logger.warn("Pluging {} restarted".format(plugin_unique_name))
                        del self.online_plugins[plugin_unique_name]
                    else:
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
                # New plugin. First, start with a name with no unique identifier. Then, continue to
                # ongoing numbers.
                for unique_name_suffix in [f"_{i}" for i in range(MAX_INSTANCES_OF_SAME_PLUGIN)]:
                    # Try generating a unique name
                    # TODO: Check that this name is also not in the DB
                    plugin_unique_name = f"{plugin_name}{unique_name_suffix}"
                    if not self._get_config(plugin_unique_name) and plugin_unique_name not in self.online_plugins:
                        break
                else:
                    # Looped through the whole for and couldn't hit the break..
                    raise ValueError(f"Error, couldn't find a unique name for plugin {plugin_name}!")
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
                    'log_addr': self.logstash_host,
                    'status': 'ok',
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

            # This time it must work since we enterned the needed document
            relevant_doc = self._get_config(plugin_unique_name)

            self.online_plugins[plugin_unique_name] = relevant_doc
            del relevant_doc['_id']  # We dont need the '_id' field
            self.did_adapter_registered = True
            logger.info("Plugin {0} registered successfuly!".format(relevant_doc[PLUGIN_UNIQUE_NAME]))
            return jsonify(relevant_doc)

    def _get_online_plugins(self):
        online_devices = dict()
        for plugin_name, plugin in self.online_plugins.items():
            online_devices[plugin_name] = {
                'plugin_type': plugin['plugin_type'],
                'plugin_subtype': plugin['plugin_subtype'],
                PLUGIN_UNIQUE_NAME: plugin[PLUGIN_UNIQUE_NAME],
                'plugin_name': plugin['plugin_name'],
                'supported_features': plugin['supported_features']
            }

        return online_devices

    @add_rule("<path:full_url>", methods=['POST', 'GET', 'PUT', 'DELETE'], should_authenticate=False)
    def proxy(self, full_url):
        """Fetch the specified URL and streams it out to the client.

        If the request was referred by the proxy itself (e.g. this is an image fetch for
        a previously proxied HTML page), then the original Referer is passed.

        :param str full_url: Full URL of the request
        """
        api_key = self.get_request_header('x-api-key')

        # Checking api key
        calling_plugin = next((plugin for plugin in self.online_plugins.values() if plugin['api_key'] == api_key), None)
        if calling_plugin is None:
            logger.warning("Got request from {ip} with wrong api key.".format(ip=request.remote_addr))
            return return_error("Api key not valid", 401)

        try:
            url_data = self._translate_url(full_url)
        except PluginNotFoundError:
            return return_error("No such plugin!", 400)

        data = self.get_request_data()

        final_url = uritools.uricompose(scheme='https', host=url_data['plugin_ip'], port=url_data['plugin_port'],
                                        path=url_data['path'], query=request.args)

        # Requesting the wanted plugin
        headers = {
            'x-api-key': url_data['api_key'],
            'x-unique-plugin-name': calling_plugin[PLUGIN_UNIQUE_NAME],
            'x-plugin-name': calling_plugin['plugin_name'],
            X_UI_USER: request.headers.get(X_UI_USER),
            X_UI_USER_SOURCE: request.headers.get(X_UI_USER_SOURCE)
        }
        copy_headers = ['Content-Type', 'Content-Length', 'Accept', 'Accept-Encoding']
        headers.update({h: request.headers[h] for h in copy_headers if request.headers.get(h, '') != ''})

        r = requests.request(self.get_method(), final_url, headers=headers, data=data, stream=True)

        headers = dict(r.headers)

        def generate():
            for chunk in r.iter_content(CHUNK_SIZE):
                yield chunk

        return Response(generate(), headers=headers), r.status_code

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

        relevant_doc = self._get_config(unique_plugin)

        if not relevant_doc:
            logger.warning("No online plugin found for {0}".format(plugin_unique_name))
            raise PluginNotFoundError()

        return {"plugin_ip": relevant_doc["plugin_ip"],
                "plugin_port": str(relevant_doc["plugin_port"]),
                "api_key": relevant_doc["api_key"]}

    def _on_config_update(self, config):
        logger.info(f"Loading core config: {config}")
        self._proxy_settings = config[PROXY_SETTINGS]

        try:
            with open('/tmp/proxy_data.txt', 'w') as f:
                f.write(self.to_proxy_string(self._proxy_settings))
        except Exception:
            logger.error(f'Failed to set proxy settings from gui {self._proxy_settings}')

        def update_plugin(plugin_name):
            try:
                self._request_plugin('update_config', plugin_name, method='post')
            except Exception:
                logger.exception(f"Failed to update config on {plugin_name}")

        online_plugins = self.online_plugins.keys()
        if online_plugins:
            self.__config_updater_pool.map_async(update_plugin, online_plugins)

    @staticmethod
    def to_proxy_string(proxy_data):
        """
        Format proxy paramteres into proxy string format without the protocol prefix
        :param proxy_data: dict with proxy params such as user name, port ip etc
        """
        if not proxy_data['enabled'] or not proxy_data[PROXY_ADDR] or proxy_data[PROXY_ADDR] == '':
            return ''
        ip_port = f'{proxy_data[PROXY_ADDR]}:{proxy_data[PROXY_PORT]}'
        proxy_string = ip_port
        if proxy_data[PROXY_USER]:
            proxy_string = f'{proxy_data[PROXY_USER]}:{proxy_data[PROXY_PASSW]}@{ip_port}'

        urllib3.ProxyManager(f'http://{proxy_string}')
        return proxy_string

    @classmethod
    def _db_config_schema(cls) -> dict:
        return PluginBase.global_settings_schema()

    @classmethod
    def _db_config_default(cls):
        return PluginBase.global_settings_defaults()
