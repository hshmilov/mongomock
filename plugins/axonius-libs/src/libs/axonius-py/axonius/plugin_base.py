"""PluginBase.py: Implementation of the base class to be inherited by other plugins."""

__author__ = "Ofir Yefet"

import json
from datetime import datetime, timedelta
import sys
import traceback
import requests
import configparser
import os
import logging
import socket

from flask import Flask, request, jsonify
from flask.json import JSONEncoder
from pymongo import MongoClient
# bson is requirement of mongo and its not recommended to install it manually
from bson import ObjectId
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from retrying import retry
from pathlib import Path
from promise import Promise

from axonius import plugin_exceptions
from axonius.adapter_exceptions import TagDeviceError
from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.mixins.feature import Feature
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME, VOLATILE_CONFIG_PATH, AGGREGATOR_PLUGIN_NAME
from axonius.logging.logger import create_logger

# Starting the Flask application
AXONIUS_REST = Flask(__name__)

# this would be /home/axonius/logs, or c:\users\axonius\logs, etc.
LOG_PATH = str(Path.home().joinpath('logs'))

# Can wait up to 5 minutes if core didnt answer yet
TIME_WAIT_FOR_REGISTER = 60 * 5


@AXONIUS_REST.after_request
def after_request(response):
    """This function is used to allow other domains to send post messages to this app.

    These headers are used to provide the cross origin resource sharing (cors) policy of this domain. 
    Modern browsers do not permit sending requests (especially post, put, etc) to different domains
    without the explicit permission of the webserver on this domain. 
    This is why we have to add headers that say that we allow these methods from all domains.

    :param str docker_base_url: The response of the client (Will change is headers)

    :return: Fixed response that allow other domain to send all methods
    """
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


# Global list of all the functions we are registering.
ROUTED_FUNCTIONS = list()


def add_rule(rule, methods=['GET'], should_authenticate=True):
    """ Decorator for adding function to URL.

    This decorator will add a flask rule to a wanted method from a class derived
    From PluginBase

    :param str rule: The address. for example, if rule='device' 
            This function will be accessed when browsing '/device'
    :param methods: Methods that this function will handle
    :param bool should_authenticate: Whether to check api key or not. True by default

    :type methods: list of str
    """

    def wrap(func):
        ROUTED_FUNCTIONS.append((func, '{0}/{1}'.format('api', rule), methods))

        def actual_wrapper(self, *args, **kwargs):
            """This wrapper will catch every exception.

            This wrapper will always cath exceptions from the decorated func. In that case, we return 
            the exception name with the Exception string.
            In case of exception, a detailed traceback will be sent to log
            """
            # We expect the first argument to be a PluginBase object (which have a logger object)
            logger = getattr(self, "logger", None)

            if logger:
                logger.info(f"Rule={rule} request={request}")

            try:
                if should_authenticate:
                    # finding the api key
                    api_key = self.api_key
                    if api_key != request.headers.get('x-api-key'):
                        raise RuntimeError(f"Bad api key. got {request.headers.get('x-api-key')}")
                return func(self, *args, **kwargs)
            except Exception as err:
                try:
                    if logger:
                        # Adding exception details for the json logger
                        _, _, exc_traceback = sys.exc_info()
                        tb = repr(traceback.extract_tb(exc_traceback))
                        err_type = type(err).__name__
                        err_message = str(err)
                        extra_log = dict()
                        extra_log['err_traceback'] = tb
                        extra_log['err_type'] = err_type
                        extra_log['err_message'] = err_message
                        logger.exception("Unhandled exception thrown from plugin", extra=extra_log)
                    return json.dumps({"status": "error", "type": err_type, "message": err_message}), 400
                except Exception as second_err:
                    return json.dumps({"status": "error", "type": type(second_err).__name__,
                                       "message": str(second_err)}), 400

        return actual_wrapper

    return wrap


class IteratorJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o.generation_time)
        try:
            iterable = iter(o)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, o)


def retry_if_connection_error(exception):
    """Return True if we should retry (in this case when it's an connection), False otherwise"""
    return isinstance(exception, requests.exceptions.ConnectionError)


def return_error(error_message, http_status=500):
    """ Helper function for returning errors in our format.

    :param str error_message: The explenation of the error
    :param int http_status: The http status to return, 500 by default
    """
    return jsonify({'status': 'error', 'message': error_message}), http_status


class PluginBase(Feature):
    """ This is an abstract class containing the implementation
    For the base capabilities of the Plugin.

    You should inherit this class from your Plugin class, and then use the decorator
    'add_rule' in order to add this rule to the URL.

    All Exceptions thrown from your decorated function will return as a response for
    The user request.

    """

    def __init__(self, core_data=None, requested_unique_plugin_name=None, *args, **kwargs):
        """ Initialize the class.

        This will automatically add the rule of '/version' to get the Plugin version.

        :param dict core_data: A data sent by the core plugin. (Will skip the registration process)

        :raise KeyError: In case of environment variables missing
        """

        # Basic configurations concerning axonius-libs. This will be changed by the CI.
        # No need to put such a small thing in a version.ini file, the CI changes this string everywhere.

        # Getting values from configuration file
        temp_config = configparser.ConfigParser()
        temp_config.read(VOLATILE_CONFIG_PATH)
        self.config_file_path = 'plugin_config.ini'

        self.config = configparser.ConfigParser()
        self.config.read(self.config_file_path)

        self.version = self.config['DEFAULT']['version']
        self.lib_version = self.version  # no meaning to axonius-libs right now, when we are in one repo.
        self.plugin_name = self.config['DEFAULT']['name']
        self.plugin_unique_name = None
        self.api_key = None

        print(f"{self.plugin_name} is starting")

        # Debug values. On production, flask is not the server, its just a wsgi app that uWSGI uses.
        try:
            self.host = temp_config['DEBUG']['host']
            self.port = int(temp_config['DEBUG']['port'])
            self.core_address = temp_config['DEBUG']['core_address'] + '/api'
        except KeyError:
            try:
                # We can enter debug value on all of the config files
                self.host = self.config['DEBUG']['host']
                self.port = int(self.config['DEBUG']['port'])
                self.core_address = self.config['DEBUG']['core_address'] + '/api'
            except KeyError:
                # This is the default value, which is what nginx sets for us.
                self.host = "0.0.0.0"
                self.port = 443  # We listen on https.
                # This should be dns resolved.
                self.core_address = "http://core/api"

        if requested_unique_plugin_name is not None:
            self.plugin_unique_name = requested_unique_plugin_name

        try:
            self.plugin_unique_name = temp_config['registration'][PLUGIN_UNIQUE_NAME]
            self.api_key = temp_config['registration']['api_key']
        except KeyError:
            # We might have api_key but not have a unique plugin name.
            pass

        if not core_data:
            core_data = self._register(self.core_address + "/register", self.plugin_unique_name, self.api_key)
        if not core_data or core_data['status'] == 'error':
            raise RuntimeError("Register process failed, Exiting. Reason: {0}".format(core_data['message']))

        if core_data[PLUGIN_UNIQUE_NAME] != self.plugin_unique_name or core_data['api_key'] != self.api_key:
            self.plugin_unique_name = core_data[PLUGIN_UNIQUE_NAME]
            self.api_key = core_data['api_key']
            temp_config['registration'] = {}
            temp_config['registration'][PLUGIN_UNIQUE_NAME] = self.plugin_unique_name
            temp_config['registration']['api_key'] = self.api_key

            with open(VOLATILE_CONFIG_PATH, 'w') as temp_config_file:
                temp_config.write(temp_config_file)

        # Use the data we have from the core.

        self.db_host = core_data['db_addr']
        self.db_user = core_data['db_user']
        self.db_password = core_data['db_password']
        self.logstash_host = core_data['log_addr']

        self.log_path = LOG_PATH + '/' + self.plugin_unique_name + '_axonius.log'
        self.log_level = logging.INFO

        # Creating logger
        self.logger = create_logger(self.plugin_unique_name, self.log_level, self.logstash_host, self.log_path)

        # Adding rules to flask
        for routed in ROUTED_FUNCTIONS:
            (wanted_function, rule, wanted_methods) = routed

            # this condition is here to force only rules that are relevant to the current class
            local_function = getattr(self, wanted_function.__name__, None)
            if local_function:
                AXONIUS_REST.add_url_rule('/' + rule, rule,
                                          local_function,
                                          methods=wanted_methods)
            else:
                self.logger.info(f"Skipped rule {rule}, {wanted_function.__qualname__}, {wanted_methods}")

        # Adding "keepalive" thread
        if self.plugin_unique_name != "core":
            self.comm_failure_counter = 0
            executors = {'default': ThreadPoolExecutor(1)}
            self.online_plugins_scheduler = LoggedBackgroundScheduler(self.logger, executors=executors)
            self.online_plugins_scheduler.add_job(func=self._check_registered_thread,
                                                  trigger=IntervalTrigger(seconds=30),
                                                  next_run_time=datetime.now() + timedelta(seconds=20),
                                                  id='check_registered',
                                                  name='check_registered',
                                                  max_instances=1)
            self.online_plugins_scheduler.start()

        # Creating open actions dict. This dict will hold all of the open actions issued by this plugin.
        # We will use this dict in order to determine what is the right callback for the action update retrieved.
        self._open_actions = dict()

        # Add some more changes to the app.
        AXONIUS_REST.json_encoder = IteratorJSONEncoder
        self.wsgi_app = AXONIUS_REST

        for section in self.config.sections():
            self.logger.info(f"Config {section}: {dict(self.config[section])}")

        self.logger.info(f"Running on ip {socket.gethostbyname(socket.gethostname())}")

        super().__init__(*args, **kwargs)
        # Finished, Writing some log
        self.logger.info("Plugin {0}:{1} with axonius-libs:{2} started successfully. ".format(self.plugin_unique_name,
                                                                                              self.version,
                                                                                              self.lib_version))

    @classmethod
    def specific_supported_features(cls) -> list:
        return ["Plugin"]

    def wsgi_app(self, *args, **kwargs):
        """
        A proxy to our wsgi app. Should be used by anyone inheriting from PluginBase that wants access
        to the wsgi function, like uWSGI.
        :return: what the actual wsgi app returns.
        """

        return self.wsgi_app(*args, **kwargs)

    def _check_registered_thread(self, retries=12):
        """Function for check that the plugin is still registered.

        This function will issue a get request to the Core to see if we are still registered.
        I case we arent, this function will stop this application (and let the docker manager to run it again)

        :param int retries: Number of retries before exiting the plugin.
        """
        try:
            if self.plugin_name == "core":
                return  # No need to check on core itself
            response = self.request_remote_plugin("register?unique_name={0}".format(self.plugin_unique_name), timeout=5)
            if response.status_code in [404, 499, 502]:  # Fault values
                self.logger.error(f"Not registered to core (got response {response.status_code}), Exiting")
                # TODO: Think about a better way for exiting this process
                os._exit(1)
        except Exception as e:
            self.comm_failure_counter += 1
            if self.comm_failure_counter > retries:  # Two minutes
                self.logger.exception(("Error communicating with Core for more than 2 minutes, "
                                       "exiting. Reason: {0}").format(e))
                os._exit(1)

    def populate_register_doc(self, register_doc, config_plugin_path):
        """
        :param register_doc: hook that allows subclass to populate plugins register doc
        :param config_plugin_path: path to config file
        """
        pass

    @retry(wait_fixed=10 * 1000,
           stop_max_delay=60 * 5 * 1000,
           retry_on_exception=retry_if_connection_error)  # Try every 10 seconds for 5 minutes
    def _register(self, core_address, plugin_unique_name=None, api_key=None):
        """Create registration of the adapter to core.

        :param str core_address: The address of the core plugin
        :param str plugin_unique_name: Wanted name of the plugin(Optional)
        :param str api_key: Api key to use in case we want a certain plugin_unique_name
        :return requests.response: The register response from the core
        """
        register_doc = {"plugin_name": self.plugin_name,
                        "plugin_type": self.plugin_type,
                        "plugin_port": self.port
                        }

        self.populate_register_doc(register_doc, self.config_file_path)

        if plugin_unique_name is not None:
            register_doc[PLUGIN_UNIQUE_NAME] = plugin_unique_name
            if api_key is not None:
                register_doc['api_key'] = api_key

        response = requests.post(core_address, data=json.dumps(register_doc))
        return response.json()

    def start_serve(self):
        """Start Http server.

        This function is blocking as long as the Http server is up.
        .. warning:: Do not use it in production! nginx->uwsgi is the one that loads us on production, so it does not call start_serve.
        """
        AXONIUS_REST.run(host=self.host, port=self.port,
                         debug=True, use_reloader=False)

    def get_method(self):
        """Getting the method type of the request.

        :return: The method type of the current request
        """
        return request.method

    def get_url_param(self, param_name):
        """ Getting params from the URL entered.

        This function is getting parameters only from the URL. For example '/somthing?param1=somthing'

        :param str param_name: The name of the parameters we want to get

        :return: The value of the wanted parameter
        """
        return request.args.get(param_name)

    def get_request_header(self, header_name):
        return request.headers.get(header_name)

    def get_request_data(self):
        """Get the data (raw) from the request.

        :return:The content of the post request
        """
        return request.data

    def get_request_data_as_object(self):
        """ Get data from HTTP request as python object.

        :return: The contest of the post request as a python object (An output of the json.loads function)
        """
        post_data = self.get_request_data()
        if post_data:
            # To make it string instead of bytes
            decoded_data = post_data.decode('utf-8')
            data = json.loads(decoded_data)
            return data
        else:
            return None

    def get_caller_plugin_name(self):
        """
        Figures out who called us from
        :return: tuple(plugin_unique_name, plugin_name)
        """
        return request.headers.get('x-unique-plugin-name'), request.headers.get('x-plugin-name')

    def request_remote_plugin(self, resource, plugin_unique_name=None, method='get', **kwargs):
        """
        Provides an interface to access other plugins, with the current plugin's API key.
        :type resource: str
        :param resource: The resource (e.g. 'devices' or 'version') of the plugin
        :type plugin_unique_name: str
        :param plugin_unique_name: The unique name of the plugin in question. None will make a request to the core.
                                   You can also enter a plugin name instead of unique name for single instances like
                                   Aggregator or Execution.
        :param method: HTTP method - see `request.request`
        :param kwargs: passed to `requests.request`
        :return: :class:`Response <Response>` object
        :rtype: requests.Response
        """
        headers = {'x-api-key': self.api_key}
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
            # this does not change the original dict given to this method
            del kwargs['headers']

        if plugin_unique_name is None:
            url = '{0}/{1}'.format(self.core_address, resource)
        else:
            url = '{0}/{1}/{2}'.format(self.core_address,
                                       plugin_unique_name, resource)

        return requests.request(method, url,
                                headers=headers, **kwargs)

    def create_notification(self, title, content='', severity_type='info', notification_type='basic'):
        with self._get_db_connection(True) as db:
            return db['core']['notifications'].insert_one(dict(who=self.plugin_unique_name,
                                                               plugin_name=self.plugin_name,
                                                               severity=severity_type,
                                                               type=notification_type,
                                                               title=title,
                                                               content=content,
                                                               seen=False)).inserted_id

    def get_plugin_by_name(self, plugin_name, verify_single=True, verify_exists=True):
        """
        Finds plugin_name in the online plugin list
        :param plugin_name: str
        :param verify_single: If True, will raise if many instances are found.
        :param verify_exists: If True, will raise if no instances are found.
        :return: if verify_single: single plugin data or None; if not verify_single: all plugin datas
        """
        # using requests directly so the api key won't be sent, so the core will give a list of the plugins
        plugins_available = requests.get(self.core_address + '/register').json()
        found_plugins = [x for x in plugins_available.values() if x['plugin_name'] == plugin_name]

        if verify_single:
            if len(found_plugins) == 0:
                if verify_exists:
                    raise plugin_exceptions.PluginNotFoundException(
                        "There is no plugin {0} currently registered".format(plugin_name))
                return None
            if len(found_plugins) != 1:
                raise RuntimeError(
                    "There are {0} plugins or {1}, there should only be one".format(len(found_plugins), plugin_name))
            return found_plugins[0]
        else:
            if verify_exists and (not found_plugins):
                raise plugin_exceptions.PluginNotFoundException(
                    "There is no plugin {0} currently registered".format(plugin_name))
            return found_plugins

    @add_rule('supported_features', should_authenticate=False)
    def get_supported_features(self):
        return jsonify(self.supported_features)

    @add_rule('version', methods=['GET'], should_authenticate=False)
    def _get_version(self):
        """ /version - Get the version of the app.

        Accepts:
            GET - In order to retrieve the plugin version
        """
        version_object = {"plugin_name": self.plugin_name,
                          "plugin_unique_name": self.plugin_unique_name,
                          "plugin": self.version,
                          "axonius-libs": self.lib_version}

        return jsonify(version_object)

    @add_rule('trigger_registration_check', methods=['GET'], should_authenticate=False)
    def trigger_registration_check(self):
        """ /check_registered - Get the version of the app.

        Accepts:
            GET - In order to check if we are registered
        """
        # Will exit immediately if plugin is not registered
        self._check_registered_thread(retries=0)
        return ''

    @add_rule('logger', methods=['GET', 'PUT'])
    def _logger_func(self):
        """ /logger - In order to change logger settings

        Accepts:
            GET - In order to get the current logger details (currently just logging level)
            PUT - In order to change logger details. available params:
                'level': The wanted logging level (string)
        """
        logging_types = {'debug': logging.DEBUG,
                         'info': logging.INFO,
                         'warning': logging.WARNING,
                         'error': logging.ERROR,
                         'fatal': logging.FATAL}
        if self.get_method() == 'PUT':
            wanted_level = self.get_url_param('level')
            if wanted_level is None:
                return return_error("missing wanted_level parameter", 400)
            wanted_level = wanted_level.lower()
            if wanted_level in logging_types.keys():
                self.log_level = logging_types[wanted_level]
                self.logger.setLevel(self.log_level)
                return ''
            else:
                error_string = "Unsupported log level \"{wanted_level}\", available log levels are {levels}"
                return return_error(error_string.format(wanted_level=wanted_level, levels=logging_types.keys()), 400)
        else:
            return logging.getLevelName(self.log_level)

    @add_rule('action_update/<action_id>', methods=['POST'])
    def action_callback(self, action_id):
        """ A function for receiving updates from the executor (Adapter or EC).

        This function will listen on updates, and if the update is on a relevant action_id it will call the 
        Callback registered for this action.

        :param str action_id: The id of the wanted action

        Accepts:
            POST - For posting a status update (or sending results) on a specific action
        """
        if self.plugin_name == "execution":
            # This is a special case for the execution_controller plugin. In that case, The EC plugin knows how to
            # handle other actions such as reset_update. In case of ec plugin, we know for sure what is the
            # callback, we use this fact to just call the callback and not search for it on the _open_actions
            # list (because the current action id will not be there)
            self.ec_callback(action_id)
            return ''

        if action_id in self._open_actions:
            # We recognize this action id, should call its callback
            action_promise = self._open_actions[action_id]
            # Calling the needed function
            request_content = self.get_request_data_as_object()

            if request_content['status'] == 'failed':
                action_promise.do_reject(Exception(request_content))
            elif request_content['status'] == 'finished':
                action_promise.do_resolve(request_content)
            return ''
        else:
            self.logger.error('Got unrecognized action_id update. Action ID: {0}'.format(action_id))
            return return_error('Unrecognized action_id {0}'.format(action_id), 404)

    def request_action(self, action_type, axon_id, data_for_action=None):
        """ A function for requesting action.

        This function called be used by any plugin. It will initiate an action request from the EC

        :param str action_type: The type of the action. For example 'put_file'
        :param str axon_id: The axon id of the device we want to run action on
        :param dict data_for_action: Extra data for executing the wanted action.

        :return Promise result: A promise of the action
        """
        data = {}
        if data_for_action:
            data = data_for_action.copy()

        # Building the uri for the request
        uri = f"action/{action_type}?axon_id={axon_id}"

        result = self.request_remote_plugin(uri,
                                            plugin_unique_name='execution',
                                            method='POST',
                                            data=json.dumps(data))

        action_id = result.json()['action_id']

        promise_for_action = Promise()

        self._open_actions[action_id] = promise_for_action

        return promise_for_action

    def _get_db_connection(self, limited_user=True):
        """
        Returns a new DB connection that can be queried.
        Currently, it uses mongodb

        :return: MongoClient
        """
        if limited_user:
            pure_addr = self.db_host.split("mongodb://")[1]
            connection_line = "mongodb://{user}:{password}@{addr}/{db}".format(user=self.db_user,
                                                                               password=self.db_password,
                                                                               addr=pure_addr,
                                                                               db=self.plugin_unique_name)
            return MongoClient(connection_line)
        else:
            return MongoClient(self.db_host, username=self.db_user, password=self.db_password)

    def _get_collection(self, collection_name, db_name=None, limited_user=True):
        """
        Returns all configs for the current plugin.

        :param str collection_name: The name of the collection we want to get
        :param str db_name: The name of the db. By default it is the unique plugin name

        :return: list(dict)
        """
        if not db_name:
            db_name = self.plugin_unique_name
        return self._get_db_connection(limited_user)[db_name][collection_name]

    @add_rule('schema/<schema_type>', methods=['GET'])
    def schema(self, schema_type):
        """ /schema - Get the schema the plugin expects from configs. 
                      Will try to get the wanted schema according to <schema_type>

        Accepts:
            GET - Get schema. name of the schema is given in the url. 
                  For example: "http://<address>/schema/general_schema

        :return: list(str)
        """
        schema_type = "_" + schema_type + "_schema"
        if schema_type in dir(self):
            # We have a schema like this
            schema_func = getattr(self, schema_type)
            return jsonify(schema_func())
        else:
            self.logger.warning("Someone tried to get wrong schema '{0}'".format(schema_type))
            return return_error("No such schema. should implement {0}".format(schema_type), 400)

    def _general_schema(self):
        """
        Represents the set of keys the plugin expects from general config

        :return: JSON Schema
        """

        return {}

    @property
    def plugin_type(self):
        return "Plugin"

    @property
    def devices_db(self):
        """
        Simply returns the collection of the devices db.
        :return: A mongodb collection.
        """

        # This would throw an exception if we haven't found it, or found multiple aggregators for some reason.
        aggregator = self.get_plugin_by_name('aggregator')
        return self._get_collection("devices_db", db_name=aggregator[PLUGIN_UNIQUE_NAME])

    def __tag_device(self, device_identity_by_adapter, tagname, tagvalue, tagtype):
        """ Function for tagging adapter devices.
        This function will tag a wanted device. The tag will be related only to this adapter
        :param device_identity_by_adapter: a tuple of (adapter_unique_name, device_unique_id).
                                           e.g. ("ad-adapter-1234", "CN=EC2AMAZ-3B5UJ01,OU=D....")
        :param tagname: the name of the tag. should be a string.
        :param tagvalue: the value of the tag. could be any object.
        :param tagtype: the type of the tag. "label" for a regular tag, "data" for a data tag.
        :return:
        """
        tag_data = {'association_type': 'Tag',
                    'associated_adapter_devices': [
                        (device_identity_by_adapter[0], device_identity_by_adapter[1])
                    ],
                    "tagname": tagname,
                    "tagvalue": tagvalue,
                    "tagtype": tagtype}
        response = self.request_remote_plugin('plugin_push', AGGREGATOR_PLUGIN_NAME, 'post', data=json.dumps(tag_data))
        if response.status_code != 200:
            self.logger.error(f"Couldn't tag device. Reason: {response.status_code}, {str(response.content)}")
            raise TagDeviceError()

    def add_label_to_device(self, device_identity_by_adapter, label, is_enabled=True):
        """ A shortcut to _tag_device with tagtype "label" . if is_enabled = False, the label is grayed out."""
        return self.__tag_device(device_identity_by_adapter, label, is_enabled, "label")

    def add_data_to_device(self, device_identity_by_adapter, name, value):
        """ A shortcut to _tag_device with tagtype "data" """
        return self.__tag_device(device_identity_by_adapter, name, value, "data")

    def add_adapterdata_to_device(self, device_identity_by_adapter, name, value):
        """ A shortcut to _tag_device with tagtype "adapterdata" """
        return self.__tag_device(device_identity_by_adapter, name, value, "adapterdata")
