"""PluginBase.py: Implementation of the base class to be inherited by other plugins."""

import logging
import logging.handlers
from concurrent.futures import ALL_COMPLETED
from funcy import chunks
from namedlist import namedtuple

from axonius.email_server import EmailServer

logger = logging.getLogger(f"axonius.{__name__}")
from axonius.mixins.configurable import Configurable
import json
from datetime import datetime, timedelta
import sys
import traceback

import requests
import configparser
import os
import threading
import functools
import socket
import ssl
import urllib3
import pymongo
import concurrent
import uuid
import multiprocessing

from axonius.consts.adapter_consts import IGNORE_DEVICE
from axonius.utils.threading import run_in_executor_helper, LazyMultiLocker
from axonius.utils.parsing import get_exception_string
from flask import Flask, request, jsonify
from flask.json import JSONEncoder
from bson import json_util
from pymongo import MongoClient
# bson is requirement of mongo and its not recommended to install it manually
from bson import ObjectId
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
import concurrent.futures
from retrying import retry
from pathlib import Path
from promise import Promise
from typing import Iterable

import axonius.entities
from axonius.entities import EntityType
from axonius import plugin_exceptions
from axonius.adapter_exceptions import TagDeviceError
from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME, VOLATILE_CONFIG_PATH, AGGREGATOR_PLUGIN_NAME, \
    ADAPTERS_LIST_LENGTH, CORE_UNIQUE_NAME, GUI_NAME
from axonius.devices.device_adapter import DeviceAdapter
from axonius.users.user_adapter import UserAdapter
from axonius.logging.logger import create_logger
from axonius.mixins.feature import Feature
from axonius.thread_stopper import StopThreadException, ThreadStopper, stoppable
from axonius.utils.debug import is_debug_attached

# Starting the Flask application
AXONIUS_REST = Flask(__name__)

# this would be /home/axonius/logs, or c:\users\axonius\logs, etc.
LOG_PATH = str(Path.home().joinpath('logs'))

# Can wait up to 5 minutes if core didnt answer yet
TIME_WAIT_FOR_REGISTER = 60 * 5

# After this time, the execution promise will be rejected.
TIMEOUT_FOR_EXECUTION_THREADS_IN_SECONDS = 150

# Removing ssl_verify false warnings from appearing in the logs on all the plugins.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass
else:
    # Handle target environment that doesn't support HTTPS verification
    ssl._create_default_https_context = _create_unverified_https_context


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


def add_rule(rule, methods=['GET'], should_authenticate: bool = True):
    """ Decorator for adding function to URL.

    This decorator will add a flask rule to a wanted method from a class derived
    From PluginBase

    :param str rule: The address. for example, if rule='device'
            This function will be accessed when browsing '/device'
    :param methods: Methods that this function will handle
    :param should_authenticate: Whether to check api key or not. True by default

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
            logger.debug(f"Rule={rule} request={request}")

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
                    return json.dumps({"status": "error", "type": err_type, "message": get_exception_string()}), 400
                except Exception as second_err:
                    return json.dumps({"status": "error", "type": type(second_err).__name__,
                                       "message": str(second_err)}), 400
                except StopThreadException:
                    if logger:
                        # Adding exception details for the json logger
                        logger.info(f"Gracefully stopped {threading.get_ident()}")
                        return return_error(f"Gracefully stopped.", 400)
            except StopThreadException:
                if logger:
                    # Adding exception details for the json logger
                    logger.info(f"Gracefully stopped {threading.get_ident()}")
                    return return_error(f"Gracefully stopped.", 400)

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


def return_error(error_message, http_status=500, additional_data=None):
    """ Helper function for returning errors in our format.

    :param str error_message: The explenation of the error
    :param int http_status: The http status to return, 500 by default
    """
    return jsonify({'status': 'error', 'message': error_message, 'additional_data': additional_data}), http_status


"""
entity_query_views_db_map   - map between EntityType and views collection from the GUI (e.g. user_views)
entity_views_results_db_map - map between EntityType and results collection from GUI (e.g. user_view_results) 
"""
GUI_DBs = namedtuple("GUI_DBs", ['entity_query_views_db_map', 'entity_views_results_db_map'])


class PluginBase(Configurable, Feature):
    """ This is an abstract class containing the implementation
    For the base capabilities of the Plugin.

    You should inherit this class from your Plugin class, and then use the decorator
    'add_rule' in order to add this rule to the URL.

    All Exceptions thrown from your decorated function will return as a response for
    The user request.

    """
    MyDeviceAdapter = None
    MyUserAdapter = None

    def __init__(self, config_file_path: str, core_data=None, requested_unique_plugin_name=None, *args, **kwargs):
        """ Initialize the class.

        This will automatically add the rule of '/version' to get the Plugin version.

        :param dict core_data: A data sent by the core plugin. (Will skip the registration process)

        :raise KeyError: In case of environment variables missing
        """
        print(f"{datetime.now()} Hello docker from {type(self)}")
        super().__init__(*args, **kwargs)

        # Basic configurations concerning axonius-libs. This will be changed by the CI.
        # No need to put such a small thing in a version.ini file, the CI changes this string everywhere.

        # Getting values from configuration file
        self.temp_config = configparser.ConfigParser()
        self.temp_config.read(VOLATILE_CONFIG_PATH)
        self.config_file_path = config_file_path

        self.config = configparser.ConfigParser()
        self.config.read(self.config_file_path)

        self.version = self.config['DEFAULT']['version']
        self.lib_version = self.version  # no meaning to axonius-libs right now, when we are in one repo.
        self.plugin_name = os.path.basename(os.path.dirname(self.config_file_path))
        self.plugin_unique_name = None
        self.api_key = None

        # MyDeviceAdapter things.
        self._entity_adapter_fields = {entity_type: {
            "fields_set": set(),
            "raw_fields_set": set(),
            "last_fields_count": (0, 0),
            "first_fields_change": True,
            "fields_db_lock": threading.RLock()
        } for entity_type in [EntityType.Devices, EntityType.Users]}
        print(f"{datetime.now()} {self.plugin_name} is starting")

        # Debug values. On production, flask is not the server, its just a wsgi app that uWSGI uses.
        try:
            self.host = self.temp_config['DEBUG']['host']
            self.port = int(self.temp_config['DEBUG']['port'])
            self.core_address = self.temp_config['DEBUG']['core_address'] + '/api'
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
                self.core_address = "https://core/api"

        if requested_unique_plugin_name is not None:
            self.plugin_unique_name = requested_unique_plugin_name

        try:
            self.plugin_unique_name = self.temp_config['registration'][PLUGIN_UNIQUE_NAME]
            self.api_key = self.temp_config['registration']['api_key']
        except KeyError:
            # We might have api_key but not have a unique plugin name.
            pass

        if not core_data:
            core_data = self._register(self.core_address + "/register", self.plugin_unique_name, self.api_key)
        if not core_data or core_data['status'] == 'error':
            raise RuntimeError("Register process failed, Exiting. Reason: {0}".format(core_data['message']))
        if 'registration' not in self.temp_config:
            self.temp_config['registration'] = {}

        if core_data[PLUGIN_UNIQUE_NAME] != self.plugin_unique_name or core_data['api_key'] != self.api_key:
            self.plugin_unique_name = core_data[PLUGIN_UNIQUE_NAME]
            self.api_key = core_data['api_key']
            self.temp_config['registration'][PLUGIN_UNIQUE_NAME] = self.plugin_unique_name
            self.temp_config['registration']['api_key'] = self.api_key

        with open(VOLATILE_CONFIG_PATH, 'w') as self.temp_config_file:
            self.temp_config.write(self.temp_config_file)

        # Use the data we have from the core.
        try:
            self.db_host = self.config['DEBUG']['db_addr']
            self.logstash_host = self.config['DEBUG']['log_addr']
        except KeyError:
            self.db_host = core_data['db_addr']
            self.logstash_host = core_data['log_addr']

        self.db_user = core_data['db_user']
        self.db_password = core_data['db_password']

        self.log_path = LOG_PATH + '/' + self.plugin_unique_name + '_axonius.log'
        self.log_level = logging.INFO

        # Creating logger
        create_logger(self.plugin_unique_name, self.log_level, self.logstash_host, self.log_path)

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
                logger.info(f"Skipped rule {rule}, {wanted_function.__qualname__}, {wanted_methods}")

        # Adding "keepalive" thread
        if self.plugin_unique_name != "core":
            self.comm_failure_counter = 0
            executors = {'default': ThreadPoolExecutor(1)}
            self.online_plugins_scheduler = LoggedBackgroundScheduler(executors=executors)
            if is_debug_attached():
                logger.info(f'Plugin is under debug mode, disabling keep alive thread')
            else:
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
        self._open_actions_lock = threading.Lock()

        # Add some more changes to the app.
        AXONIUS_REST.json_encoder = IteratorJSONEncoder
        self.wsgi_app = AXONIUS_REST

        for section in self.config.sections():
            logger.info(f"Config {section}: {dict(self.config[section])}")

        logger.info(f"Running on ip {socket.gethostbyname(socket.gethostname())}")

        # DB's
        self.aggregator_db_connection = self._get_db_connection()[AGGREGATOR_PLUGIN_NAME]
        self.devices_db = self.aggregator_db_connection['devices_db']
        self.users_db = self.aggregator_db_connection['users_db']
        self.devices_db_view = self.aggregator_db_connection['devices_db_view']
        self.users_db_view = self.aggregator_db_connection['users_db_view']

        self._entity_db_map = {
            EntityType.Users: self.users_db,
            EntityType.Devices: self.devices_db,
        }
        self._entity_views_db_map = {
            EntityType.Users: self.users_db_view,
            EntityType.Devices: self.devices_db_view,
        }

        self._my_adapters_map = {
            EntityType.Users: self.MyUserAdapter,
            EntityType.Devices: self.MyDeviceAdapter
        }

        # GUI Stuff
        gui_db_connection = self._get_db_connection()[GUI_NAME]
        user_view = gui_db_connection["user_views"]
        device_view = gui_db_connection["device_views"]

        entity_query_views_db_map = {
            EntityType.Users: user_view,
            EntityType.Devices: device_view,
        }

        user_view_results = gui_db_connection["user_view_results"]
        device_view_results = gui_db_connection["device_view_results"]

        entity_views_results_db_map = {
            EntityType.Users: user_view_results,
            EntityType.Devices: device_view_results
        }

        self.gui = GUI_DBs(entity_query_views_db_map, entity_views_results_db_map)

        # Namespaces
        self.devices = axonius.entities.DevicesNamespace(self)
        self.users = axonius.entities.UsersNamespace(self)

        # An executor dedicated to inserting devices to the DB
        # the number of threads should be in a proportion to the number of actual core that can run them
        # since these things are more IO bound here - we allow ourselves to fire more than the number of cores we have
        self.__data_inserter = concurrent.futures.ThreadPoolExecutor(max_workers=20 * multiprocessing.cpu_count())

        if "ScannerAdapter" not in self.specific_supported_features():
            # This is only used if it's the first time inserting to the DB - i.e. the DB is empty of any device
            # from this plugin. After it is exhausted, it should be None.
            # Also, for complexity reasons, we currently don't support scanners, because they
            # might want to be associated with another device instead of being inserted. This restriction might
            # be relaxed and allow scanners, but for now it's not important enough to do.
            self.__first_time_inserter = concurrent.futures.ThreadPoolExecutor(
                max_workers=2 * multiprocessing.cpu_count())
        else:
            self.__first_time_inserter = None

        self.device_id_db = self.aggregator_db_connection['current_devices_id']

        # An executor dedicated for running execution promises
        self.execution_promises = concurrent.futures.ThreadPoolExecutor(max_workers=20 * multiprocessing.cpu_count())

        # the execution monitor has its own mechanism. this thread will make exceptions if we run it in execution,
        # since it will try to reject functions and not promises.
        if self.plugin_name != "execution":
            # An executor dedicated to deleting forgotten execution requests
            self.execution_monitor_scheduler = LoggedBackgroundScheduler(executors={'default': ThreadPoolExecutor(1)})
            self.execution_monitor_scheduler.add_job(func=self.execution_monitor_thread,
                                                     trigger=IntervalTrigger(seconds=30),
                                                     next_run_time=datetime.now(),
                                                     name='execution_monitor_thread',
                                                     id='execution_monitor_thread',
                                                     max_instances=1)
            self.execution_monitor_scheduler.start()

        self._update_schema()
        self.renew_config_from_db()
        self.__renew_global_settings_from_db()

        # Finished, Writing some log
        logger.info("Plugin {0}:{1} with axonius-libs:{2} started successfully. ".format(self.plugin_unique_name,
                                                                                         self.version,
                                                                                         self.lib_version))

    def _save_field_names_to_db(self, entity_type: EntityType):
        """ Saves fields_set and raw_fields_set to the Plugin's DB """
        entity_fields = self._entity_adapter_fields[entity_type]
        collection_name = f"{entity_type.value}_fields"
        my_entity = self._my_adapters_map[entity_type]

        if my_entity is None:
            return

        with entity_fields['fields_db_lock']:
            logger.debug(f"Persisting {entity_type.name} fields to DB")
            fields = list(entity_fields['fields_set'])  # copy
            raw_fields = list(entity_fields['raw_fields_set'])  # copy

            # Upsert new fields
            fields_collection = self._get_db_connection()[self.plugin_unique_name][collection_name]

            fields_collection.update({'name': 'raw'}, {'$addToSet': {'raw': {'$each': raw_fields}}}, upsert=True)
            if entity_fields['first_fields_change']:
                fields_collection.update({'name': 'parsed'},
                                         {'name': 'parsed', 'schema': my_entity.get_fields_info()},
                                         upsert=True)
                entity_fields['first_fields_change'] = False

            # Save last update count
            entity_fields['last_fields_count'] = len(fields), len(raw_fields)

    def _new_device_adapter(self) -> DeviceAdapter:
        """ Returns a new empty device associated with this adapter. """
        if self.MyDeviceAdapter is None:
            raise ValueError('class MyDeviceAdapter(Device) class was not declared inside this Adapter class')
        return self.MyDeviceAdapter(self._entity_adapter_fields[EntityType.Devices]['fields_set'],
                                    self._entity_adapter_fields[EntityType.Devices]['raw_fields_set'])

    # Users.
    def _new_user_adapter(self) -> UserAdapter:
        """ Returns a new empty User associated with this adapter. """
        if self.MyUserAdapter is None:
            raise ValueError('class MyUserAdapter(user) class was not declared inside this Adapter class')
        return self.MyUserAdapter(self._entity_adapter_fields[EntityType.Users]['fields_set'],
                                  self._entity_adapter_fields[EntityType.Users]['raw_fields_set'])

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
                logger.error(f"Not registered to core (got response {response.status_code}), Exiting")
                # TODO: Think about a better way for exiting this process
                os._exit(1)
        except Exception as e:
            self.comm_failure_counter += 1
            if self.comm_failure_counter > retries:  # Two minutes
                logger.exception(("Error communicating with Core for more than 2 minutes, "
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
        register_doc = {
            "plugin_name": self.plugin_name,
            "plugin_type": self.plugin_type,
            "plugin_subtype": self.plugin_subtype,
            "plugin_port": self.port,
            "is_debug": is_debug_attached(),
            "supported_features": list(self.supported_features)
        }

        self.populate_register_doc(register_doc, self.config_file_path)

        if plugin_unique_name is not None:
            register_doc[PLUGIN_UNIQUE_NAME] = plugin_unique_name
            if api_key is not None:
                register_doc['api_key'] = api_key

        try:
            response = requests.post(core_address, data=json.dumps(register_doc))
            return response.json()
        except Exception as e:
            # this is in print because this is called before logger is available
            print(f"Exception on register: {repr(e)}")
            raise

    def start_serve(self):
        """Start Http server.

        This function is blocking as long as the Http server is up.
        .. warning:: Do not use it in production! nginx->uwsgi is the one that loads us on production, so it does not call start_serve.
        """
        context = ('/etc/ssl/certs/nginx-selfsigned.crt', '/etc/ssl/private/nginx-selfsigned.key')

        # uncomment the following lines run under profiler
        # from werkzeug.contrib.profiler import ProfilerMiddleware
        # AXONIUS_REST.config['PROFILE'] = True
        # AXONIUS_REST.wsgi_app = ProfilerMiddleware(AXONIUS_REST.wsgi_app, restrictions=[100], sort_by=('time', 'calls'))

        AXONIUS_REST.run(host=self.host,
                         port=self.port,
                         ssl_context=context,
                         debug=True,
                         use_reloader=False)

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
            # object_hook is needed to unserialize specific not json-serializable things, like Datetime.
            data = json.loads(decoded_data, object_hook=json_util.object_hook)
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

        if plugin_unique_name is None or plugin_unique_name == CORE_UNIQUE_NAME:
            url = '{0}/{1}'.format(self.core_address, resource)
        else:
            url = '{0}/{1}/{2}'.format(self.core_address,
                                       plugin_unique_name, resource)

        return requests.request(method, url, headers=headers, **kwargs)

    def create_notification(self, title, content='', severity_type='info', notification_type='basic'):
        with self._get_db_connection() as db:
            return db[CORE_UNIQUE_NAME]['notifications'].insert_one(dict(who=self.plugin_unique_name,
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

    @add_rule('stop_plugin', should_authenticate=False)
    def stop_plugin(self):
        ThreadStopper.stopped.set()
        try:
            logger.info(f"received stop request for plugin: {self.plugin_unique_name}")
            ThreadStopper.stop_all()
        finally:
            ThreadStopper.stopped.clear()
        return '', 204

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

    @add_rule('logger', methods=['GET', 'PUT'], should_authenticate=False)
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
                logger.setLevel(self.log_level)
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
        try:
            if self.plugin_name == "execution":
                # This is a special case for the execution_controller plugin. In that case, The EC plugin knows how to
                # handle other actions such as reset_update. In case of ec plugin, we know for sure what is the
                # callback, we use this fact to just call the callback and not search for it on the _open_actions
                # list (because the current action id will not be there)
                self.ec_callback(action_id)
                return ''

            with self._open_actions_lock:
                if action_id in self._open_actions:
                    # We recognize this action id, should call its callback
                    action_promise, started_time = self._open_actions[action_id]
                    # logger.info(f"action id {action_id} returned after time {datetime.now() - started_time}")
                    # Calling the needed function
                    request_content = self.get_request_data_as_object()

                    # We must reject or resolve the promise with a thread, so that we wouldn't catch the lock
                    # and return the http request immediately.

                    if request_content['status'] == 'failed':
                        self.execution_promises.submit(action_promise.do_reject, Exception(request_content))
                        self._open_actions.pop(action_id)
                    elif request_content['status'] == 'finished':
                        self.execution_promises.submit(action_promise.do_resolve, request_content)
                        self._open_actions.pop(action_id)
                    return ''
                else:
                    logger.error(f'Got unrecognized action_id update. Action ID: {action_id}. Was it resolved?')
                    return return_error('Unrecognized action_id {action_id}. Was it resolved?', 404)
        except Exception as e:
            logger.exception("General exception in action callback")
            raise e

    def request_action(self, action_type, axon_id, data_for_action=None):
        """ A function for requesting action.

        This function called be used by any plugin. It will initiate an action request from the EC

        :param str action_type: The type of the action. For example 'put_file'
        :param str axon_id: The axon id of the device we want to run action on
        :param dict data_for_action: Extra data for executing the wanted action.

        :return Promise result: A promise of the action
        """
        if action_type in ('execute_wmi_smb', 'execute_shell', 'execute_binary') and not self._execution_enabled:
            logger.critical("Plugins decided to execute even though execution is disabled")
            return None
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

        with self._open_actions_lock:
            self._open_actions[action_id] = promise_for_action, datetime.now()

        return promise_for_action

    def execution_monitor_thread(self):
        """
        Monitors the _open_actions dict to reject actions that did not return after a certain time.
        :return:
        """

        with self._open_actions_lock:
            # copy it just to be able to change the dict size in the for loop
            open_actions_lock_copy = self._open_actions.copy()
            for action_id, (action_promise, time_started) in open_actions_lock_copy.items():
                if time_started + timedelta(seconds=TIMEOUT_FOR_EXECUTION_THREADS_IN_SECONDS) < datetime.now():
                    err_msg = f"Timeout {TIMEOUT_FOR_EXECUTION_THREADS_IN_SECONDS } reached for " \
                              f"action_id {action_id}, rejecting the promise."
                    logger.error(err_msg)

                    # We must reject or resolve the promise with a thread, so that we wouldn't catch the lock
                    # and return the http request immediately.
                    self.execution_promises.submit(action_promise.do_reject, Exception(err_msg))
                    self._open_actions.pop(action_id)

    def _get_db_connection(self):
        """
        Returns a new DB connection that can be queried.
        Currently, it uses mongodb

        :return: MongoClient
        """
        return MongoClient(self.db_host, username=self.db_user, password=self.db_password)

    def _get_collection(self, collection_name, db_name=None):
        """
        Returns all configs for the current plugin.

        :param str collection_name: The name of the collection we want to get
        :param str db_name: The name of the db. By default it is the unique plugin name

        :return: list(dict)
        """
        if not db_name:
            db_name = self.plugin_unique_name
        return self._get_db_connection()[db_name][collection_name]

    def _grab_file(self, field_data, stored_locally=True):
        """
        Fetches the file pointed by `field_data` from the DB.
        The user should not assume anything about the internals of the file.
        :param field_data:
        :param db_name: Name of the DB that file is stored in
        :return: stream like object
        """
        if field_data:
            import gridfs
            db_name = self.plugin_unique_name if stored_locally else CORE_UNIQUE_NAME
            return gridfs.GridFS(self._get_db_connection()[db_name]).get(ObjectId(field_data['uuid']))

    def _grab_file_contents(self, field_data, stored_locally=True):
        """
        Fetches the file pointed by `field_data` from the DB.
        The user should not assume anything about the internals of the file.
        :param field_data:
        :param stored_locally: Is the file stored in current plugin or in core (so it's generally available)
        :return: stream like object
        """
        if field_data:
            return self._grab_file(field_data, stored_locally).read()

    @add_rule('schema/<schema_type>', methods=['GET'])
    def schema(self, schema_type):
        """ /schema - Get the schema the plugin expects from configs. 
                      Will try to get the wanted schema according to <schema_type>

        Accepts:
            GET - Get schema. name of the schema is given in the url. 
                  For example: "https://<address>/schema/general_schema

        :return: list(str)
        """
        schema_type = "_" + schema_type + "_schema"
        if schema_type in dir(self):
            # We have a schema like this
            schema_func = getattr(self, schema_type)
            return jsonify(schema_func())
        else:
            logger.warning("Someone tried to get wrong schema '{0}'".format(schema_type))
            return return_error("No such schema. should implement {0}".format(schema_type), 400)

    @property
    def plugin_type(self):
        return "Plugin"

    @property
    def plugin_subtype(self):
        # TODO: This is bad, since pre-correlation plugins are being constantly triggered by the system scheduler
        # TODO: for "execute" trigger. but PluginBase isn't triggerable! so we better make it also triggerable
        # TODO: and make it not do anything.
        return "Pre-Correlation"

    def _save_data_from_plugin(self, client_name, data_of_client, entity_type: EntityType, should_log_info=True) -> int:
        """
        Saves all given data from adapter (devices, users) into the DB for the given client name
        :return: Device count saved
        """
        multilocker = LazyMultiLocker()
        db_to_use = self._entity_db_map.get(entity_type)
        assert db_to_use, f"got unexpected {entity_type}"

        @stoppable
        def insert_data_to_db(data_to_update, parsed_to_insert):
            """
            Insert data (devices/users/...) into the DB
            :return:
            """
            correlates = parsed_to_insert['data'].get('correlates')
            if correlates == IGNORE_DEVICE:
                # special case: this is a device we shouldn't handle
                self._save_parsed_in_db(parsed_to_insert, db_type='ignored_scanner_devices')
                return
            _to_insert_identity = parsed_to_insert['data']['id'], parsed_to_insert[PLUGIN_UNIQUE_NAME]

            if correlates:
                to_lock = [_to_insert_identity, correlates]
            else:
                to_lock = [_to_insert_identity]

            with multilocker.get_lock(to_lock):
                # trying to update the device if it is already in the DB
                modified_count = db_to_use.update_one({
                    'adapters': {
                        '$elemMatch': {
                            PLUGIN_UNIQUE_NAME: parsed_to_insert[PLUGIN_UNIQUE_NAME],
                            'data.id': parsed_to_insert['data']['id']
                        }
                    }
                }, {"$set": data_to_update}).modified_count

                if modified_count == 0:
                    # if it's not in the db then,

                    if correlates:
                        # for scanner adapters this is case B - see "scanner_adapter_base.py"
                        # we need to add this device to the list of adapters in another device
                        correlate_plugin_unique_name, correlated_id = correlates
                        modified_count = db_to_use.update_one({
                            'adapters': {
                                '$elemMatch': {
                                    PLUGIN_UNIQUE_NAME: correlate_plugin_unique_name,
                                    'data.id': correlated_id
                                }
                            }},
                            {
                                "$addToSet": {
                                    "adapters": parsed_to_insert
                                }
                        })
                        if modified_count == 0:
                            logger.error("No devices update for case B for scanner device "
                                         f"{parsed_to_insert['data']['id']} from "
                                         f"{parsed_to_insert[PLUGIN_UNIQUE_NAME]}")
                    else:
                        # this is regular first-seen device, make its own value
                        db_to_use.insert_one({
                            "internal_axon_id": uuid.uuid4().hex,
                            "accurate_for_datetime": datetime.now(),
                            "adapters": [parsed_to_insert],
                            "tags": [],
                            ADAPTERS_LIST_LENGTH: 1
                        })

        if should_log_info is True:
            logger.info(f"Starting to fetch data (devices/users) for {client_name}")
        try:
            time_before_client = datetime.now()

            inserted_data_count = 0
            promises = []

            @stoppable
            def insert_quickpath_to_db(devices):
                all_parsed = (self._create_axonius_entity(client_name, data, entity_type) for data in devices)
                db_to_use.insert_many(({
                    "internal_axon_id": uuid.uuid4().hex,
                    "accurate_for_datetime": datetime.now(),
                    "adapters": [parsed_to_insert],
                    "tags": [],
                    ADAPTERS_LIST_LENGTH: 1
                }
                    for parsed_to_insert
                    in all_parsed),
                    ordered=False,
                    bypass_document_validation=True
                )

            inserter = self.__first_time_inserter
            # quickest way to find if there are any devices from this plugin in the DB
            if inserter and db_to_use.find_one(
                    {"adapters.plugin_unique_name": self.plugin_unique_name}) is None:
                logger.info("Fast path! First run.")
                # DB is empty! no need for slow path, can just bulk-insert all.
                for devices in chunks(500, data_of_client['parsed']):
                    promises.append(Promise(functools.partial(run_in_executor_helper,
                                                              inserter,
                                                              insert_quickpath_to_db,
                                                              args=[devices])))
                    inserted_data_count += len(devices)
                    logger.info(f"Over {inserted_data_count} to DB")

            else:
                # DB is not empty. Should go for slow path.
                # Here we have all the devices a single client sees
                for data in data_of_client['parsed']:
                    parsed_to_insert = self._create_axonius_entity(client_name, data, entity_type)

                    # Note that this updates fields that are present. If some fields are not present but are present
                    # in the db they will stay there.
                    data_to_update = {f"adapters.$.{key}": value
                                      for key, value in parsed_to_insert.items() if key != 'data'}

                    fields_to_update = data.keys() - ['id']

                    for field in fields_to_update:
                        field_of_data = data.get(field, [])
                        data_to_update[f"adapters.$.data.{field}"] = field_of_data

                    inserted_data_count += 1
                    promises.append(Promise(functools.partial(run_in_executor_helper,
                                                              self.__data_inserter,
                                                              insert_data_to_db,
                                                              args=[data_to_update, parsed_to_insert])))

                    promises = [p for p in promises if p.is_pending or p.is_rejected]

                    if inserted_data_count % 1000 == 0:
                        logger.info(f"Entities went through: {inserted_data_count}; " +
                                    f"promises active: {len(promises)}; " +
                                    f"in DB: {inserted_data_count - len(promises)}")

            promise_all = Promise.all(promises)
            Promise.wait(promise_all, timedelta(minutes=20).total_seconds())
            if promise_all.is_rejected:
                logger.error(f"Error in insertion of {entity_type} to DB", exc_info=promise_all.reason)

            if entity_type == EntityType.Devices:
                added_pretty_ids_count = self._add_pretty_id_to_missing_adapter_devices()
                logger.info(f"{added_pretty_ids_count} devices had their pretty_id set")

            time_for_client = datetime.now() - time_before_client
            if should_log_info is True:
                logger.info(
                    f"Finished aggregating {entity_type} for client {client_name}, "
                    f" aggregation took {time_for_client.seconds} seconds and returned {inserted_data_count}.")

        except Exception as e:
            logger.exception("Thread {0} encountered error: {1}".format(threading.current_thread(), str(e)))
            raise
        finally:
            # whether or not it was successful, next time we shouldn't try first-time optimization and
            # go full slow path
            self.__first_time_inserter = None

        logger.info(f"Finished inserting {entity_type} of client {client_name}")
        if should_log_info is True:
            logger.info(f"Finished inserting {entity_type} of client {client_name}")
        return inserted_data_count

    def _create_axonius_entity(self, client_name, data, entity_type: EntityType):
        """
        Virtual.
        Creates an axonius entity ("Parsed data")
        :param client_name: the name of the client
        :param data: the parsed data
        :param entity_type: the type of the entity (see EntityType)
        :return: dict
        """
        parsed_to_insert = {
            'client_used': client_name,
            'plugin_type': self.plugin_type,
            "plugin_name": self.plugin_name,
            "plugin_unique_name": self.plugin_unique_name,
            "type": "entitydata",
            'accurate_for_datetime': datetime.now(),
            'data': data
        }
        parsed_to_insert['data']['accurate_for_datetime'] = datetime.now()

        return parsed_to_insert

    def _add_pretty_id_to_missing_adapter_devices(self):
        """
        Generates a unique pretty ID to all devices that don't have them for the current adapter
        :return: int - count of devices added
        """
        devices = self.devices_db.find(filter={'adapters': {
            '$elemMatch': {
                PLUGIN_UNIQUE_NAME: self.plugin_unique_name,
                'data.pretty_id': {"$exists": False}
            }
        }},
            projection={
                '_id': 1,
                'adapters.data.id': 1,
                'adapters.data.pretty_id': 1
        })

        adapter_devices_ids_to_add = []

        for device in devices:
            for adapter_device in device['adapters']:
                adapter_data = adapter_device['data']
                if 'pretty_id' not in adapter_data:
                    adapter_devices_ids_to_add.append((device['_id'], adapter_data['id']))

        pretty_ids_to_distribute = list(self._get_pretty_ids(len(adapter_devices_ids_to_add)))

        for (_id, adapter_id), pretty_id_to_add in zip(adapter_devices_ids_to_add, pretty_ids_to_distribute):
            res = self.devices_db.update_one({
                '_id': _id,
                'adapters': {
                    '$elemMatch': {
                        PLUGIN_UNIQUE_NAME: self.plugin_unique_name,
                        'data.id': adapter_id
                    }
                }
            }, {"$set":
                {'adapters.$.data.pretty_id': pretty_id_to_add}})
        return len(adapter_devices_ids_to_add)

    def _get_pretty_ids(self, count: int) -> Iterable[str]:
        """
        Returns fresh IDs from the DB. These are guaranteed to be unique.
        :param count: Amount of IDs to find
        :return:
        """
        new_id = self.device_id_db.find_one_and_update(
            filter={},
            update={'$inc': {'number': count}},
            upsert=True,
            return_document=pymongo.ReturnDocument.AFTER
        )['number']
        return (f'AX-{index}' for index in range(int(new_id - count), int(new_id)))

    def _save_parsed_in_db(self, device, db_type='parsed'):
        """
        Save axonius device in DB
        :param device: AxoniusDevice or device list
        :param db_type: 'parsed' or 'raw
        :return: None
        """
        self.aggregator_db_connection[db_type].insert_one(device)

    def _save_raw_data_in_history(self, device):
        """ Function for saving raw data in history.
        This function will save the data on mongodb. The db name is 'devices' and the collection is 'raw' always!
        :param device: The raw data of the current device
        """
        try:
            self.aggregator_db_connection['raw'].insert_one({'raw': device,
                                                             "plugin_name": self.plugin_name,
                                                             "plugin_unique_name": self.plugin_unique_name,
                                                             'plugin_type': self.plugin_type})
        except pymongo.errors.PyMongoError as e:
            logger.exception("Error in pymongo. details: {}".format(e))
        except pymongo.errors.DocumentTooLarge:
            # wanna see my "something too large"?
            logger.warn(f"Got DocumentTooLarge with client.")

    def _tag_many(self, entity: EntityType, identity_by_adapter, names, data, type, action_if_exists):
        """ Function for tagging many adapter devices with many tags.
        This function will tag a wanted device. The tag will be related to all adapters in the device.
        :param identity_by_adapter: a list of tuples of (adapter_unique_name, unique_id).
                                           e.g. [("ad-adapter-1234", "CN=EC2AMAZ-3B5UJ01,OU=D...."),...]
        :param names: a list of the tag. should be a list of strings.
        :param data: the data of the tag. could be any object. will be the same for all tags.
        :param type: the type of the tag. "label" for a regular tag, "data" for a data tag.
                     will be the same for all tags.
        :param entity: "devices" or "users" -> what is the entity we are tagging.
        :param action_if_exists: "replace" to replace the tag, "update" to update the tag (in case its a dict)
        :return:
        """
        assert action_if_exists == "replace" or (action_if_exists == "update" and type == "adapterdata")

        tag_data = {'association_type': 'Multitag',
                    'associated_adapters': identity_by_adapter,
                    'entity': entity.value,
                    'tags': [{
                        "action_if_exists": action_if_exists,
                        "name": name,
                        "data": data,
                        "type": type} for name in names]
                    }
        # Since datetime is often passed here, and it is not serializable, we use json_util.default
        # That automatically serializes it as a mongodb date object.
        response = self.request_remote_plugin('plugin_push', AGGREGATOR_PLUGIN_NAME, 'post',
                                              data=json.dumps(tag_data, default=json_util.default))
        if response.status_code != 200:
            logger.error(f"Couldn't tag device. Reason: {response.status_code}, {str(response.content)}")
            raise TagDeviceError(f"Couldn't tag device. Reason: {response.status_code}, {str(response.content)}")

        return response

    def _tag(self, entity: EntityType, identity_by_adapter, name, data, type, action_if_exists):
        """ Function for tagging adapter devices.
        This function will tag a wanted device. The tag will be related only to this adapter
        :param identity_by_adapter: a list of tuples of (adapter_unique_name, unique_id).
                                           e.g. [("ad-adapter-1234", "CN=EC2AMAZ-3B5UJ01,OU=D....")]
        :param name: the name of the tag. should be a string.
        :param data: the data of the tag. could be any object.
        :param type: the type of the tag. "label" for a regular tag, "data" for a data tag.
        :param entity: "devices" or "users" -> what is the entity we are tagging.
        :param action_if_exists: "replace" to replace the tag, "update" to update the tag (in case its a dict)
        :return:
        """

        assert action_if_exists == "replace" or (action_if_exists == "update" and type == "adapterdata")

        tag_data = {'association_type': 'Tag',
                    'associated_adapters': identity_by_adapter,
                    "name": name,
                    "data": data,
                    "type": type,
                    "entity": entity.value,
                    "action_if_exists": action_if_exists}
        # Since datetime is often passed here, and it is not serializable, we use json_util.default
        # That automatically serializes it as a mongodb date object.
        response = self.request_remote_plugin('plugin_push', AGGREGATOR_PLUGIN_NAME, 'post',
                                              data=json.dumps(tag_data, default=json_util.default))
        if response.status_code != 200:
            logger.error(f"Couldn't tag device. Reason: {response.status_code}, {str(response.content)}")
            logger.error(tag_data)
            raise TagDeviceError(f"Couldn't tag device. Reason: {response.status_code}, {str(response.content)}")

        return response

    def add_many_labels_to_entity(self, entity: EntityType, identity_by_adapter, labels, are_enabled=True):
        """ Tag many devices with many tags. if is_enabled = False, the labels are grayed out."""
        return self._tag_many(entity, identity_by_adapter, labels, are_enabled, "label", "replace")

    def add_label_to_entity(self, entity: EntityType, identity_by_adapter, label, is_enabled=True):
        """ A shortcut to __tag with type "label" . if is_enabled = False, the label is grayed out."""
        return self._tag(entity, identity_by_adapter, label, is_enabled, "label", "replace")

    def add_data_to_entity(self, entity: EntityType, identity_by_adapter, name, data):
        """ A shortcut to __tag with type "data" """
        return self._tag(entity, identity_by_adapter, name, data, "data", "replace")

    def add_adapterdata_to_entity(self, entity: EntityType, identity_by_adapter, data, action_if_exists="replace"):
        """ A shortcut to __tag with type "adapterdata" """
        return self._tag(entity, identity_by_adapter, self.plugin_unique_name, data, "adapterdata", action_if_exists)

    @add_rule("update_config", methods=['POST'], should_authenticate=False)
    def update_config(self):
        self.renew_config_from_db()
        self.__renew_global_settings_from_db()
        return ""

    def create_service_now_incident(self, short_description, description, impact):
        service_now_dict = {'short_description': short_description, 'description': description, 'impact': impact}
        self.request_remote_plugin('create_incident', 'service_now_adapter', 'post', json=service_now_dict)

    def send_syslog_message(self, message, log_level):
        syslog_settings = self._syslog_settings
        if syslog_settings['enabled'] is True:
            temp_logger = logging.getLogger("axonius.syslog")
            syslog_hdlr = logging.handlers.SysLogHandler(address=(
                syslog_settings['syslogHost'], syslog_settings.get('syslogPort', logging.handlers.SYSLOG_UDP_PORT)),
                facility=logging.handlers.SysLogHandler.LOG_DAEMON)
            syslog_hdlr.setLevel(logging.INFO)
            temp_logger.addHandler(syslog_hdlr)

            # Starting the messages with the tag Axonius
            formatted_message = f"Axonius:{message}"
            getattr(temp_logger, log_level)(formatted_message)

    @property
    def mail_sender(self):
        email_settings = self._email_settings
        if email_settings['enabled'] is True:
            return EmailServer(email_settings['smtpHost'], email_settings['smtpPort'],
                               email_settings.get('smtpUser'), email_settings.get('smtpPassword'),
                               self._grab_file_contents(email_settings.get('smtpKey'), stored_locally=False),
                               self._grab_file_contents(email_settings.get('smtpCert'), stored_locally=False))
        return None

    # Global settings
    # These are settings which are shared between all plugins. For example, all plugins should use the same
    # mail server when doing reports.
    # Adding or changing a settings requires a full restart of the system
    # and making sure you don't break a setting somebody else uses.

    def __renew_global_settings_from_db(self):
        config = self._get_db_connection()[CORE_UNIQUE_NAME]['configurable_configs'].find_one(
            {'config_name': 'CoreService'})['config']
        logger.info(f"Loading global config: {config}")
        self._email_settings = config['email_settings']
        self._execution_enabled = config['execution_settings']['enabled']
        self._syslog_settings = config['syslog_settings']

    @staticmethod
    def global_settings_schema():
        return {
            "items": [
                {
                    "items": [
                        {
                            "name": "enabled",
                            "title": "Use syslog",
                            "type": "bool"
                        },
                        {
                            "name": "syslogHost",
                            "title": "Syslog Host",
                            "type": "string"
                        },
                        {
                            "name": "syslogPort",
                            "title": "Port",
                            "type": "integer",
                            "format": "port"
                        }
                    ],
                    "name": "syslog_settings",
                    "title": "Syslog Settings",
                    "type": "array",
                    "required": ["syslogHost"]
                },
                {
                    "items": [
                        {
                            "name": "enabled",
                            "title": "Send emails",
                            "type": "bool"
                        },
                        {
                            "name": "smtpHost",
                            "title": "Email Host",
                            "type": "string"
                        },
                        {
                            "name": "smtpPort",
                            "title": "Port",
                            "type": "integer",
                            "format": "port"
                        },
                        {
                            "name": "smtpUser",
                            "title": "User Name",
                            "type": "string"
                        },
                        {
                            "name": "smtpPassword",
                            "title": "Password",
                            "type": "string"
                        },
                        {
                            "name": "smtpKey",
                            "title": "TLS 1.2 Key File",
                            "type": "file"
                        },
                        {
                            "name": "smtpCert",
                            "title": "TLS 1.2 Cert File",
                            "type": "file"
                        }
                    ],
                    "name": "email_settings",
                    "title": "Email Settings",
                    "type": "array",
                    "required": ["smtpHost", "smtpPort"]
                },
                {
                    "items": [
                        {
                            "name": "enabled",
                            "title": "Execution Enabled",
                            "type": "bool",
                            "required": True
                        }
                    ],
                    "name": "execution_settings",
                    "title": "Execution Settings",
                    "type": "array"
                }
            ],
            "pretty_name": "Global Configuration",
            "type": "array"
        }

    @staticmethod
    def global_settings_defaults():
        return {
            "email_settings": {
                "enabled": False,
                "smtpHost": None,
                "smtpPort": None,
                "smtpUser": None,
                "smtpPassword": None,
                "smtpCert": None,
                "smtpKey": None
            },
            "execution_settings": {
                "enabled": False
            },
            "syslog_settings": {
                "enabled": False,
                "syslogHost": None,
                "syslogPort": logging.handlers.SYSLOG_UDP_PORT
            }
        }
