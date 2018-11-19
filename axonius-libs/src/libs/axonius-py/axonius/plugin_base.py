"""PluginBase.py: Implementation of the base class to be inherited by other plugins."""

import concurrent
import concurrent.futures
import configparser
import functools
import gc
import json
import logging
import logging.handlers
import multiprocessing
import os
import socket
import ssl
import sys
import threading
import traceback
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from itertools import groupby
from pathlib import Path
from typing import Iterable, List

import cachetools
import func_timeout
import pymongo
import requests
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger
# bson is requirement of mongo and its not recommended to install it manually
from tlssyslog import TLSSysLogHandler

from axonius.consts.plugin_subtype import PluginSubtype
from axonius.devices import deep_merge_only_dict
from bson import ObjectId, json_util
from flask import Flask, jsonify, request, has_request_context, session
from funcy import chunks
from namedlist import namedtuple
from promise import Promise
from pymongo import MongoClient
from retrying import retry

import axonius.entities
from axonius import plugin_exceptions, adapter_exceptions
from axonius.adapter_exceptions import TagDeviceError
from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.clients.service_now.connection import ServiceNowConnection
from axonius.clients.fresh_service.connection import FreshServiceConnection
from axonius.consts.adapter_consts import IGNORE_DEVICE
from axonius.consts.plugin_consts import (ADAPTERS_LIST_LENGTH,
                                          AGGREGATOR_PLUGIN_NAME,
                                          MAINTENANCE_SETTINGS,
                                          ANALYTICS_SETTING,
                                          CONFIGURABLE_CONFIGS_COLLECTION,
                                          CORE_UNIQUE_NAME, GUI_NAME,
                                          PLUGIN_UNIQUE_NAME,
                                          TROUBLESHOOTING_SETTING,
                                          VOLATILE_CONFIG_PATH, PLUGIN_NAME, X_UI_USER, X_UI_USER_SOURCE,
                                          PROXY_SETTINGS, PROXY_ADDR, PROXY_PORT, PROXY_USER, PROXY_PASSW,
                                          NOTIFICATIONS_SETTINGS, NOTIFY_ADAPTERS_FETCH)
from axonius.devices.device_adapter import DeviceAdapter, LAST_SEEN_FIELD
from axonius.email_server import EmailServer
from axonius.entities import EntityType
from axonius.logging.logger import create_logger
from axonius.mixins.configurable import Configurable
from axonius.mixins.feature import Feature
from axonius.types.correlation import CorrelationResult, CorrelateException
from axonius.types.ssl_state import COMMON_SSL_CONFIG_SCHEMA, COMMON_SSL_CONFIG_SCHEMA_DEFAULTS, SSLState
from axonius.users.user_adapter import UserAdapter
from axonius.utils.debug import is_debug_attached
from axonius.utils.json_encoders import IteratorJSONEncoder
from axonius.utils.mongo_retries import mongo_retry
from axonius.utils.parsing import get_exception_string
from axonius.utils.threading import LazyMultiLocker, run_in_executor_helper, run_and_forget

logger = logging.getLogger(f'axonius.{__name__}')

# Starting the Flask application
AXONIUS_REST = Flask(__name__)

# this would be /home/axonius/logs, or c:\users\axonius\logs, etc.
LOG_PATH = str(Path.home().joinpath('logs'))

# Can wait up to 5 minutes if core didnt answer yet
TIME_WAIT_FOR_REGISTER = 60 * 5

# After this time, the execution promise will be rejected.
TIMEOUT_FOR_EXECUTION_THREADS_IN_SECONDS = 60 * 25

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

        return actual_wrapper

    return wrap


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
"""
GUI_DBs = namedtuple("GUI_DBs", ['entity_query_views_db_map'])


def recalculate_adapter_oldness(adapter_list: list):
    """
    Updates (in place) all adapters given.
    This assuems that they all comprise a single axonius entity.
    All groups of adapters by plugin_name (i.e. "duplicate" adapter entities from the same adapter)
    will have they're "old" value recalculated
    https://axonius.atlassian.net/wiki/spaces/AX/pages/794230909/Handle+Duplicates+of+adapter+entity+of+the+same+adapter+entity
    Only the newest adapter entity will have an "old" value of False, all others will have "new".
    (Adapters that don't have duplicates are unaffected)
    :param adapter_list: list of adapter entities
    :return: None
    """
    all_unique_adapter_entities_data_indexed = defaultdict(list)
    for adapter in adapter_list:
        all_unique_adapter_entities_data_indexed[adapter[PLUGIN_NAME]].append(adapter)

    for adapters in all_unique_adapter_entities_data_indexed.values():
        if len(adapters) > 1:
            if not all(LAST_SEEN_FIELD in adapter['data'] for adapter in adapters):
                continue
            for adapter in adapters:
                adapter['data']['_old'] = True
            max(adapters, key=lambda x: x['data'][LAST_SEEN_FIELD])['data']['_old'] = False


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
    """
    This is effectively a singleton anyway
    """
    Instance = None

    def __init__(self, config_file_path: str, core_data=None, requested_unique_plugin_name=None, *args, **kwargs):
        """ Initialize the class.

        This will automatically add the rule of '/version' to get the Plugin version.

        :param dict core_data: A data sent by the core plugin. (Will skip the registration process)

        :raise KeyError: In case of environment variables missing
        """
        print(f"{datetime.now()} Hello docker from {type(self)}")

        PluginBase.Instance = self
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

        self.log_level = logging.INFO

        # Creating logger
        create_logger(self.plugin_unique_name, self.log_level, self.logstash_host, LOG_PATH)

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
        AXONIUS_REST.url_map.strict_slashes = False  # makes routing to "page" and "page/" the same.
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
        self.historical_devices_db_view = self.aggregator_db_connection['historical_devices_db_view']
        self.historical_users_db_view = self.aggregator_db_connection['historical_users_db_view']

        self._entity_db_map = {
            EntityType.Users: self.users_db,
            EntityType.Devices: self.devices_db,
        }
        self._entity_views_db_map = {
            EntityType.Users: self.users_db_view,
            EntityType.Devices: self.devices_db_view,
        }

        self._historical_entity_views_db_map = {
            EntityType.Users: self.historical_users_db_view,
            EntityType.Devices: self.historical_devices_db_view,
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

        self.gui_dbs = GUI_DBs(entity_query_views_db_map)

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
        self._update_config_inner()

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

        # Do note that we are saving the schema each time this function is called, instead of just once.
        # we do this because things can change due to dynamic fields etc.
        # we need to make sure that _save_field_names_to_db is not called too frequently, but mainly after
        # schema change (we can just call it once after all entities insertion,
        # or maybe after the insertion of X entities)

        with entity_fields['fields_db_lock']:
            logger.info(f"Persisting {entity_type.name} fields to DB")
            raw_fields = list(entity_fields['raw_fields_set'])  # copy

            # Upsert new fields
            fields_collection = self._get_db_connection()[self.plugin_unique_name][collection_name]
            fields_collection.update({'name': 'raw'}, {'$addToSet': {'raw': {'$each': raw_fields}}}, upsert=True)

            # Dynamic fields that were somewhen in the schema must always stay there (unless explicitly removed)
            # because otherwise we would always miss them (image an adapter parsing csv1 and then removing it. csv1's
            # columns are dynamic fields. we want the schema of csv1 appear in the gui even after its not longer
            # the current client!).
            current_dynamic_schema = my_entity.get_fields_info('dynamic')
            current_dynamic_schema_names = [field['name'] for field in current_dynamic_schema['items']]

            # Search for an old dynamic schema and add whatever we don't already have
            dynamic_fields_collection_in_db = fields_collection.find_one({'name': 'dynamic'})
            if dynamic_fields_collection_in_db:
                for old_dynamic_field in dynamic_fields_collection_in_db.get('schema', {}).get('items', []):
                    if old_dynamic_field['name'] not in current_dynamic_schema_names:
                        current_dynamic_schema['items'].append(old_dynamic_field)

            # Save the new dynamic schema
            fields_collection.update({'name': 'dynamic'},
                                     {'name': 'dynamic', 'schema': current_dynamic_schema},
                                     upsert=True)

            # extend the overall schema
            current_schema = my_entity.get_fields_info('static')
            current_schema['items'].extend(current_dynamic_schema['items'])
            fields_collection.update({'name': 'parsed'},
                                     {'name': 'parsed', 'schema': current_schema},
                                     upsert=True)

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
            "plugin_subtype": self.plugin_subtype.value,
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

        if has_request_context():
            user = session.get('user', {}).get('user_name')
            user_source = session.get('user', {}).get('source')
            headers[X_UI_USER] = user
            headers[X_UI_USER_SOURCE] = user_source

        return requests.request(method, url, headers=headers, **kwargs)

    def get_available_plugins_from_core_uncached(self):
        """
        Uncached version for get_available_plugins_from_core
        """
        return requests.get(self.core_address + '/register').json()

    @cachetools.cached(cachetools.TTLCache(maxsize=1, ttl=10))
    def get_available_plugins_from_core(self):
        """
        Gets all running plugins from core by querying core/register
        """
        return self.get_available_plugins_from_core_uncached()

    def _request_db_rebuild(self, sync=True, internal_axon_ids: List[str] = None):
        """
        Requests a db rebuild
        :param sync: whether or not you want to wait until it ends
        :param internal_axon_ids: if you want to rebuild only a part of the db, give the internal_axon_ids here
        """

        def make_request():
            axon_ids = internal_axon_ids
            if axon_ids and len(axon_ids) > 50000:
                axon_ids = None
                # if you're trying to process that much you're better of with a regular rebuild

            url = f'trigger/rebuild_entity_view?blocking={sync}&priority={bool(axon_ids)}'
            return self.request_remote_plugin(url,
                                              AGGREGATOR_PLUGIN_NAME,
                                              method='post',
                                              json={
                                                  'internal_axon_ids': axon_ids
                                              }
                                              )

        if sync:
            return make_request()
        run_and_forget(make_request)

    def create_notification(self, title, content='', severity_type='info', notification_type='basic'):
        with self._get_db_connection() as db:
            return db[CORE_UNIQUE_NAME]['notifications'].insert_one(dict(who=self.plugin_unique_name,
                                                                         plugin_name=self.plugin_name,
                                                                         severity=severity_type,
                                                                         type=notification_type,
                                                                         title=title,
                                                                         content=content,
                                                                         seen=False)).inserted_id

    @cachetools.cached(cachetools.TTLCache(maxsize=10, ttl=20))
    def get_plugin_by_name(self, plugin_name, verify_single=True, verify_exists=True):
        """
        Finds plugin_name in the online plugin list
        :param plugin_name: str for plugin_name or plugin_unique_name
        :param verify_single: If True, will raise if many instances are found.
        :param verify_exists: If True, will raise if no instances are found.
        :return: if verify_single: single plugin data or None; if not verify_single: all plugin datas
        """
        # using requests directly so the api key won't be sent, so the core will give a list of the plugins
        plugins_available = self.get_available_plugins_from_core_uncached()
        found_plugins = [x
                         for x
                         in plugins_available.values()
                         if x['plugin_name'] == plugin_name or x[PLUGIN_UNIQUE_NAME] == plugin_name]

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

    @add_rule('debug/run_gc/<generation>', methods=['POST'])
    def run_gc(self, generation: int):
        """
        Runs GC for the given generation
        :param generation: generation to collect
        :return: see gc.collect
        """
        return jsonify(gc.collect(int(generation)))

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
            raise ValueError("Execution Is Disabled")
        data = {}
        if data_for_action:
            data = data_for_action.copy()

        # Building the uri for the request
        uri = f"action/{action_type}?axon_id={axon_id}"

        result = self.request_remote_plugin(uri,
                                            plugin_unique_name='execution',
                                            method='POST',
                                            data=json.dumps(data))

        try:
            result.raise_for_status()
            action_id = result.json()['action_id']
        except Exception as e:
            err_msg = f"Failed to request remote plugin, got response {result.status_code}: {result.content}"
            logger.exception(err_msg)
            raise ValueError(f"{err_msg}. Exception is {e}")

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
        return MongoClient(self.db_host, replicaset='axon-cluster', retryWrites=True,
                           username=self.db_user, password=self.db_password)

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

    def _get_appropriate_view(self, historical, entity_type: EntityType):
        if historical:
            return self._historical_entity_views_db_map[entity_type]
        return self._entity_views_db_map[entity_type]

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
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.NotRunning

    def _save_data_from_plugin(self, client_name, *args, **kwargs) -> int:
        """
        Timeout supporting facade for __do_save_data_from_plugin
        Everything is the same as there
        """
        try:
            return self.__do_save_data_from_plugin(client_name, *args, **kwargs)
        except func_timeout.exceptions.FunctionTimedOut:
            logger.exception(f"Timeout for {client_name} on {self.plugin_unique_name}")
            raise adapter_exceptions.AdapterException(f"Fetching has timed out")

    def __do_save_data_from_plugin(self, client_name, data_of_client, entity_type: EntityType,
                                   should_log_info=True) -> int:
        """
        Saves all given data from adapter (devices, users) into the DB for the given client name
        :return: Device count saved
        """
        multilocker = LazyMultiLocker()
        db_to_use = self._entity_db_map.get(entity_type)
        assert db_to_use, f"got unexpected {entity_type}"

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
                                                              args=[devices])).then(
                        lambda result: self._request_db_rebuild(sync=False)
                    ))

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
                        self._request_db_rebuild(sync=False)

            promise_all = Promise.all(promises)
            Promise.wait(promise_all, timedelta(minutes=20).total_seconds())
            if promise_all.is_rejected:
                logger.error(f"Error in insertion of {entity_type} to DB", exc_info=promise_all.reason)

            if entity_type == EntityType.Devices:
                added_pretty_ids_count = self._add_pretty_id_to_missing_adapter_devices()
                logger.info(f"{added_pretty_ids_count} devices had their pretty_id set")

            time_for_client = datetime.now() - time_before_client
            if self._notify_on_adapters is True:
                self.create_notification(
                    f"Finished aggregating {entity_type} for client {client_name}, "
                    f" aggregation took {time_for_client.seconds} seconds and returned {inserted_data_count}.")
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

        if should_log_info is True:
            logger.info(f"Finished inserting {entity_type} of client {client_name}")

        self._request_db_rebuild(sync=False)
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

    @mongo_retry()
    def __perform_tag(self, entity: EntityType, associated_adapters, name: str, data, tag_type: str, action_if_exists,
                      additional_data) -> List[dict]:
        """
        Actually performs a 'tag' operation
        See _tag for more docs
        :return: List of affected entities
        """
        _entities_db = self._entity_db_map[entity]
        if PLUGIN_UNIQUE_NAME not in additional_data or PLUGIN_NAME not in additional_data:
            additional_data[PLUGIN_UNIQUE_NAME] = self.plugin_unique_name
            additional_data[PLUGIN_NAME] = self.plugin_name

        additional_data['accurate_for_datetime'] = datetime.utcnow()
        with _entities_db.start_session() as session:
            entities_candidates_list = list(session.find({"$or": [
                {
                    'adapters': {
                        '$elemMatch': {
                            PLUGIN_UNIQUE_NAME: associated_plugin_unique_name,
                            'data.id': associated_id
                        }
                    }
                }
                for associated_plugin_unique_name, associated_id in associated_adapters
            ]}))

            if len(entities_candidates_list) != 1:
                raise TagDeviceError(f"A tag must be associated with just one adapter, "
                                     f"0 != {len(entities_candidates_list)}")

            # take (assumed single) candidate
            entities_candidate = entities_candidates_list[0]

            if tag_type == "adapterdata":
                relevant_adapter = [x for x in entities_candidate['adapters']
                                    if x[PLUGIN_UNIQUE_NAME] == associated_adapters[0][0]]
                assert relevant_adapter, "Couldn't find adapter in axon device"
                additional_data['associated_adapter_plugin_name'] = relevant_adapter[0][PLUGIN_NAME]

            if any(x['name'] == name and
                   x[PLUGIN_UNIQUE_NAME] == self.plugin_unique_name and
                   x['type'] == tag_type
                   for x
                   in entities_candidate['tags']):

                # We found the tag. If action_if_exists is replace just replace it. but if its update, lets
                # make a deep merge here.
                if action_if_exists == "update" and tag_type == "adapterdata":
                    # Take the old value of this tag.
                    final_data = [
                        x["data"] for x in entities_candidate["tags"] if
                        x["plugin_unique_name"] == self.plugin_unique_name
                        and x["type"] == "adapterdata"
                        and x["name"] == name
                    ]

                    if len(final_data) != 1:
                        msg = f"Got {name}/{tag_type} with " \
                              f"action_if_exists=update, but final_data is not of length 1: {final_data}"
                        logger.error(msg)
                        raise TagDeviceError(msg)

                    final_data = final_data[0]

                    # Merge. Note that we deep merge dicts but not lists, since lists are like fields
                    # for us (for example ip). Usually when we get some list variable we get all of it so we don't need
                    # any update things
                    data = deep_merge_only_dict(data, final_data)
                    logger.debug("action if exists on tag!")

                tag_data = {
                    'association_type': 'Tag',
                    'associated_adapters': associated_adapters,
                    "name": name,
                    "data": data,
                    "type": tag_type,
                    "entity": entity.value,
                    "action_if_exists": action_if_exists,
                    **additional_data
                }

                result = session.update_one({
                    "internal_axon_id": entities_candidate['internal_axon_id'],
                    "tags": {
                        "$elemMatch":
                            {
                                "name": name,
                                "plugin_unique_name": self.plugin_unique_name,
                                "type": tag_type
                            }
                    }
                }, {
                    "$set": {
                        "tags.$": tag_data
                    }
                })

                if result.matched_count != 1:
                    msg = f"tried to update tag {tag_data}. " \
                          f"expected matched_count == 1 but got {result.matched_count}"
                    logger.error(msg)
                    raise TagDeviceError(msg)
            elif self.plugin_name == "gui" and tag_type == 'label' and tag_type is False:
                # Gui is a special plugin. It can delete any label it wants (even if it has come from
                # another service)

                result = session.update_one({
                    "internal_axon_id": entities_candidate['internal_axon_id'],
                    "tags": {
                        "$elemMatch":
                            {
                                "name": name,
                                "type": "label"
                            }
                    }
                }, {
                    "$set": {
                        "tags.$.data": False
                    }
                })

                if result.matched_count != 1:
                    msg = f"tried to update label {tag}. expected matched_count == 1 but got {result.matched_count}"
                    logger.error(msg)
                    raise TagDeviceError(msg)

            else:
                tag_data = {
                    'association_type': 'Tag',
                    'associated_adapters': associated_adapters,
                    "name": name,
                    "data": data,
                    "type": tag_type,
                    "entity": entity.value,
                    "action_if_exists": action_if_exists,
                    **additional_data
                }

                result = session.update_one(
                    {"internal_axon_id": entities_candidate['internal_axon_id']},
                    {
                        "$addToSet": {
                            "tags": tag_data
                        }
                    })

                if result.modified_count != 1:
                    msg = f"tried to add tag {tag_data}. expected modified_count == 1 but got {result.modified_count}"
                    logger.error(msg)
                    raise TagDeviceError(msg)
        return entities_candidates_list

    def _tag(self, entity: EntityType, identity_by_adapter, name, data, tag_type, action_if_exists,
             client_used,
             additional_data) -> List[dict]:
        """ Function for tagging adapter devices.
        This function will tag a wanted device. The tag will be related only to this adapter
        :param identity_by_adapter: a list of tuples of (adapter_unique_name, unique_id).
                                           e.g. [("ad-adapter-1234", "CN=EC2AMAZ-3B5UJ01,OU=D....")]
        :param name: the name of the tag. should be a string.
        :param data: the data of the tag. could be any object.
        :param tag_type: the type of the tag. "label" for a regular tag, "data" for a data tag.
        :param entity: "devices" or "users" -> what is the entity we are tagging.
        :param action_if_exists: "replace" to replace the tag, "update" to update the tag (in case its a dict)
        :param client_used: an optional parameter to indicate client_used. This is important since we show this in
                            the gui (we can know where the data came from)
        :param additional_data: additional data to the dict sent to the aggregator
        :return: List of affected entities
        """

        assert action_if_exists == "replace" or (action_if_exists == "update" and tag_type == "adapterdata") or \
            (action_if_exists == 'merge' and tag_type == 'data')
        additional_data = additional_data or {}

        if client_used is not None:
            assert type(client_used) == str
            additional_data['client_used'] = client_used

        return self.__perform_tag(entity, identity_by_adapter, name, data, tag_type, action_if_exists, additional_data)

    @mongo_retry()
    def link_adapters(self, entity: EntityType, correlation: CorrelationResult, rebuild: bool = True):
        """
        Performs a correlation between the entities given by 'correlation'
        :param entity: The entity type to use
        :param correlation: The information of the correlation - see definition of CorrelationResult
        :param rebuild: Whether or not to rebuild the entities
        """
        _entities_db = self._entity_db_map[entity]
        with _entities_db.start_session() as session:
            try:
                with session.start_transaction():
                    entities_candidates = list(session.find({"$or": [
                        {
                            'adapters': {
                                '$elemMatch': {
                                    PLUGIN_UNIQUE_NAME: associated_plugin_unique_name,
                                    'data.id': associated_id
                                }
                            }
                        }
                        for associated_plugin_unique_name, associated_id in correlation.associated_adapters
                    ]}))

                    if len(entities_candidates) == 0:
                        raise CorrelateException(f"No entities given or all entities given don't exist. "
                                                 f"Associated adapters: {correlation.associated_adapters}")
                    # in this case, we need to link (i.e. "merge") all entities_candidates
                    # if there's only one, then the link is either associated only to
                    # one entity (which is as irrelevant as it gets)
                    # or all the entities are already linked. In any case, if a real merge isn't done
                    # it means someone made a mistake.
                    if len(entities_candidates) != 2:
                        logger.warning(f"{len(entities_candidates)} != 2, entities_candidates: ")
                        raise CorrelateException(f'Link with wrong number of devices '
                                                 f'{len(correlation.associated_adapters)}')

                    collected_adapter_entities = [axonius_entity['adapters'] for axonius_entity in entities_candidates]
                    all_unique_adapter_entities_data = [v for d in collected_adapter_entities for v in d]
                    recalculate_adapter_oldness(all_unique_adapter_entities_data)

                    # Get all tags from all devices. If we have the same tag name and issuer, prefer the newest.
                    # a tag is the same tag, if it has the same plugin_unique_name and name.
                    def keyfunc(tag):
                        return tag['plugin_unique_name'], tag['name']

                    # first, lets get all tags and have them sorted. This will make the same tags be consecutive.
                    all_tags = sorted((t for dc in entities_candidates for t in dc['tags']), key=keyfunc)
                    # now we have the same tags ordered consecutively. so we want to group them, so that we
                    # would have duplicates of the same tag in their identity key.
                    all_tags = groupby(all_tags, keyfunc)

                    # Now we have them grouped by, lets select only the one which is the newest, or merge
                    tags_for_new_device = {}
                    for tag_key, duplicated_tags in all_tags:
                        duplicated_tags = list(duplicated_tags)
                        tags_for_new_device[tag_key] = max(duplicated_tags,
                                                           key=lambda tag: tag['accurate_for_datetime'])
                        # The data tag with action 'merge' should aggregate all the data from merge adapter entities
                        # AX-2253
                        if tags_for_new_device[tag_key]['action_if_exists'] == 'merge':
                            tags_for_new_device[tag_key]['data'] = [item for tag in duplicated_tags for item in
                                                                    tag['data']]

                    internal_axon_id = uuid.uuid4().hex

                    # now, let us delete all other AxoniusDevices
                    session.delete_many({'$or':
                                         [
                                             {'internal_axon_id': axonius_entity['internal_axon_id']}
                                             for axonius_entity in entities_candidates
                                         ]
                                         })
                    session.insert_one({
                        "internal_axon_id": internal_axon_id,
                        "accurate_for_datetime": datetime.now(),
                        "adapters": all_unique_adapter_entities_data,
                        ADAPTERS_LIST_LENGTH: len(set([x[PLUGIN_NAME] for x in all_unique_adapter_entities_data])),
                        "tags": list(tags_for_new_device.values())  # Turn it to a list
                    })
            except CorrelateException as e:
                logger.exception("Unlink logic exception")
                raise

        if rebuild:
            self._request_db_rebuild(sync=False,
                                     internal_axon_ids=[x['internal_axon_id'] for x in entities_candidates])

    @mongo_retry()
    def unlink_adapter(self, entity: EntityType, plugin_unique_name: str, adapter_id: str):
        """
        Unlinks a specific adapter from its axonius device
        :param entity: The entity type to use
        :param plugin_unique_name: The plugin unique name of the given adapter
        :param adapter_id: The ID of the given adapt
        """
        _entities_db = self._entity_db_map[entity]
        with _entities_db.start_session() as session:
            with session.start_transaction():
                self.__perform_unlink_with_session(adapter_id, plugin_unique_name, session)

    @staticmethod
    def __perform_unlink_with_session(adapter_id: str, plugin_unique_name: str,
                                      session, entity_to_split=None):
        """
        Perform an unlink given a session on a particular adapter entity
        :param adapter_id: the id of the adapter to unlink
        :param plugin_unique_name: the plugin unique name of the adapter
        :param session: the session to use, this also implies the DB to use
        :param entity_to_split: if not none, uses this as the entity (optimization)
        :return:
        """
        entity_to_split = entity_to_split or session.find_one({
            'adapters': {
                '$elemMatch': {
                    PLUGIN_UNIQUE_NAME: plugin_unique_name,
                    'data.id': adapter_id
                }
            }
        })
        if not entity_to_split:
            raise CorrelateException(f"Could not find given entity {plugin_unique_name}:{adapter_id}")
        if len(entity_to_split['adapters']) == 1:
            raise CorrelateException("Only one adapter entity in axonius entity, can't split that")
        internal_axon_id = uuid.uuid4().hex
        adapter_to_extract = [x for x in entity_to_split['adapters'] if
                              x[PLUGIN_UNIQUE_NAME] == plugin_unique_name and
                              x['data']['id'] == adapter_id]
        if len(adapter_to_extract) != 1:
            raise CorrelateException(f'Weird entity: {entity_to_split}')
        new_axonius_entity = {
            "internal_axon_id": internal_axon_id,
            "accurate_for_datetime": datetime.now(),
            "adapters": adapter_to_extract,
            "tags": []
        }

        # figure out which adapters should stay on the current entity (axonius_entity_to_split - remaining adapters)
        # and those that should move to the new axonius entity
        remaining_adapters = set(x[PLUGIN_UNIQUE_NAME] for x in entity_to_split['adapters']) - \
            {adapter_to_extract[0][PLUGIN_UNIQUE_NAME]}
        # figure out for each tag G (in the current entity, i.e. axonius_entity_to_split)
        # whether any of G.associated_adapters is in the `associated_adapters`, i.e.
        # whether G should be a part of the new axonius entity.
        # clarification: G should be a part of the new axonius entity if any of G.associated_adapters
        # is also part of the new axonius entity
        for tag in entity_to_split['tags']:
            for tag_plugin_unique_name, tag_adapter_id in tag['associated_adapters']:
                if tag_plugin_unique_name == plugin_unique_name and tag_adapter_id == adapter_id:
                    newtag = dict(tag)
                    # if the tags moves/copied to the new entity, it should 'forget' it's old
                    # associated adapters, because most of the them stay in the old device,
                    # and so the new G.associated_adapters are the associated_adapters
                    # that are also part of the new axonius entity
                    newtag['associated_adapters'] = [tag_plugin_unique_name, tag_adapter_id]
                    new_axonius_entity['tags'].append(newtag)
        # remove the adapters one by one from the DB, and also keep track in memory
        adapter_entities_left = list(entity_to_split['adapters'])

        for adapter_to_remove_from_old in new_axonius_entity['adapters']:
            adapter_entities_left.remove(adapter_to_remove_from_old)

        recalculate_adapter_oldness(adapter_entities_left)
        session.update_one({
            'internal_axon_id': entity_to_split['internal_axon_id']
        },
            {
                '$set': {
                    'adapters': adapter_entities_left
                }
        })

        # generate a list of (unique_plugin_name, id) from the adapter entities left
        adapter_entities_left_by_id = [
            [adapter[PLUGIN_UNIQUE_NAME], adapter['data']['id']]
            for adapter
            in adapter_entities_left
        ]
        # the old entity might and might not keep the tag:
        # if the tag contains an associated_adapter that is also part of the old entity
        # - then this tag is also associated with the old entity
        # if it does not
        # - this this tag is removed from the old entity
        # so now we generate a list of all tags that must be removed from the old entity
        # a tag will be removed if all of its associated_adapters are not in any of the
        # adapter entities left in the old device, i.e. all of its associated_adapters have moved
        pull_those = [tag_from_old
                      for tag_from_old
                      in entity_to_split['tags']
                      if all(assoc_adapter not in adapter_entities_left_by_id
                             for assoc_adapter
                             in tag_from_old['associated_adapters'])]
        set_query = {
            ADAPTERS_LIST_LENGTH: len(set(remaining_adapters))
        }
        if pull_those:
            pull_query = {
                'tags': {
                    "$or": [
                        {
                            PLUGIN_UNIQUE_NAME: pull_this_tag[PLUGIN_UNIQUE_NAME],
                            "name": pull_this_tag['name']
                        }
                        for pull_this_tag
                        in pull_those
                    ]

                }
            }
            full_query = {
                "$pull": pull_query,
                "$set": set_query
            }
        else:
            full_query = {
                "$set": set_query
            }
        session.update_many({'internal_axon_id': entity_to_split['internal_axon_id']},
                            full_query)
        new_axonius_entity[ADAPTERS_LIST_LENGTH] = len(
            set([x[PLUGIN_NAME] for x in new_axonius_entity['adapters']]))

        recalculate_adapter_oldness(new_axonius_entity['adapters'])
        session.insert_one(new_axonius_entity)

    def __archive_axonius_device(self, plugin_unique_name, device_id, db_to_use, session=None):
        """
        Finds the axonius device with the given plugin_unique_name and device id,
        assumes that the axonius device has only this single adapter device.

        If you want to delete an adapter entity use delete_adapter_entity

        writes the device to the archive db, then deletes it
        """
        axonius_device = db_to_use.find_one_and_delete({
            'adapters': {
                '$elemMatch': {
                    PLUGIN_UNIQUE_NAME: plugin_unique_name,
                    'data.id': device_id
                }
            }
        }, session=session)
        if axonius_device is None:
            logger.error(f"Tried to archive nonexisting device: {plugin_unique_name}: {device_id}")
            return False

        axonius_device['archived_at'] = datetime.utcnow()
        self.aggregator_db_connection['old_device_archive'].insert_one(axonius_device, session=session)
        return True

    @mongo_retry()
    def delete_adapter_entity(self, entity: EntityType, plugin_unique_name: str, adapter_id: str):
        """
        Delete an adapter entity from the DB
        :param entity: The entity type to use
        :param plugin_unique_name: The plugin unique name of the given adapter
        :param adapter_id: The ID of the given adapt
        """
        _entities_db = self._entity_db_map[entity]
        with _entities_db.start_session() as session:
            with session.start_transaction():
                axonius_entity = session.find_one({
                    'adapters': {
                        '$elemMatch': {
                            PLUGIN_UNIQUE_NAME: plugin_unique_name,
                            'data.id': adapter_id
                        }
                    }
                })
                if not axonius_entity:
                    return  # deleting an empty adapter shouldn't be hard

                # if the condition below isn't met it means
                # that the current adapterentity is the last adapter in the axoniusentity
                # in which case - there is no reason to unlink it, just to delete it
                if len(axonius_entity['adapters']) > 1:
                    self.__perform_unlink_with_session(adapter_id, plugin_unique_name, session,
                                                       entity_to_split=axonius_entity)
                self.__archive_axonius_device(plugin_unique_name, adapter_id, _entities_db, session)

    def add_many_labels_to_entity(self, entity: EntityType, identity_by_adapter, labels, are_enabled=True,
                                  rebuild: bool = True) -> List[dict]:
        """
        Tag many devices with many tags. if is_enabled = False, the labels are grayed out.
        :param rebuild: Whether or not to trigger a rebuild afterwards
        :return: List of affected entities
        """

        def perform_many_tags():
            for label in labels:
                for specific_identity in identity_by_adapter:
                    yield from self.add_label_to_entity(entity, [specific_identity], label, are_enabled,
                                                        rebuild=False)

        result = list(perform_many_tags())
        if result and rebuild:
            self._request_db_rebuild(sync=True, internal_axon_ids=[x['internal_axon_id'] for x in result])
        return result

    def add_label_to_entity(self, entity: EntityType, identity_by_adapter, label, is_enabled=True,
                            additional_data={},
                            rebuild: bool = True) -> List[dict]:
        """
        A shortcut to __tag with type "label" . if is_enabled = False, the label is grayed out.
        :param rebuild: Whether or not to trigger a rebuild afterwards
        :return: List of affected entities
        """
        # all labels belong to GUI
        additional_data[PLUGIN_UNIQUE_NAME], additional_data[PLUGIN_NAME] = GUI_NAME, GUI_NAME

        result = self._tag(entity, identity_by_adapter, label, is_enabled, "label", "replace", None,
                           additional_data)
        if result and rebuild:
            self._request_db_rebuild(sync=True, internal_axon_ids=[x['internal_axon_id'] for x in result])
        return result

    def add_data_to_entity(self, entity: EntityType, identity_by_adapter, name, data, additional_data={},
                           action_if_exists='replace',
                           rebuild: bool = True) -> List[dict]:
        """
        A shortcut to __tag with type "data"
        :param rebuild: Whether or not to trigger a rebuild afterwards
        :return: List of affected entities
        """
        result = self._tag(entity, identity_by_adapter, name, data, "data", action_if_exists, None, additional_data)
        if result and rebuild:
            self._request_db_rebuild(sync=True, internal_axon_ids=[x['internal_axon_id'] for x in result])
        return result

    def add_adapterdata_to_entity(self, entity: EntityType, identity_by_adapter, data,
                                  action_if_exists="replace", client_used=None, additional_data={},
                                  rebuild: bool = True) -> List[dict]:
        """
        A shortcut to __tag with type "adapterdata"
        :param rebuild: Whether or not to trigger a rebuild afterwards
        :return: List of affected entities
        """
        result = self._tag(entity, identity_by_adapter, self.plugin_unique_name, data, "adapterdata",
                           action_if_exists, client_used, additional_data)
        if result and rebuild:
            self._request_db_rebuild(sync=True, internal_axon_ids=[x['internal_axon_id'] for x in result])
        return result

    @add_rule("update_config", methods=['POST'], should_authenticate=False)
    def update_config(self):
        return self._update_config_inner()

    def _update_config_inner(self):
        self.renew_config_from_db()
        self.__renew_global_settings_from_db()
        return ""

    def create_fresh_service_incident(self, subject, description, priority, email):
        """
        Create new incident on alerts page.
        :param description: string - html content of the ticket
        :param subject: string - subject of the ticket
        :param email: string - email address of the requester
        :param priority: integer - priority of the ticket (1 (low) - 4 (urgent))
        :return:
        """
        fresh_service_settings = self._fresh_service_settings

        if email:
            ticket_email = email
        else:
            ticket_email = fresh_service_settings['admin_email']

        # we make status = 2 because this denotes that the ticket must be opened. Also manually setting priority
        # as medium to begin
        fresh_service_dict = {'subject': subject,
                              'description': description,
                              'email': ticket_email,
                              'priority': priority,
                              'status': 2
                              }

        if fresh_service_settings['enabled']:
            try:
                fresh_service_connection = FreshServiceConnection(domain=fresh_service_settings['domain'],
                                                                  apikey=fresh_service_settings['api_key'])

                with fresh_service_connection:
                    fresh_service_connection.create_fresh_service_incident(dict_data=fresh_service_dict)
            except Exception:
                logger.exception(f'Got exception creating Fresh Service incident with {fresh_service_dict}')

    def create_service_now_incident(self, short_description, description, impact):
        service_now_dict = {'short_description': short_description, 'description': description, 'impact': impact}
        service_now_settings = self._service_now_settings
        if service_now_settings['enabled'] is True:
            try:
                if service_now_settings['use_adapter'] is True:
                    self.request_remote_plugin('create_incident', 'service_now_adapter', 'post', json=service_now_dict)
                else:
                    service_now_connection = ServiceNowConnection(domain=service_now_settings['domain'],
                                                                  verify_ssl=service_now_settings.get("verify_ssl"),
                                                                  username=service_now_settings.get("username"),
                                                                  password=service_now_settings.get("password"),
                                                                  https_proxy=service_now_settings.get("https_proxy"))
                    with service_now_connection:
                        service_now_connection.create_service_now_incident(service_now_dict)
            except Exception:
                logger.exception(f"Got exception creating ServiceNow incident wiht {service_now_dict}")

    def create_service_now_computer(self, name, mac_address=None, ip_address=None,
                                    manufacturer=None, os=None, serial_number=None):
        connection_dict = dict()
        if name is None or name == "":
            return
        connection_dict["name"] = name
        if mac_address is not None and mac_address != "":
            connection_dict["mac_address"] = mac_address
        if ip_address is not None and ip_address != "":
            connection_dict["ip_address"] = ip_address
        if manufacturer is not None and manufacturer != "":
            connection_dict["manufacturer"] = manufacturer
        if serial_number is not None and serial_number != "":
            connection_dict["serial_number"] = serial_number
        if os is not None and os != "":
            connection_dict["os"] = os
        serive_now_settings = self._service_now_settings
        if serive_now_settings['enabled'] is True:
            if serive_now_settings['use_adapter'] is True:
                self.request_remote_plugin('create_computer', 'service_now_adapter', 'post', json=connection_dict)
            else:
                try:
                    service_now_connection = ServiceNowConnection(domain=serive_now_settings['domain'],
                                                                  verify_ssl=serive_now_settings.get("verify_ssl"),
                                                                  username=serive_now_settings.get("username"),
                                                                  password=serive_now_settings.get("password"),
                                                                  https_proxy=serive_now_settings.get("https_proxy"))
                    with service_now_connection:
                        service_now_connection.create_service_now_computer(connection_dict)
                except Exception:
                    logger.exception(f"Got exception creating ServiceNow computer with {name}")

    def send_syslog_message(self, message, log_level):
        syslog_settings = self._syslog_settings
        if syslog_settings['enabled'] is True:
            syslog_logger = logging.getLogger("axonius.syslog")
            # Starting the messages with the tag Axonius
            formatted_message = f'Axonius:{message}'
            getattr(syslog_logger, log_level)(formatted_message)

    @property
    def mail_sender(self):
        email_settings = self._email_settings
        if email_settings['enabled'] is True:
            return EmailServer(email_settings['smtpHost'], email_settings['smtpPort'],
                               email_settings.get('smtpUser'), email_settings.get('smtpPassword'),
                               self._grab_file_contents(email_settings.get('smtpKey'), stored_locally=False),
                               self._grab_file_contents(email_settings.get('smtpCert'), stored_locally=False),
                               source=email_settings.get('sender_address')
                               if email_settings.get('sender_address') else None)
        return None

    # Global settings
    # These are settings which are shared between all plugins. For example, all plugins should use the same
    # mail server when doing reports.
    # Adding or changing a settings requires a full restart of the system
    # and making sure you don't break a setting somebody else uses.

    def __renew_global_settings_from_db(self):
        config = self._get_db_connection()[CORE_UNIQUE_NAME][CONFIGURABLE_CONFIGS_COLLECTION].find_one(
            {'config_name': 'CoreService'})['config']
        logger.info(f"Loading global config: {config}")
        self._email_settings = config['email_settings']
        self._notify_on_adapters = config[NOTIFICATIONS_SETTINGS].get(NOTIFY_ADAPTERS_FETCH)
        self._execution_enabled = config['execution_settings']['enabled']
        self._should_use_axr = config['execution_settings']['should_use_axr']
        self._pm_rpc_enabled = config['execution_settings']['pm_rpc_enabled']
        self._pm_smb_enabled = config['execution_settings']['pm_smb_enabled']
        self._reg_check_exists = config['execution_settings'].get('reg_check_exists')

        current_syslog = getattr(self, '_syslog_settings', None)
        if current_syslog != config['syslog_settings']:
            logger.info('new syslog settings arrived')
            self.__create_syslog_handler(config['syslog_settings'])
            self._syslog_settings = config['syslog_settings']
        else:
            self._syslog_settings = current_syslog

        self._service_now_settings = config['service_now_settings']
        self._fresh_service_settings = config['fresh_service_settings']

        if not config[MAINTENANCE_SETTINGS][ANALYTICS_SETTING]:
            config[MAINTENANCE_SETTINGS][TROUBLESHOOTING_SETTING] = False

        self._maintenance_settings = config[MAINTENANCE_SETTINGS]

        self._get_db_connection()[CORE_UNIQUE_NAME][CONFIGURABLE_CONFIGS_COLLECTION].update_one(
            filter={'config_name': 'CoreService'}, update={"$set": {"config": config}})

        logger.info(self._maintenance_settings)

    def __create_syslog_handler(self, syslog_settings: dict):
        """
        Replaces the syslog handler used with the provided
        """
        try:
            # No syslog handler defined yet or settings changed.
            # We should replace the current handler with a new one.
            logger.info("Initializing new handler to syslog logger (deleting old if exist)")
            syslog_logger = logging.getLogger("axonius.syslog")
            syslog_logger.handlers = []  # Removing all previous handlers
            # Making a new handler with most up to date settings
            use_ssl = SSLState[syslog_settings['use_ssl']]
            if use_ssl != SSLState.Unencrypted:
                cert_file = self._grab_file_contents(syslog_settings.get('cert_file'))
                ssl_kwargs = dict(
                    cert_reqs=ssl.CERT_REQUIRED if use_ssl == SSLState.Verified else ssl.CERT_NONE,
                    ssl_version=ssl.PROTOCOL_TLS,
                    ca_certs=cert_file.name if cert_file else None
                )
                syslog_handler = TLSSysLogHandler(address=(syslog_settings['syslogHost'],
                                                           syslog_settings.get('syslogPort',
                                                                               6514)),
                                                  facility=logging.handlers.SysLogHandler.LOG_DAEMON,
                                                  ssl_kwargs=ssl_kwargs)
            else:
                syslog_handler = logging.handlers.SysLogHandler(address=(syslog_settings['syslogHost'],
                                                                         syslog_settings.get('syslogPort',
                                                                                             logging.handlers.SYSLOG_UDP_PORT)),
                                                                facility=logging.handlers.SysLogHandler.LOG_DAEMON)
            syslog_handler.setLevel(logging.INFO)
            syslog_logger.addHandler(syslog_handler)
        except Exception:
            logger.exception('Failed setting up syslog handler, no syslog handler has been set up')

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
                        },
                        *COMMON_SSL_CONFIG_SCHEMA
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
                            "title": "Use ServiceNow",
                            "type": "bool"
                        },
                        {
                            "name": "use_adapter",
                            "title": "Use ServiceNow Adapter",
                            "type": "bool"
                        },
                        {
                            "name": "domain",
                            "title": "ServiceNow Domain",
                            "type": "string"
                        },
                        {
                            "name": "username",
                            "title": "User Name",
                            "type": "string"
                        },
                        {
                            "name": "password",
                            "title": "Password",
                            "type": "string",
                            "format": "password"
                        },
                        {
                            "name": "verify_ssl",
                            "title": "Verify SSL",
                            "type": "bool"
                        },
                        {
                            "name": "https_proxy",
                            "title": "HTTPS Proxy",
                            "type": "string"
                        }
                    ],
                    "required": [
                        "enabled"
                    ],
                    "type": "array",
                    "name": "service_now_settings",
                    "title": "ServiceNow Settings",
                },
                {
                    "items": [
                        {
                            "name": "enabled",
                            "title": "Use FreshService",
                            "type": "bool"
                        },
                        {
                            "name": "domain",
                            "title": "FreshService Domain",
                            "type": "string"
                        },
                        {
                            "name": "api_key",
                            "title": "API Key",
                            "type": "string",
                            "format": "password"
                        },
                        {
                            "name": "admin_email",
                            "title": "Admin Email",
                            "type": "string"
                        }
                    ],
                    "required": [
                        "enabled",
                        "domain",
                        "api_key",
                        "admin_email"
                    ],
                    "type": "array",
                    "name": "fresh_service_settings",
                    "title": "FreshService Settings",
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
                            "type": "string",
                            "format": "password"
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
                        },
                        {
                            'name': 'sender_address',
                            'title': 'Sender Address',
                            'type': 'string'
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
                        },
                        {
                            "name": "should_use_axr",
                            "title": "Use Fast Execution Method (BETA)",
                            "type": "bool",
                            "required": True
                        },
                        {
                            "name": "pm_rpc_enabled",
                            "title": "Patch Management Using RPC (Online)",
                            "type": "bool",
                            "required": True
                        },
                        {
                            "name": "pm_smb_enabled",
                            "title": "Patch Management Using SMB (Online)",
                            "type": "bool",
                            "required": True
                        },
                        {
                            'name': 'reg_check_exists',
                            "title": "Validated Registry Keys",
                            "type": "array",
                            "required": True,
                            'items': {
                                'type': 'array',
                                'items': [
                                    {
                                        'type': 'string',
                                        'name': 'key_name',
                                        'title': 'Reg Key Name'
                                    }
                                ]
                            }
                        }
                    ],
                    "name": "execution_settings",
                    "title": "Execution Settings",
                    "type": "array"
                },
                {
                    "items": [
                        {
                            "name": ANALYTICS_SETTING,
                            "title": "Anonymized Analytics - Warning: turning off this feature prevents Axonius from \
                            proactively detecting issues and notifying about errors.",
                            "type": "bool"
                        },
                        {
                            "name": TROUBLESHOOTING_SETTING,
                            "title": "Remote Support - Warning: turning off this feature prevents Axonius from \
                            updating the system and can lead to slower issue resolution time. \
                            Note: anonymized analytics must be enabled for remote support",
                            "type": "bool"
                        }
                    ],
                    "name": MAINTENANCE_SETTINGS,
                    "title": "Maintenance Settings",
                    "type": "array",
                    "required": [ANALYTICS_SETTING, TROUBLESHOOTING_SETTING]
                },
                {
                    'name': PROXY_SETTINGS,
                    'title': 'Proxy settings',
                    'type': 'array',
                    'required': ['proxy_addr', 'proxy_port'],
                    'items': [
                        {
                            "name": "enabled",
                            "title": "Proxy Enabled",
                            "type": "bool",
                            "required": True
                        },
                        {
                            'name': PROXY_ADDR,
                            'title': 'Proxy address',
                            'type': 'string'
                        },
                        {
                            'name': PROXY_PORT,
                            'title': 'Proxy port',
                            'type': 'number'
                        },
                        {
                            'name': PROXY_USER,
                            'title': 'Proxy username',
                            'type': 'string'
                        },
                        {
                            'name': PROXY_PASSW,
                            'title': 'Proxy password',
                            'type': 'string'
                        }
                    ]
                },
                {
                    "items": [
                        {
                            "name": NOTIFY_ADAPTERS_FETCH,
                            "title": "Notify On Adapters Fetch",
                            "type": "bool"
                        }
                    ],
                    "name": NOTIFICATIONS_SETTINGS,
                    "title": "Notifications Settings",
                    "type": "array",
                    "required": [NOTIFY_ADAPTERS_FETCH]
                },
            ],
            'pretty_name': 'Global Configuration',
            'type': 'array'
        }

    @staticmethod
    def global_settings_defaults():
        return {
            "service_now_settings": {
                "enabled": False,
                "use_adapter": False,
                "domain": None,
                "username": None,
                "password": None,
                "https_proxy": None,
                "verify_ssl": True
            },
            'fresh_service_settings': {
                'enabled': False,
                'domain': None,
                'api_key': None,
                'admin_email': None
            },
            "email_settings": {
                "enabled": False,
                "smtpHost": None,
                "smtpPort": None,
                "smtpUser": None,
                "smtpPassword": None,
                "smtpCert": None,
                "smtpKey": None,
                'sender_address': None
            },
            "execution_settings": {
                "enabled": False,
                "should_use_axr": False,
                "pm_rpc_enabled": False,
                "pm_smb_enabled": False,
                'reg_check_exists': None,
            },
            "syslog_settings": {
                "enabled": False,
                "syslogHost": None,
                "syslogPort": logging.handlers.SYSLOG_UDP_PORT,
                **COMMON_SSL_CONFIG_SCHEMA_DEFAULTS
            },
            MAINTENANCE_SETTINGS: {
                ANALYTICS_SETTING: True,
                TROUBLESHOOTING_SETTING: True
            },
            PROXY_SETTINGS: {
                'enabled': False,
                PROXY_ADDR: '',
                PROXY_PORT: 8080,
                PROXY_USER: '',
                PROXY_PASSW: ''
            },
            NOTIFICATIONS_SETTINGS: {
                NOTIFY_ADAPTERS_FETCH: False
            }
        }
