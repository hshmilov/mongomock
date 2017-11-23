"""app.py: This is the core process of Axonius system"""

__author__ = "Ofir Yefet"

import random
import string
import requests
import threading
import time
import configparser
import exceptions
import uritools
import uuid

from flask import jsonify, request, Response
from axonius.PluginBase import PluginBase, add_rule, return_error
from requests.exceptions import ReadTimeout, Timeout, ConnectionError

CHUNK_SIZE = 1024


class Core(PluginBase):
    def __init__(self, **kargs):
        """ Initialize all needed configurations
        """
        # Get local configuration
        config = configparser.ConfigParser()
        config.read('plugin_config.ini')
        plugin_unique_name = config['core_specific']['plugin_unique_name']
        db_addr = config['core_specific']['db_addr']
        db_user = config['core_specific']['db_user']
        db_password = config['core_specific']['db_password']
        log_addr = config['core_specific']['log_addr']

        temp_config = configparser.ConfigParser()
        temp_config.read('plugin_volatile_config.ini')
        try:
            api_key = config['core_specific']['api_key']
        except KeyError:
            # We should generate a new api_key and save it
            api_key = uuid.uuid4().hex
            temp_config['registration'] = {}
            temp_config['registration']['api_key'] = api_key
        with open('plugin_volatile_config.ini', 'w') as temp_config_file:
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

        # Initialize the base plugin (will initialize http server)
        # No registration process since we are sending core_data
        super().__init__(core_data=core_data, **kargs)

        # Get the needed docker socket
        # self.docker_client = docker.APIClient(base_url='unix://var/run/docker.sock')

        self.online_plugins = {}

        self._setup_images()  # TODO: Check if we should move it to another function
        # (so we wont get register request before initializing the server here)

        self.adapters_lock = threading.Lock()

        # Create plugin cleaner thread
        self.cleaner_thread = threading.Thread(
            target=self.clean_offline_plugins, name='plugins_cleaner')
        self.cleaner_thread.start()

    def clean_offline_plugins(self):
        """Thread for cleaning offline plugin.

        This function will run forever as a thread. It will remove from the online list plugins that do not appear
        To be online anymore.
        Currently the sample rate is determined to be 60 seconds
        """
        while True:
            try:
                with self.adapters_lock:
                    # Copying the list so we wont have to lock for the whole cleaning process
                    temp_list = self.online_plugins.copy()

                delete_list = []
                for plugin_unique_name in temp_list:
                    with self.adapters_lock:
                        if not self._check_plugin_online(plugin_unique_name):
                            if self.did_adapter_registered:
                                # We need to wait a bit and then try to check if plugin exists again
                                self.did_adapter_registered = False
                                break
                            else:
                                # The plugin didnt answer, removing the plugin subscription
                                delete_list.append(
                                    (plugin_unique_name, temp_list[plugin_unique_name]))

                with self.adapters_lock:
                    for delete_key, delete_value in delete_list:
                        delete_candidate = self.online_plugins.get(delete_key)
                        if delete_candidate is delete_value:
                            self.logger.info("Plugin {0} didnt answer, deleting "
                                             "from online plugins list".format(plugin_unique_name))
                            del self.online_plugins[delete_key]

                time.sleep(20)
            except Exception as e:
                self.logger.critical(
                    "Cleaning plugins had an error. message: {0}", str(e))

    def _setup_images(self):
        """ Setting up needed images
        """
        # TODO: Implement this
        pass

    def _get_config(self, plugin_unique_name):
        collection = self._get_collection('configs', limited_user=False)
        return collection.find_one({"plugin_unique_name": plugin_unique_name})

    def _check_plugin_online(self, plugin_unique_name):
        """ Function for checking if a plugin is online.

        May block for a maximum of 10 seconds.

        :param str plugin_unique_name: The name of the plugin

        :returns: True if the plugin is online, False otherwise
        """
        try:
            # Trying a simple GET request for the version
            data = self._translate_url(plugin_unique_name + '/version')
            final_url = uritools.uricompose(scheme='http', host=data['plugin_ip'], port=data['plugin_port'],
                                            path=data['path'])

            check_response = requests.get(final_url, timeout=10)

            if check_response.status_code == 200:
                return True
            else:
                return False

        except (ConnectionError, ReadTimeout, Timeout) as e:
            self.logger.info(
                "Got exception {} while trying to contact {}".format(e, plugin_unique_name))
            return False

        except Exception as e:
            self.logger.fatal(
                "Got unhandled exception {} while trying to contact {}".format(e, plugin_unique_name))
            return False

    def _create_db_for_plugin(self, plugin_unique_name, plugin_special_db_credentials=None):
        """ Creates a db for new plugin.
        This function will create a new database for the new plugin and give it the correct credentials.

        :param str plugin_unique_name: The unique name of the new plugin
        :param list plugin_special_db_credentials: A list of db's to get read-only role for them.

        :return db_user: The user name for this db
        :return db_password: The password for this db
        """
        db_user = plugin_unique_name
        db_password = ''.join(random.choices(
            string.ascii_letters + string.digits, k=16))
        db_connection = self._get_db_connection(False)
        roles = [{'role': 'dbOwner', 'db': plugin_unique_name},
                 {'role': 'insert_notification', 'db': 'core'}]

        # TODO: Consider a way of requesting roles other than read-only.
        if plugin_special_db_credentials is not None:
            for current_requested_db_cred in plugin_special_db_credentials:
                roles.append({'role': 'read', 'db': current_requested_db_cred})
        db_connection[plugin_unique_name].add_user(db_user,
                                                   password=db_password,
                                                   roles=roles)

        return db_user, db_password

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
        with self.adapters_lock:  # Locking the adapters list, in case "register" will get called from 2 plugins
            if self.get_method() == 'GET':
                api_key = self.get_request_header('x-api-key')
                if not api_key:
                    # No api_key, Returning the current online plugins. This will be used by the aggregator
                    # To find out which adapters are available
                    to_return_device = dict()
                    for plugin_name, plugin in self.online_plugins.items():
                        to_return_device[plugin_name] = {'plugin_type': plugin['plugin_type'],
                                                         'device_sample_rate': plugin['device_sample_rate'],
                                                         'plugin_unique_name': plugin['plugin_unique_name'],
                                                         'plugin_name': plugin['plugin_name']}
                    return jsonify(to_return_device)
                else:
                    # This is a registered check, we should get the plugin name (a parameter) and tell if its
                    # In our online list
                    unique_name = request.args.get('unique_name')
                    if unique_name in self.online_plugins:
                        if api_key == self.online_plugins[unique_name]['api_key']:
                            return 'OK'
                    # If we reached here than plugin is not registered, returning error
                    return return_error('Plugin not registered', 404)

            # method == POST
            data = self.get_request_data_as_object()

            plugin_name = data['plugin_name']
            plugin_type = data['plugin_type']
            plugin_port = data['plugin_port']
            plugin_special_db_credentials = data.get(
                'special_db_credentials', None)

            self.logger.info(
                "Got registration request from {0}".format(plugin_name))

            relevant_doc = None

            if 'plugin_unique_name' in data:
                # Plugin is trying to register with his own name
                plugin_unique_name = data['plugin_unique_name']
                self.logger.info(
                    "Plugin request to register with his own name: {0}".format(plugin_unique_name))

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
                    self.logger.warning("Plugin {0} request to register with "
                                        "unique name but with no api key".format(plugin_unique_name))

                # Checking if this plugin already online for some reason
                if plugin_unique_name in self.online_plugins:
                    duplicated = self.online_plugins[plugin_unique_name]
                    if request.remote_addr == duplicated['plugin_ip'] and plugin_port == duplicated['plugin_port']:
                        self.logger.warn(
                            "Pluging {} restrated".format(plugin_unique_name))
                        del self.online_plugins[plugin_unique_name]
                    else:
                        if self._check_plugin_online(plugin_unique_name):
                            # There is already a running plugin with the same name
                            self.logger.error(
                                "Plugin {0} trying to register but already online")
                            return return_error("Error - {0} is trying to register but already "
                                                "online".format(plugin_unique_name), 400)
                        else:
                            # The old plugin should be deleted
                            del self.online_plugins[plugin_unique_name]

            else:
                # New plugin
                while True:
                    # Trying to generate a random name
                    # TODO: Check that this name is also not in the DB
                    random_bits = random.getrandbits(16)
                    plugin_unique_name = plugin_name + "_" + str(random_bits)
                    if not self._get_config(plugin_unique_name) and plugin_unique_name not in self.online_plugins:
                        break
            if not relevant_doc:
                # Create a new plugin line
                # TODO: Ask the gui for permission to register this new plugin
                plugin_user, plugin_password = self._create_db_for_plugin(plugin_unique_name,
                                                                          plugin_special_db_credentials)
                doc = {
                    'plugin_unique_name': plugin_unique_name,
                    'plugin_name': plugin_name,
                    'plugin_ip': request.remote_addr,
                    'plugin_port': plugin_port,
                    'plugin_type': plugin_type,
                    'api_key': uuid.uuid4().hex,
                    'db_addr': self.db_host,
                    'db_user': plugin_user,
                    'db_password': plugin_password,
                    'log_addr': self.logstash_host,
                    'device_sample_rate': 60,  # Default sample rate is 60 seconds
                    'status': 'ok'
                }

            else:
                # This is an existing plugin, we should update its data on the db (data that the plugin can change)
                doc = relevant_doc.copy()
                doc['plugin_name'] = plugin_name
                doc['plugin_ip'] = request.remote_addr
                doc['plugin_port'] = plugin_port

            # Setting a new doc with the wanted configuration
            collection = self._get_collection('configs', limited_user=False)
            collection.replace_one(filter={'plugin_unique_name': doc['plugin_unique_name']},
                                   replacement=doc,
                                   upsert=True)

            # This time it must work since we enterned the needed document
            relevant_doc = self._get_config(plugin_unique_name)

            self.online_plugins[plugin_unique_name] = relevant_doc
            del relevant_doc['_id']  # We dont need the '_id' field
            self.did_adapter_registered = True
            self.logger.info("Plugin {0} registered successfuly!".format(
                relevant_doc['plugin_unique_name']))
            return jsonify(relevant_doc)

    @add_rule("<path:full_url>", methods=['POST', 'GET'], should_authenticate=False)
    def proxy(self, full_url):
        """Fetch the specified URL and streams it out to the client.

        If the request was referred by the proxy itself (e.g. this is an image fetch for
        a previously proxied HTML page), then the original Referer is passed.

        :param str full_url: Full URL of the request
        """
        api_key = self.get_request_header('x-api-key')

        # Checking api key
        calling_plugin = next((plugin for plugin in self.online_plugins.values(
        ) if plugin['api_key'] == api_key), None)
        if calling_plugin is None:
            self.logger.warning(
                "Got request from {ip} with wrong api key.".format(ip=request.remote_addr))
            return return_error("Api key not valid", 401)

        try:
            url_data = self._translate_url(full_url)
        except exceptions.PluginNotFoundError:
            return return_error("No such plugin!", 400)

        data = self.get_request_data()

        final_url = uritools.uricompose(scheme='http', host=url_data['plugin_ip'], port=url_data['plugin_port'],
                                        path=url_data['path'], query=request.args)

        # Requesting the wanted plugin
        headers = {
            'x-api-key': url_data['api_key'],
            'x-unique-plugin-name': calling_plugin['plugin_unique_name'],
            'x-plugin-name': calling_plugin['plugin_name']
        }
        r = requests.request(self.get_method(), final_url,
                             headers=headers, data=data)

        headers = dict(r.headers)

        def generate():
            for chunk in r.iter_content(CHUNK_SIZE):
                yield chunk

        return Response(generate(), headers=headers), r.status_code

    def _translate_url(self, full_url):
        (plugin, *url) = full_url.split('/')

        address_dict = self._get_plugin_addr(plugin.lower())

        address_dict['path'] = '/' + '/'.join(url)

        return address_dict

    def _get_plugin_addr(self, plugin_unique_name):
        """ Get the plugin address from its unique_name/name.

        Looks in the online plugins list.
        At first, it will try to find the plugin by his unique name. If one cant find a matching unique name,
        It will try to search for a plugin with the same name (For example, Execution)

        :param str plugin_unique_name: The unique_name/name of the plugin

        :return dict: Dictionary containing plugin ip, plugin port and api key to use.
        """
        if plugin_unique_name not in self.online_plugins:
            # Try to find plugin by name and not by unique name
            candidate_plugin = next((plugin for plugin in self.online_plugins.values()
                                     if plugin['plugin_name'] == plugin_unique_name), None)
            if not candidate_plugin:
                # Plugin is not in the online list
                raise exceptions.PluginNotFoundError()
        else:
            candidate_plugin = self.online_plugins[plugin_unique_name]

        unique_plugin = candidate_plugin['plugin_unique_name']

        relevant_doc = self._get_config(unique_plugin)

        if not relevant_doc:
            self.logger.warning(
                "No online plugin found for {0}".format(plugin_unique_name))
            return None, None

        return {"plugin_ip": relevant_doc["plugin_ip"],
                "plugin_port": str(relevant_doc["plugin_port"]),
                "api_key": relevant_doc["api_key"]}


def initialize():
    return Core()


def wsgi_main(*args, **kwargs):
    """The main method for wsgi apps.

    When in production mode, we use a production server with wsgi support to load our modules.
    so we use this function as a proxy to the real wsgi function flask provides.
    """

    # This has to be static, since wsgi_main is called a lot.
    if not hasattr(wsgi_main, "plugin"):
        wsgi_main.plugin = initialize()

    return wsgi_main.plugin.wsgi_app(*args, **kwargs)


if __name__ == "__main__":
    """The main function for a regular terminal call."""
    core = initialize()
    core.start_serve()
