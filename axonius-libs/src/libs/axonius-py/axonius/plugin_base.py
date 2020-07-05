"""PluginBase.py: Implementation of the base class to be inherited by other plugins."""
# pylint: disable=W0402, bad-option-value, unnecessary-comprehension, import-error, C0302
import base64
import concurrent
import concurrent.futures
import configparser
import functools
import gc
import hashlib
import json
import logging
import logging.handlers
import multiprocessing
import os
import secrets
import socket
import ssl
import string
import subprocess
import sys
import threading
import time
import traceback
import uuid
from abc import ABC
from collections import defaultdict
from datetime import datetime, timedelta
from itertools import groupby, chain
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

import pymongo
from urllib3.exceptions import ProtocolError
# bson is requirement of mongo and its not recommended to install it manually
from bson import ObjectId, json_util
# pylint: disable=ungrouped-imports
from pymongo import ReplaceOne
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, OperationFailure
import cachetools
import func_timeout
import requests
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger
from flask import (Flask, Response, has_request_context, jsonify, request,
                   session)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from funcy import chunks
from jira import JIRA
from namedlist import namedtuple
from promise import Promise
from retrying import retry
from tlssyslog import TLSSysLogHandler

import axonius.entities
from axonius.adapter_exceptions import AdapterException, TagDeviceError
from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.clients.abstract.abstract_vault_connection import AbstractVaultConnection, VaultProvider
from axonius.clients.cyberark_vault.connection import CyberArkVaultConnection
from axonius.clients.opsgenie.connection import OpsgenieConnection
from axonius.clients.opsgenie.consts import OPSGENIE_DEFAULT_DOMAIN
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.thycotic_vault.connection import ThycoticVaultConnection
from axonius.consts.adapter_consts import IGNORE_DEVICE, CLIENT_ID, CONNECTION_LABEL
from axonius.consts.core_consts import ACTIVATED_NODE_STATUS, CORE_CONFIG_NAME
from axonius.consts.gui_consts import (CORRELATION_REASONS,
                                       HAS_NOTES,
                                       FEATURE_FLAGS_CONFIG,
                                       GETTING_STARTED_CHECKLIST_SETTING,
                                       HASH_SALT, CloudComplianceNames,
                                       FeatureFlagsNames)
from axonius.consts.plugin_consts import (
    ADAPTERS_ERRORS_MAIL_ADDRESS, ADAPTERS_ERRORS_WEBHOOK_ADDRESS,
    ADAPTERS_LIST_LENGTH, AGGREGATION_SETTINGS, AGGREGATOR_PLUGIN_NAME,
    ALLOW_SERVICE_NOW_BY_NAME_ONLY, AXONIUS_DNS_SUFFIX, AUDIT_COLLECTION,
    CORE_UNIQUE_NAME, CORRELATE_AD_DISPLAY_NAME, CORRELATE_AD_SCCM, CORRELATE_AWS_USERNAME,
    CORRELATE_BY_AZURE_AD_NAME_ONLY, CORRELATE_BY_EMAIL_PREFIX,
    CORRELATE_BY_SNOW_MAC, CORRELATE_SNOW_NO_DASH, CORRELATE_BY_USERNAME_DOMAIN_ONLY,
    CORRELATE_GLOBALY_ON_HOSTNAME, CORRELATION_SCHEDULE, CORRELATION_SCHEDULE_ENABLED,
    CORRELATION_SCHEDULE_HOURS_INTERVAL, CORRELATION_SETTINGS,
    CORRELATE_PUBLIC_IP_ONLY, CSV_FULL_HOSTNAME, DB_KEY_ENV_VAR_NAME,
    DEFAULT_SOCKET_READ_TIMEOUT, DEFAULT_SOCKET_RECV_TIMEOUT,
    EXECUTION_PLUGIN_NAME, FETCH_EMPTY_VENDOR_SOFTWARE_VULNERABILITES,
    FETCH_TIME, FIRST_FETCH_TIME, GLOBAL_KEYVAL_COLLECTION,
    GUI_PLUGIN_NAME, HEAVY_LIFTING_PLUGIN_NAME,
    KEYS_COLLECTION, MAX_WORKERS, NODE_ID, NODE_ID_ENV_VAR_NAME,
    NODE_INIT_NAME, NODE_USER_PASSWORD, NOTIFICATIONS_SETTINGS,
    PASSWORD_PROTECTION_BY_USERNAME,
    PASSWORD_LENGTH_SETTING, PASSWORD_MANGER_THYCOTIC_SS_VAULT, PASSWORD_MANGER_ENUM,
    PASSWORD_MIN_LOWERCASE, PASSWORD_MIN_NUMBERS, PASSWORD_MANGER_ENABLED,
    PASSWORD_MIN_SPECIAL_CHARS, PASSWORD_MIN_UPPERCASE,
    PASSWORD_PROTECTION_ALLOWED_RETRIES, PASSWORD_PROTECTION_LOCKOUT_MIN,
    PASSWORD_SETTINGS, PASSWORD_BRUTE_FORCE_PROTECTION, PLUGIN_NAME,
    PASSWORD_PROTECTION_BY_IP, PLUGIN_UNIQUE_NAME, PROXY_ADDR,
    PROXY_PASSW, PROXY_PORT, PROXY_SETTINGS, PROXY_USER, PROXY_VERIFY,
    RESET_PASSWORD_SETTINGS, RESET_PASSWORD_LINK_EXPIRATION,
    REPORTS_PLUGIN_NAME, SOCKET_READ_TIMEOUT, STATIC_ANALYSIS_SETTINGS,
    THYCOTIC_SS_HOST, THYCOTIC_SS_PORT, THYCOTIC_SS_PASSWORD, THYCOTIC_SS_VERIFY_SSL,
    THYCOTIC_SS_USERNAME, PASSWORD_MANGER_CYBERARK_VAULT, CYBERARK_APP_ID,
    CYBERARK_CERT_KEY, CYBERARK_DOMAIN, CYBERARK_PORT, UPDATE_CLIENTS_STATUS,
    UPPERCASE_HOSTNAMES, VAULT_SETTINGS, VOLATILE_CONFIG_PATH, X_UI_USER, X_UI_USER_SOURCE, DEVICE_LOCATION_MAPPING,
    CSV_IP_LOCATION_FILE, TUNNEL_SETTINGS, TUNNEL_EMAILS_RECIPIENTS, TUNNEL_PROXY_ADDR, TUNNEL_PROXY_PORT,
    TUNNEL_PROXY_USER, TUNNEL_PROXY_PASSW, TUNNEL_PROXY_SETTINGS, DISCOVERY_CONFIG_NAME, ENABLE_CUSTOM_DISCOVERY,
    NOTES_DATA_TAG)
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.consts.system_consts import GENERIC_ERROR_MESSAGE
from axonius.db.db_client import get_db_client
from axonius.db.files import DBFileHelper
from axonius.devices import deep_merge_only_dict
from axonius.devices.device_adapter import LAST_SEEN_FIELD, DeviceAdapter
from axonius.email_server import EmailServer
from axonius.entities import EntityType
from axonius.irequests import IRequests
from axonius.logging.audit_helper import (AuditCategory, AuditAction, AuditType)
from axonius.logging.logger import create_logger
from axonius.mixins.configurable import Configurable
from axonius.mixins.feature import Feature
from axonius.modules.axonius_plugins import AxoniusPlugins
from axonius.plugin_exceptions import PluginNotFoundException, SessionInvalid
from axonius.profiling.memory_tracing import run_memory_tracing
from axonius.types.correlation import (MAX_LINK_AMOUNT, CorrelateException,
                                       CorrelationResult)
from axonius.types.ssl_state import (COMMON_SSL_CONFIG_SCHEMA,
                                     COMMON_SSL_CONFIG_SCHEMA_DEFAULTS,
                                     MANDATORY_SSL_CONFIG_SCHEMA,
                                     MANDATORY_SSL_CONFIG_SCHEMA_DEFAULTS,
                                     SSLState)
from axonius.users.user_adapter import UserAdapter
from axonius.utils.atomicint import AtomicInteger
from axonius.utils.build_modes import get_build_mode
from axonius.utils.datetime import parse_date
from axonius.utils.debug import is_debug_attached
from axonius.utils.encryption.mongo_encrypt import MongoEncrypt
from axonius.utils.hash import get_preferred_internal_axon_id_from_dict, get_preferred_quick_adapter_id
from axonius.utils.json_encoders import IteratorJSONEncoder
from axonius.utils.mongo_retries import CustomRetryOperation, mongo_retry
from axonius.utils.parsing import get_exception_string, remove_large_ints
from axonius.utils.revving_cache import rev_cached
from axonius.utils.ssl import SSL_CERT_PATH, SSL_KEY_PATH, CA_CERT_PATH, get_private_key_without_passphrase, \
    SSL_CERT_PATH_LIBS, SSL_KEY_PATH_LIBS
from axonius.utils.threading import (LazyMultiLocker, run_and_forget,
                                     run_in_executor_helper, ThreadPoolExecutorReusable, singlethreaded)
from axonius.utils.mongo_indices import (
    common_db_indexes,
    non_historic_indexes,
    adapter_entity_raw_index,
    adapter_entity_historical_raw_index,
    historic_indexes,
)

# pylint: disable=C0302

logger = logging.getLogger(f'axonius.{__name__}')

# Starting the Flask application
AXONIUS_REST = Flask(__name__)

# Starting the rate limiter
# pylint: disable=invalid-name
limiter = Limiter(
    AXONIUS_REST,
    key_func=get_remote_address,
    strategy='fixed-window-elastic-expiry'
)
# pylint: disable=invalid-name
limiter_settings = {}
LIMITER_SCOPE = 'axonius'

# this would be /home/axonius/logs, or c:\users\axonius\logs, etc.
LOG_PATH = str(Path.home().joinpath('logs'))

# Can wait up to 5 minutes if core didnt answer yet
TIME_WAIT_FOR_REGISTER = 60 * 5

# After this time, the execution promise will be rejected.
TIMEOUT_FOR_EXECUTION_THREADS_IN_SECONDS = 60 * 25

try:
    # pylint: disable=protected-access
    ssl._create_default_https_context = ssl._create_unverified_context
    # pylint: enable=protected-access
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass


# Global list of all the functions we are registering.
ROUTED_FUNCTIONS = list()

# Initialize running add_rule function counter
RUNNING_ADD_RULES_COUNT = AtomicInteger(0)


def random_string(length: int, source: str = string.ascii_letters + string.digits) -> str:
    """
        Generate a random string with length
        Seed it time in milliseconds and salt `HASH_SALT`
    """
    result = ''
    for i in range(0, length):
        result += secrets.choice(source)
    return hashlib.sha256(f'{HASH_SALT}{result}'.encode('utf-16')).hexdigest()


def ratelimiting_settings():
    return f'{limiter_settings[PASSWORD_PROTECTION_ALLOWED_RETRIES]} per ' \
           f'{limiter_settings[PASSWORD_PROTECTION_LOCKOUT_MIN]} minute' \
           if 'enabled' in limiter_settings and limiter_settings['enabled'] else ''


def get_username_from_session():
    return session['user']['user_name'] if 'user' in session and session['user'] is not None else ''


def route_limiter_key_func():
    return get_username_from_session() \
        if limiter_settings['conditional'] == PASSWORD_PROTECTION_BY_IP else get_remote_address()


# I know its ugly, but this way the function wont even be initialized in production
# otherwise every request would have go thru the after_request and do nothing in there...
if os.environ.get('HOT') == 'true':
    import urllib3
    urllib3.disable_warnings()

    @AXONIUS_REST.after_request
    def after_request(response) -> Response:
        response.headers.add('Access-Control-Allow-Origin', 'http://127.0.0.1:8080')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Set-Cookie,x-csrf-token')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response


@AXONIUS_REST.errorhandler(429)
def ratelimit_handler(exception):
    return return_error('Rate limit exceeded', 429)


def add_rule(rule, methods=('GET',), should_authenticate: bool = True):
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
            logger.debug(f'Rule={rule} request={request}')

            try:
                if should_authenticate:
                    # finding the api key
                    if request.headers.get('x-api-key') not in self.authorized_api_keys():
                        # clearing cache before failing
                        self.authorized_api_keys.clean_cache()
                        if request.headers.get('x-api-key') not in self.authorized_api_keys():
                            raise RuntimeError(f'Bad api key. got {request.headers.get("x-api-key")}')
                return func(self, *args, **kwargs)
            except SessionInvalid:
                return return_error('Not logged in', 401)
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
                        logger.exception('Unhandled exception thrown from plugin', extra=extra_log)
                    return json.dumps({'status': 'error', 'type': err_type, 'message': get_exception_string()}), 400
                except Exception as second_err:
                    return json.dumps({'status': 'error', 'type': type(second_err).__name__,
                                       'message': str(second_err)}), 400

        return actual_wrapper
    try:
        RUNNING_ADD_RULES_COUNT.inc()
        return wrap
    except Exception:
        return wrap
    finally:
        RUNNING_ADD_RULES_COUNT.dec()


def retry_if_connection_error(exception):
    """Return True if we should retry (in this case when it's an connection), False otherwise"""
    return isinstance(exception, requests.exceptions.ConnectionError)


def retry_if_remote_disconnected(exception):
    """Return True if we should retry (in this case when it's an connection), False otherwise"""
    return isinstance(exception, requests.exceptions.ConnectionError) and\
        exception.args and isinstance(exception.args[0], ProtocolError)


def return_error(error_message, http_status=500, additional_data=None, non_prod_error=False):
    """ Helper function for returning errors in our format.

    :param str error_message: The explenation of the error
    :param int http_status: The http status to return, 500 by default
    """
    if non_prod_error and os.environ.get('PROD') == 'True':
        exc_id = uuid.uuid4()
        logger.error(f'UUID {exc_id}: error: {error_message}')
        error_message = GENERIC_ERROR_MESSAGE.format(exc_id)
    return jsonify({'status': 'error', 'message': error_message, 'additional_data': additional_data}), http_status


# entity_query_views_db_map   - map between EntityType and views collection from the GUI (e.g. user_views)
GuiDB = namedtuple('GuiDB', ['entity_query_views_db_map'])


def recalculate_adapter_oldness(adapter_list: list, entity_type: EntityType):
    """
    Updates (in place) all adapters given.
    This assumes that they all comprise a single axonius entity.
    All groups of adapters by plugin_name (i.e. 'duplicate' adapter entities from the same adapter)
    will have they're 'old' value recalculated
    https://axonius.atlassian.net/wiki/spaces/AX/pages/794230909/Handle+Duplicates+of+adapter+entity+of+the+same+adapter+entity
    Only the newest adapter entity will have an 'old' value of False, all others will have 'new'.
    (Adapters that don't have duplicates are unaffected)
    :param adapter_list: list of adapter entities
    :param entity_type: Used to verify whether or not this calculation should take palce
    :return: None
    """
    if not entity_type.is_old_calculated:
        return

    all_unique_adapter_entities_data_indexed = defaultdict(list)
    for adapter in adapter_list:
        all_unique_adapter_entities_data_indexed[adapter[PLUGIN_NAME]].append(adapter)

    for adapters in all_unique_adapter_entities_data_indexed.values():
        if not all(LAST_SEEN_FIELD in adapter['data'] for adapter in adapters):
            continue
        for adapter in adapters:
            adapter['data']['_old'] = True
        max(adapters, key=lambda x: x['data'][LAST_SEEN_FIELD])['data']['_old'] = False


def is_plugin_on_demand(plugin_unique_name: str) -> bool:
    """
    Whether or not this plugin is even subject to being 'up' or 'down' dynamically
    :param plugin_unique_name: the plugin name
    """
    return 'adapter' in plugin_unique_name


# pylint: disable=too-many-instance-attributes
class PluginBase(Configurable, Feature, ABC):
    """ This is an abstract class containing the implementation
    For the base capabilities of the Plugin.

    You should inherit this class from your Plugin class, and then use the decorator
    'add_rule' in order to add this rule to the URL.

    All Exceptions thrown from your decorated function will return as a response for
    The user request.

    """
    MyDeviceAdapter: Callable = None
    MyUserAdapter: Callable = None
    # This is effectively a singleton anyway
    Instance = None

    # Use the data we have from the core.

    # pylint: disable=too-many-branches, too-many-locals, too-many-statements
    def __init__(self, config_file_path: str, *args, core_data=None, requested_unique_plugin_name=None, **kwargs):
        """ Initialize the class.

        This will automatically add the rule of '/version' to get the Plugin version.

        :param dict core_data: A data sent by the core plugin. (Will skip the registration process)

        :raise KeyError: In case of environment variables missing
        """
        print(f'{datetime.now()} Hello docker from {type(self)}')
        self.irequests = IRequests()
        run_memory_tracing()
        self.mongo_client = get_db_client()

        PluginBase.Instance = self
        self.plugins = AxoniusPlugins(self._get_db_connection())
        self.db_files = DBFileHelper(self._get_db_connection())

        super().__init__(*args, **kwargs)
        # Basic configurations concerning axonius-libs. This will be changed by the CI.
        # No need to put such a small thing in a version.ini file, the CI changes this string everywhere.

        # Getting values from configuration file
        self.__is_in_mock_mode = os.environ.get('AXONIUS_MOCK_MODE') == 'TRUE'
        self.temp_config = configparser.ConfigParser()
        self.temp_config.read(VOLATILE_CONFIG_PATH)
        self.config_file_path = config_file_path

        self.config = configparser.ConfigParser()
        self.config.read(self.config_file_path)

        self.version = self.config['DEFAULT']['version']
        self.lib_version = self.version  # no meaning to axonius-libs right now, when we are in one repo.
        self.__adapter_base_directory = os.path.dirname(self.config_file_path)
        self.plugin_name = os.path.basename(self.__adapter_base_directory)
        self.plugin_settings = self.plugins.get_plugin_settings(self.plugin_name)
        self.plugin_unique_name = None
        self.api_key = None
        self.node_id = os.environ.get(NODE_ID_ENV_VAR_NAME, None)
        self.core_configs_collection = self._get_db_connection()[CORE_UNIQUE_NAME]['configs']
        try:
            self._current_feature_flag_config = self.feature_flags_config() or {}
        except TypeError:
            # Probably first boot of core and feature flags didnt initialize yet
            self._current_feature_flag_config = {}

        # MyDeviceAdapter things.
        self._entity_adapter_fields = {entity_type: {
            'fields_set': set(),
            'raw_fields_set': set(),
            'fields_db_lock': threading.RLock()
        } for entity_type in EntityType}
        print(f'{datetime.now()} {self.plugin_name} is starting')

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
                self.host = '0.0.0.0'
                self.port = 443  # We listen on https.
                # This should be dns resolved.
                self.core_address = 'https://core.axonius.local/api'

        try:
            self.plugin_unique_name = self.temp_config['registration'][PLUGIN_UNIQUE_NAME]
            self.api_key = self.temp_config['registration']['api_key']
            self.node_id = self.temp_config['registration'][NODE_ID]
        except KeyError:
            # We might have api_key but not have a unique plugin name.
            pass

        if not self.plugin_unique_name and self.node_id:
            # find if we had been quickly registered
            ourself = self.core_configs_collection.find_one({
                NODE_ID: self.node_id,
                PLUGIN_NAME: self.plugin_name
            })
            if ourself:
                print('found quick registered info')
                self.plugin_unique_name = ourself[PLUGIN_UNIQUE_NAME]
                self.api_key = ourself['api_key']
                if 'registration' not in self.temp_config:
                    self.temp_config['registration'] = {}
                self.temp_config['registration'][PLUGIN_UNIQUE_NAME] = self.plugin_unique_name
                self.temp_config['registration']['api_key'] = self.api_key
                self.temp_config['registration'][NODE_ID] = self.node_id

        if requested_unique_plugin_name is not None:
            if self.plugin_unique_name != requested_unique_plugin_name:
                self.plugin_unique_name = requested_unique_plugin_name

        if self.plugin_unique_name:
            # we might have a wrong node_id, according to
            # https://axonius.atlassian.net/browse/AX-4606
            db_node_id = self.core_configs_collection.find_one({
                PLUGIN_UNIQUE_NAME: self.plugin_unique_name
            }, projection={
                NODE_ID: True
            })
            if not db_node_id:
                print('No config found in db!')
            else:
                db_node_id = db_node_id[NODE_ID]
                if db_node_id.startswith('!'):
                    print(f'Found (!), {db_node_id}, current is {self.node_id}')
                    db_node_id = db_node_id[1:]
                    self.node_id = db_node_id
                    try:
                        self.temp_config['registration'][NODE_ID] = self.node_id
                    except Exception:
                        print('no temp config')
                    self._get_db_connection()[CORE_UNIQUE_NAME]['configs'].update_one({
                        PLUGIN_UNIQUE_NAME: self.plugin_unique_name
                    }, {
                        '$set': {
                            NODE_ID: db_node_id
                        }
                    })

        if not core_data:
            core_data = self._register(self.core_address + '/register',
                                       self.plugin_unique_name, self.api_key, self.node_id,
                                       os.environ.get('NODE_INIT_NAME', None))
        if not core_data or core_data['status'] == 'error':
            raise RuntimeError('Register process failed, Exiting. Reason: {0}'.format(core_data))
        if 'registration' not in self.temp_config:
            self.temp_config['registration'] = {}

        if core_data[PLUGIN_UNIQUE_NAME] != self.plugin_unique_name or core_data['api_key'] != self.api_key:
            self.plugin_unique_name = core_data[PLUGIN_UNIQUE_NAME]
            self.api_key = core_data['api_key']
            self.node_id = core_data[NODE_ID]
            self.temp_config['registration'][PLUGIN_UNIQUE_NAME] = self.plugin_unique_name
            self.temp_config['registration']['api_key'] = self.api_key
            self.temp_config['registration'][NODE_ID] = self.node_id

        with open(VOLATILE_CONFIG_PATH, 'w') as self.temp_config_file:
            self.temp_config.write(self.temp_config_file)

        self.log_level = logging.INFO

        self._is_last_seen_prioritized = False

        # Creating logger
        create_logger(self.plugin_unique_name, self.log_level, LOG_PATH)

        # Adding rules to flask
        for routed in ROUTED_FUNCTIONS:
            (wanted_function, rule, wanted_methods) = routed

            # this condition is here to force only rules that are relevant to the current class
            local_function = getattr(self, wanted_function.__name__, None)
            if local_function:
                print(f'{rule}, {wanted_function}, {wanted_function.__name__} {local_function}, {wanted_methods}')
                AXONIUS_REST.add_url_rule('/' + rule,
                                          endpoint=f'{rule}::{"_".join([method for method in wanted_methods])}',
                                          view_func=local_function,
                                          methods=list(wanted_methods))
            else:
                logger.info(f'Skipped rule {rule}, {wanted_function.__qualname__}, {wanted_methods}')

        # Adding 'keepalive' thread
        if self.plugin_unique_name != 'core':
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
        AXONIUS_REST.url_map.strict_slashes = False  # makes routing to 'page' and 'page/' the same.
        self.wsgi_app = AXONIUS_REST

        # https://github.com/PyCQA/pylint/issues/2315
        # pylint bug
        for section in self.config.sections():
            to_print = dict(self.config[section])
            logger.info(f'Config {section}: {to_print}')

        logger.info(f'Running on ip {socket.gethostbyname(socket.gethostname())}')

        # DB's
        self.aggregator_db_connection = self._get_db_connection()[AGGREGATOR_PLUGIN_NAME]
        self.devices_db = self.aggregator_db_connection['devices_db']
        self.users_db = self.aggregator_db_connection['users_db']
        self.historical_devices_db_view = self.aggregator_db_connection['historical_devices_db_view']
        self.historical_users_db_view = self.aggregator_db_connection['historical_users_db_view']

        self._entity_db_map = {
            EntityType.Users: self.users_db,
            EntityType.Devices: self.devices_db,
        }

        # pylint: disable=invalid-name
        self._raw_adapter_entity_db_map = {
            EntityType.Users: self.aggregator_db_connection['user_adapters_raw_db'],
            EntityType.Devices: self.aggregator_db_connection['device_adapters_raw_db'],
        }
        self._raw_adapter_historical_entity_db_map = {
            EntityType.Users: self.aggregator_db_connection['user_adapters_historical_raw_db'],
            EntityType.Devices: self.aggregator_db_connection['device_adapters_historical_raw_db'],
        }

        self._historical_entity_views_db_map = {
            EntityType.Users: self.historical_users_db_view,
            EntityType.Devices: self.historical_devices_db_view,
        }

        self._all_fields_db_map = {
            EntityType.Users: self.aggregator_db_connection['users_fields'],
            EntityType.Devices: self.aggregator_db_connection['devices_fields'],
        }

        self._my_adapters_map: Dict[EntityType, Callable] = {
            EntityType.Users: self.MyUserAdapter,
            EntityType.Devices: self.MyDeviceAdapter
        }

        self.__existing_fields: Dict[EntityType, Set[str]] = {
            EntityType.Users: set(),
            EntityType.Devices: set()
        }

        # pylint: enable=invalid-name

        # GUI Stuff
        gui_db_connection = self._get_db_connection()[GUI_PLUGIN_NAME]

        self.gui_dbs = GuiDB({
            EntityType.Users: gui_db_connection['user_views'],
            EntityType.Devices: gui_db_connection['device_views'],
        })
        del gui_db_connection

        # Reports collections
        reports_db = self._get_db_connection()[REPORTS_PLUGIN_NAME]
        # pylint: disable=invalid-name
        self.enforcements_collection = reports_db['reports']
        self.enforcement_tasks_runs_collection = reports_db['triggerable_history']
        self.enforcements_saved_actions_collection = reports_db['saved_actions']
        self.enforcement_tasks_action_results_id_lists = reports_db['action_results']
        del reports_db
        # pylint: enable=invalid-name

        # Namespaces
        self.devices = axonius.entities.DevicesNamespace(self)
        self.users = axonius.entities.UsersNamespace(self)
        self._namespaces = {
            EntityType.Users: self.users,
            EntityType.Devices: self.devices
        }

        # An executor dedicated to inserting devices to the DB
        # the number of threads should be in a proportion to the number of actual core that can run them
        # since these things are more IO bound here - we allow ourselves to fire more than the number of cores we have
        self._common_executor = concurrent.futures.ThreadPoolExecutor(max_workers=20 * multiprocessing.cpu_count())

        # An executor dedicated for running execution promises
        self.execution_promises = concurrent.futures.ThreadPoolExecutor(max_workers=20 * multiprocessing.cpu_count())

        if 'ScannerAdapter' not in self.specific_supported_features():
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
        self.adapter_client_labels_db = self.aggregator_db_connection['adapters_client_labels']

        # the execution monitor has its own mechanism. this thread will make exceptions if we run it in execution,
        # since it will try to reject functions and not promises.
        if self.plugin_name != 'execution':
            # An executor dedicated to deleting forgotten execution requests
            self.execution_monitor_scheduler = LoggedBackgroundScheduler(executors={'default': ThreadPoolExecutor(1)})
            self.execution_monitor_scheduler.add_job(func=self.execution_monitor_thread,
                                                     trigger=IntervalTrigger(seconds=30),
                                                     next_run_time=datetime.now(),
                                                     name='execution_monitor_thread',
                                                     id='execution_monitor_thread',
                                                     max_instances=1)
            self.execution_monitor_scheduler.start()

        self.__inmem_keyval = dict()
        self._vault_connection = None
        self._update_schema()
        self._update_config_inner()
        self.__save_hyperlinks_to_db()

        # Used by revving_cache
        self.cached_operation_scheduler = LoggedBackgroundScheduler(executors={
            'default': ThreadPoolExecutorReusable(self._common_executor)
        })
        self.cached_operation_scheduler.start()

        self.build_mode = get_build_mode()
        if self.build_mode:
            logger.info(f'Running on {self.build_mode} mode')

        run_and_forget(self.__call_delayed_initialization)

        from axonius.utils.revving_cache import ALL_CACHES
        for cache in ALL_CACHES:
            cache.delayed_initialization()

        # Finished, Writing some log
        logger.info(f'Plugin {self.plugin_unique_name}:{self.version} '
                    f'with axonius-libs:{self.lib_version} started successfully')

    # pylint: enable=too-many-branches
    # pylint: enable=too-many-statements
    def _insert_indexes_entity(self, entity_type):
        """Create all the indices.

        jim: 3.3: moved here from aggregator so plugins can use this
        """
        common_db_indexes(self._entity_db_map[entity_type])
        non_historic_indexes(self._entity_db_map[entity_type])
        adapter_entity_raw_index(self._raw_adapter_entity_db_map[entity_type])
        adapter_entity_historical_raw_index(self._raw_adapter_historical_entity_db_map[entity_type])

        common_db_indexes(self._historical_entity_views_db_map[entity_type])
        historic_indexes(self._historical_entity_views_db_map[entity_type])

    # pylint: disable=no-self-use, import-error
    @add_rule('reload_uwsgi')
    def _reload_uwsgi(self):
        # We import here because this can not be imported from within the host, and the host uses plugin_base.py
        import uwsgi
        logger.info(f'Reloading uwsgi...')
        uwsgi.reload()

    @property
    def is_in_mock_mode(self):
        return self.__is_in_mock_mode

    # pylint: enable=no-self-use
    def _request_reload_uwsgi(self, plugin_unique_name: str):
        self.request_remote_plugin('reload_uwsgi', plugin_unique_name)
        time_passed = 0
        while time_passed < 280:
            time.sleep(5)
            time_passed += 5
            try:
                self.request_remote_plugin('version', plugin_unique_name, fail_on_plugin_down=True, timeout=(5, 5))
                break
            except Exception:
                pass
        else:
            logger.exception('Adapter did not reload successfully from uwsgi')
            raise ValueError(f'Adapter did not reload successfully from uwsgi')

        time.sleep(5)

    @retry(stop_max_attempt_number=3,
           wait_fixed=5000)
    def __call_delayed_initialization(self):
        """
        See _delayed_initialization docs
        This is retrying for dealing with flaky memory restrictions and DB junk
        Maybe this will save us?
        :return:
        """
        try:
            # Supposed to be delayed
            time.sleep(2)
            self._delayed_initialization()
        except BaseException:
            logger.exception('Exception when calling _delayed_initialization')
            raise
        logger.info('Finished delayed initialization')

    @staticmethod
    def lower_and_strip_first_line(iterator):
        return chain([next(iterator).strip().lower()], iterator)

    def _delayed_initialization(self):
        """
        Virtual by design
        Code in this method will run when the plugins starts.
        The stuff here should be stuff that are important but not critical for the initialization of the plugin
        and the system in general.
        The plugins should be able to work properly even if this method haven't finished running, although some
        performance or functionality drop is acceptable.
        This code will run in a different thread at the end of the plugin initialization.

        Stuff stuff won't necessarily be available here.
        For example, your own constructor might not run before this.
        If your plugin also inherits from triggerable or other classes, their constructors are not guaranteed
        to run before this method.

        Follow the inheritance line to figure out what is available or not.

        Strive to make this code as simple as possible
        :return:
        """

    @rev_cached(ttl=600)
    def authorized_api_keys(self) -> List[str]:
        """
        Gets all the api_keys generated by the system from the core/configs db.
        :return: a list of the api_keys generated by the system.
        """
        cursor = self.core_configs_collection.find(projection={
            '_id': 0,
            'api_key': 1
        })
        return set(x['api_key']
                   for x
                   in cursor)

    def __save_hyperlinks_to_db(self):
        """
        See
        https://axonius.atlassian.net/browse/AX-2691
        https://axonius.atlassian.net/wiki/spaces/AX/pages/830472463/GUI+Hyperlinks
        """
        filenames = {
            EntityType.Devices: os.path.join(self.__adapter_base_directory, 'devices_hyperlinks.js'),
            EntityType.Users: os.path.join(self.__adapter_base_directory, 'users_hyperlinks.js'),
        }

        for entity_type in EntityType:
            collection = self._all_fields_db_map[entity_type]
            filename = filenames[entity_type]
            try:
                js_code = open(filename).read()
            except FileNotFoundError:
                logger.info(f'Can\'t find {filename}')
                continue
            collection.update_one({
                'name': 'hyperlinks',
                PLUGIN_NAME: self.plugin_name
            }, {
                '$set': {
                    'code': f'let ___ = {js_code}; ___'
                }
            }, upsert=True)

    def _save_field_names_to_db(self, entity_type: EntityType):
        """ Saves fields_set and raw_fields_set to the Plugin's DB """
        entity_fields = self._entity_adapter_fields[entity_type]
        my_entity = self._my_adapters_map[entity_type]

        if not my_entity:
            return

        # Do note that we are saving the schema each time this function is called, instead of just once.
        # we do this because things can change due to dynamic fields etc.
        # we need to make sure that _save_field_names_to_db is not called too frequently, but mainly after
        # schema change (we can just call it once after all entities insertion,
        # or maybe after the insertion of X entities)

        with entity_fields['fields_db_lock']:
            logger.debug(f'Persisting {entity_type.name} fields to DB')
            try:
                raw_fields = list(entity_fields['raw_fields_set'])  # copy

                # Upsert new fields
                fields_collection = self._all_fields_db_map[entity_type]
                fields_collection.update({
                    'name': 'raw',
                    PLUGIN_UNIQUE_NAME: self.plugin_unique_name
                }, {
                    '$addToSet': {
                        'raw': {
                            '$each': raw_fields
                        }
                    }
                }, upsert=True)
            except Exception:
                logger.debug(f'Could not persist raw_fields_set', exc_info=True)

            # Dynamic fields that were somewhen in the schema must always stay there (unless explicitly removed)
            # because otherwise we would always miss them (image an adapter parsing csv1 and then removing it. csv1's
            # columns are dynamic fields. we want the schema of csv1 appear in the gui even after its not longer
            # the current client!).
            current_dynamic_schema = my_entity.get_fields_info('dynamic')
            current_dynamic_schema_names = [field['name'] for field in current_dynamic_schema['items']]

            # Search for an old dynamic schema and add whatever we don't already have
            dynamic_fields_collection_in_db = fields_collection.find_one({
                'name': 'dynamic',
                PLUGIN_UNIQUE_NAME: self.plugin_unique_name
            })
            if dynamic_fields_collection_in_db:
                for old_dynamic_field in dynamic_fields_collection_in_db.get('schema', {}).get('items', []):
                    if old_dynamic_field['name'] not in current_dynamic_schema_names:
                        current_dynamic_schema['items'].append(old_dynamic_field)

            # Save the new dynamic schema
            fields_collection.update_one({
                'name': 'dynamic',
                PLUGIN_UNIQUE_NAME: self.plugin_unique_name
            }, {
                '$set': {
                    'schema': current_dynamic_schema
                }
            }, upsert=True)

            # extend the overall schema
            current_schema = my_entity.get_fields_info('static')
            current_schema['items'].extend(current_dynamic_schema['items'])
            fields_collection.update({
                'name': 'parsed',
                PLUGIN_UNIQUE_NAME: self.plugin_unique_name
            }, {
                PLUGIN_UNIQUE_NAME: self.plugin_unique_name,
                'name': 'parsed',
                'schema': current_schema
            }, upsert=True)

            exist_fields = list(self.__existing_fields[entity_type])
            if exist_fields:
                fields_collection.update_one({
                    'name': 'exist',
                    PLUGIN_UNIQUE_NAME: self.plugin_unique_name
                }, {
                    '$addToSet': {
                        'fields': {
                            '$each': exist_fields
                        }
                    }
                }, upsert=True)

                fields_collection.update_one({
                    'name': 'exist',
                    PLUGIN_UNIQUE_NAME: '*'
                }, {
                    '$addToSet': {
                        'fields': {
                            '$each': exist_fields
                        }
                    }
                }, upsert=True)

    def _new_device_adapter(self) -> DeviceAdapter:
        """ Returns a new empty device associated with this adapter. """
        if self.MyDeviceAdapter is None:
            raise ValueError('class MyDeviceAdapter(Device) class was not declared inside this Adapter class')
        # pylint: disable=not-callable
        return self.MyDeviceAdapter(self._entity_adapter_fields[EntityType.Devices]['fields_set'],
                                    self._entity_adapter_fields[EntityType.Devices]['raw_fields_set'])
        # pylint: enable=not-callable

    # Users.
    def _new_user_adapter(self) -> UserAdapter:
        """ Returns a new empty User associated with this adapter. """
        if self.MyUserAdapter is None:
            raise ValueError('class MyUserAdapter(user) class was not declared inside this Adapter class')
        # pylint: disable=not-callable
        return self.MyUserAdapter(self._entity_adapter_fields[EntityType.Users]['fields_set'],
                                  self._entity_adapter_fields[EntityType.Users]['raw_fields_set'])
        # pylint: enable=not-callable

    @classmethod
    def specific_supported_features(cls) -> list:
        return ['Plugin']

    def _check_registered_thread(self, retries=6):
        """Function for check that the plugin is still registered.

        This function will issue a get request to the Core to see if we are still registered.
        I case we aren't, this function will stop this application (and let the docker manager to run it again)

        :param int retries: Number of retries before exiting the plugin.
        """
        try:
            response = self.request_remote_plugin('register?unique_name={0}'.format(self.plugin_unique_name),
                                                  plugin_unique_name=CORE_UNIQUE_NAME,
                                                  timeout=120,
                                                  fail_on_plugin_down=True)
            if response.status_code in [404, 499, 502, 409]:  # Fault values
                logger.error(f'Not registered to core (got response {response.status_code}), Exiting')
                # pylint: disable=protected-access
                os._exit(1)
                # pylint: enable=protected-access
            self.comm_failure_counter = 0
        except Exception as e:
            self.comm_failure_counter += 1
            if self.comm_failure_counter > retries:  # Two minutes
                logger.exception(f'Error communicating with Core for more '
                                 f'than 2 minutes, exiting. Reason: {e}')
                # pylint: disable=protected-access
                os._exit(1)
                # pylint: enable=protected-access

    @retry(wait_fixed=10 * 1000,
           stop_max_delay=60 * 5 * 1000,
           retry_on_exception=retry_if_connection_error)  # Try every 10 seconds for 5 minutes
    def _register(self, core_address, plugin_unique_name=None, api_key=None, node_id=None, node_init_name=None):
        """Create registration of the adapter to core.

        :param str core_address: The address of the core plugin
        :param str plugin_unique_name: Wanted name of the plugin(Optional)
        :param str api_key: Api key to use in case we want a certain plugin_unique_name
        :return requests.response: The register response from the core
        """
        register_doc = {
            'plugin_name': self.plugin_name,
            'plugin_type': self.plugin_type,
            'plugin_subtype': self.plugin_subtype.value,
            'plugin_port': self.port,
            'is_debug': is_debug_attached(),
            'supported_features': list(self.supported_features)
        }

        if plugin_unique_name is not None:
            register_doc[PLUGIN_UNIQUE_NAME] = plugin_unique_name
            if api_key is not None:
                register_doc['api_key'] = api_key
            if node_init_name is not None:
                register_doc[NODE_INIT_NAME] = node_init_name

        if node_id is not None:
            register_doc[NODE_ID] = node_id

        try:
            response = self.irequests.post(core_address, data=json.dumps(register_doc))
            return response.json()
        except Exception as e:
            # this is in print because this is called before logger is available
            print(f'Exception on register: {repr(e)}')
            raise

    def start_serve(self):
        """Start Http server.

        This function is blocking as long as the Http server is up.
        .. warning:: Do not use it in production!
        nginx->uwsgi is the one that loads us on production, so it does not call start_serve.
        """
        context = ('/etc/ssl/certs/nginx-selfsigned.crt', '/etc/ssl/private/nginx-selfsigned.key')

        # uncomment the following lines run under profiler
        # from werkzeug.contrib.profiler import ProfilerMiddleware
        # AXONIUS_REST.config['PROFILE'] = True
        # AXONIUS_REST.wsgi_app = ProfilerMiddleware(AXONIUS_REST.wsgi_app,
        # restrictions=[100], sort_by=('time', 'calls'))

        AXONIUS_REST.run(host=self.host,
                         port=self.port,
                         ssl_context=context,
                         debug=True,
                         use_reloader=False)

    @staticmethod
    def get_method():
        """Getting the method type of the request.

        :return: The method type of the current request
        """
        return request.method

    @staticmethod
    def get_url_param(param_name):
        """ Getting params from the URL entered.

        This function is getting parameters only from the URL. For example '/somthing?param1=somthing'

        :param str param_name: The name of the parameters we want to get

        :return: The value of the wanted parameter
        """
        return request.args.get(param_name)

    @staticmethod
    def get_request_header(header_name):
        return request.headers.get(header_name)

    @staticmethod
    def get_request_data():
        """Get the data (raw) from the request.

        :return:The content of the post request
        """
        return request.data

    @staticmethod
    def get_request_data_as_object(prefer_none: bool = False):
        """ Get data from HTTP request as python object.

        :param prefer_none: The old behavior of request.get_json(silent=True) was to return None on failure, mimic it

        :return: The contest of the post request as a python object (An output of the json.loads function)
        """
        post_data = PluginBase.get_request_data()
        if post_data:
            # To make it string instead of bytes
            decoded_data = post_data.decode('utf-8')
            # object_hook is needed to unserialize specific not json-serializable things, like Datetime.
            data = json.loads(decoded_data, object_hook=json_util.object_hook)
            return data

        if prefer_none:
            return None
        return {}

    @staticmethod
    def get_caller_plugin_name():
        """
        Figures out who called us from
        :return: tuple(plugin_unique_name, plugin_name)
        """
        try:
            return request.headers.get('x-unique-plugin-name'), request.headers.get('x-plugin-name')
        except RuntimeError:
            return 'self_induced', 'self_induced'

    def _handle_request_headers_and_users(self, **kwargs):
        headers = {
            'x-api-key': self.api_key,
            'x-unique-plugin-name': self.plugin_unique_name,
            'x-plugin-name': self.plugin_name
        }

        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
            # this does not change the original dict given to this method
            del kwargs['headers']

        if has_request_context():
            user = session.get('user', {}).get('user_name', '').encode('utf-8')
            user_source = session.get('user', {}).get('source')
            headers[X_UI_USER] = user
            headers[X_UI_USER_SOURCE] = user_source

        return headers

    def _ask_core_to_raise_adapter(self, *args, **kwargs):
        return self.__ask_core_to_raise_adapter(*args, **kwargs)

    def __ask_core_to_raise_adapter(self, plugin_unique_name: str):
        try:
            logger.info(f'Raising plugin {plugin_unique_name}')
            self._trigger_remote_plugin(CORE_UNIQUE_NAME, f'start:{plugin_unique_name}', reschedulable=False)
        except Exception:
            logger.exception('Core failed raising adapter!')
            raise

    @singlethreaded()
    @cachetools.cached(cachetools.TTLCache(maxsize=200, ttl=30), lock=threading.Lock())
    def _verify_plugin_is_up(self, plugin_unique_name: str):
        if not is_plugin_on_demand(plugin_unique_name):
            # Core is assumed to be up
            return False

        plugin_data = self.core_configs_collection.find_one({
            PLUGIN_UNIQUE_NAME: plugin_unique_name
        }, projection={
            '_id': 0,
            'status': 1,
        })
        if not plugin_data:
            raise RuntimeError(f'Plugin {plugin_unique_name} not found!')

        if plugin_data['status'] != 'up':
            # asking core to raise adapter
            logger.info(f'Plugin {plugin_unique_name} is not up, asking core to raise it')
            self.__ask_core_to_raise_adapter(plugin_unique_name)

        return True

    @retry(stop_max_attempt_number=3, wait_fixed=5000,
           retry_on_exception=retry_if_remote_disconnected)
    def request_remote_plugin(self, resource, plugin_unique_name=CORE_UNIQUE_NAME, method='get',
                              raise_on_network_error: bool = False,
                              fail_on_plugin_down: bool = False,
                              **kwargs) -> Optional[requests.Response]:
        """
        Provides an interface to access other plugins, with the current plugin's API key.
        :type resource: str
        :param resource: The resource (e.g. 'devices' or 'version') of the plugin
        :type plugin_unique_name: str
        :param plugin_unique_name: The unique name of the plugin in question. None will make a request to the core.
                                   You can also enter a plugin name instead of unique name for single instances like
                                   Aggregator or Execution.
        :param method: HTTP method - see `request.request`
        :param raise_on_network_error: Whether to raise ConnectionError on error or not
        :param fail_on_plugin_down: If True, won't try to raise a plugin if it is down
        :param kwargs: passed to `requests.request`
        :return: :class:`Response <Response>` object
        :rtype: requests.Response
        """
        if not fail_on_plugin_down:
            self._verify_plugin_is_up(plugin_unique_name)
        # if we don't want to raise adapters which are down, don't verify it

        url = f'https://{plugin_unique_name}.{AXONIUS_DNS_SUFFIX}/api/{resource}'
        headers = self._handle_request_headers_and_users(**kwargs)

        data = kwargs.pop('data', None)
        json_data = kwargs.pop('json', None)

        if json_data:
            data = json.dumps(json_data, default=json_util.default)
            headers['Content-Type'] = 'application/json'
        result = None
        try:
            result = self.irequests.request(method, url, headers=headers, data=data, **kwargs)
        except Exception:
            # If this plugin is not 'on demand' - there is no point trying again
            if not is_plugin_on_demand(plugin_unique_name):
                raise

            # If requested to fail on the case of a plugin down
            if fail_on_plugin_down:
                raise

            # Otherwise, force a 'start:plugin' request
            self.__ask_core_to_raise_adapter(plugin_unique_name)
            try:
                result = self.irequests.request(method, url, headers=headers, data=data, **kwargs)
            except Exception:
                if raise_on_network_error:
                    raise
                logger.exception(f'Request failed for {url}, {result}')
                return None
        return result

    def async_request_remote_plugin(self, *args, **kwargs) -> Promise:
        """
        See request_remote_plugin for parameters.
        Runs the request async, and returns a promise for it.
        """
        return Promise(functools.partial(run_in_executor_helper,
                                         self._common_executor,
                                         self.request_remote_plugin,
                                         args=args,
                                         kwargs=kwargs))

    def get_available_plugins_from_core_uncached(self, filter_: dict = None) -> Dict[str, dict]:
        """
        Uncached version for get_available_plugins_from_core
        """
        return {
            x[PLUGIN_UNIQUE_NAME]: x
            for x
            in self.core_configs_collection.find(filter_)
        }

    def filter_out_custom_discovery_adapters(self, adapters: List[dict]):
        all_plugins_with_custom_discovery_enabled = self.plugins.get_plugin_names_with_config(
            DISCOVERY_CONFIG_NAME,
            {
                ENABLE_CUSTOM_DISCOVERY: True
            }
        )

        for adapter in adapters:
            if not adapter[PLUGIN_NAME] in all_plugins_with_custom_discovery_enabled:
                yield adapter

    @singlethreaded()
    @cachetools.cached(cachetools.TTLCache(maxsize=1, ttl=10), lock=threading.Lock())
    def get_available_plugins_from_core(self) -> Dict[str, dict]:
        """
        Gets all running plugins from core by querying the DB
        """
        return self.get_available_plugins_from_core_uncached()

    def _stop_triggerable_plugin(self, plugin_name: str, job_name: str) -> requests.Response:
        """
        Stops a running job in a triggerable plugin
        :param plugin_name: the plugin name to address
        :param job_name: the job name to stop
        """
        return self.request_remote_plugin(f'stop/{job_name}', plugin_name, method='post')

    # pylint: disable=too-many-arguments
    def _trigger_remote_plugin(self, plugin_name: str, job_name: str = 'execute',
                               blocking: bool = True,
                               priority: bool = False,
                               data: dict = None,
                               timeout: int = None,
                               stop_on_timeout: bool = False,
                               reschedulable: bool = True,
                               external_thread: bool = True,
                               error_as_warning: bool = False) -> requests.Response:
        """
        Triggers a triggerable plugin
        :param plugin_name: The plugin name to trigger
        :param job_name: The job name to invoke
        :param blocking: Whether to wait until the operation finishes
        :param priority: Whether to force the operation to take place irrespective of job queue
        :param data: POST data to the job
        :param timeout: How long to wait for a response, only relevant if blocking=True
        :param stop_on_timeout: If true, and timed out, then a 'stop' operation will be triggered
        :param reschedulable: If true, then the job will reschedule if it's already running
        :return: Either the response from the invocation or None for async operations
        """
        timeout = timeout or ''

        def inner():
            try:
                logger.debug(f'Triggering {job_name} on {plugin_name} with {blocking}, {priority}, {reschedulable}'
                             f' and {timeout}')
                logger.debug(data)
                res = self.request_remote_plugin(f'trigger/{job_name}?blocking={blocking}&priority={priority}'
                                                 f'&timeout={timeout}&reschedulable={reschedulable}',
                                                 plugin_name, method='post',
                                                 json=data,
                                                 raise_on_network_error=True)
                if res.status_code == 408:  # timeout:
                    logger.info(f'Timeout on {plugin_name}, {job_name}')
                    if stop_on_timeout:
                        logger.info(f'Stopping task...')
                        self._stop_triggerable_plugin(plugin_name, job_name)
                return res
            except Exception:
                if error_as_warning:
                    logger.warning(f'Trigger failed on {plugin_name}, {job_name}, {data}')
                else:
                    logger.exception(f'Trigger failed on {plugin_name}, {job_name}, {data}')
                if blocking:
                    raise

        if not blocking and external_thread:
            run_and_forget(inner)
            return None
        return inner()

    def _trigger_remote_plugin_no_blocking(self, plugin_name: str, job_name: str = 'execute',
                                           priority: bool = False,
                                           data: dict = None,
                                           reschedulable: bool = True) -> requests.Response:
        """
        Triggers a triggerable plugin and get the id of the job
        :param plugin_name: The plugin name to trigger
        :param job_name: The job name to invoke
        :param priority: Whether to force the operation to take place irrespective of job queue
        :param data: POST data to the job
        :param reschedulable: If true, then the job will reschedule if it's already running
        :return: the response from the plugin
        """

        try:
            logger.debug(f'Triggering {job_name} on {plugin_name} with no blocking, {priority}, {reschedulable}')
            logger.debug(data)
            res = self.request_remote_plugin(f'trigger/{job_name}?blocking={False}&priority={priority}'
                                             f'&reschedulable={reschedulable}',
                                             plugin_name, method='post',
                                             json=data,
                                             raise_on_network_error=True)

            return res
        except Exception as e:
            logger.exception(f'Trigger failed on {plugin_name}, {job_name}, {data} error: {e}')
            return None

    def _wait_for_remote_plugin(self, plugin_name: str, job_name: str = 'execute', timeout: int = None,
                                data: dict = None,
                                stop_on_timeout: bool = False) -> requests.Response:
        """
        Wait for a triggerable plugin job to finish
        :param plugin_name: The plugin name with the job
        :param job_name: The job name to wait for
        :param data: POST data to the job
        :param timeout: How long to wait for a response
        :param stop_on_timeout: If true, and timed out, then a 'stop' operation will be triggered
        :return: The response from the job
        """
        timeout = timeout or ''
        try:
            logger.debug(f'Wait for {job_name} on {plugin_name} and {timeout}')
            res = self.request_remote_plugin(f'wait/{job_name}?timeout={timeout}',
                                             plugin_name, method='get',
                                             json=data,
                                             raise_on_network_error=True)

            if res.status_code == 408:  # timeout:
                logger.info(f'Timeout on {plugin_name}, {job_name}')
                if stop_on_timeout:
                    logger.info(f'Stopping task...')
                    self._stop_triggerable_plugin(plugin_name, job_name)
            return res
        except Exception as e:
            logger.exception(f'Wait failed on {plugin_name}, {job_name}, {data} error: {e}')
            return None

    def _async_trigger_remote_plugin(self, plugin_name: str, job_name: str = 'execute',
                                     priority: bool = False, data: dict = None,
                                     timeout: int = None, stop_on_timeout: bool = False) -> Promise:
        """
        Triggers a triggerable plugin in an async fashion, see async_request_remote_plugin and _trigger_remote_plugin
        """

        def inner():
            res = self._trigger_remote_plugin(plugin_name, job_name, blocking=True,
                                              priority=priority, data=data,
                                              timeout=timeout, stop_on_timeout=stop_on_timeout)
            res.raise_for_status()
            return res

        return Promise(functools.partial(run_in_executor_helper,
                                         self._common_executor,
                                         inner))

    def _request_gui_dashboard_cache_clear(self, clear_slow: bool = False):
        """
        Sometimes the system will make changes that will need to trigger a dashboard change
        :param clear_slow: Whether or not to also clear cache for historical dashboards that rarely change
        """
        logger.debug('Requesting clear dashboard cache')
        self._trigger_remote_plugin(GUI_PLUGIN_NAME, 'clear_dashboard_cache', blocking=False, priority=clear_slow,
                                    data={
                                        'clear_slow': clear_slow
                                    })
        logger.debug('Done requesting clear dashboard cache')

    def create_notification(self, title, content='', severity_type='info', notification_type='basic',
                            hooks: Dict[str, str] = None):
        """
        :param string title:
        :param string content:
        :param string severity_type:
        :param string notification_type:
        :param array hooks: includes all hooks to be replaced within the notification content.
        :return:
        """
        db = self._get_db_connection()
        return db[CORE_UNIQUE_NAME]['notifications'].insert_one(dict(who=self.plugin_unique_name,
                                                                     plugin_name=self.plugin_name,
                                                                     severity=severity_type,
                                                                     type=notification_type,
                                                                     title=title,
                                                                     content=content,
                                                                     seen=False,
                                                                     hooks=hooks)).inserted_id

    @singlethreaded()
    @cachetools.cached(cachetools.TTLCache(maxsize=100, ttl=20), lock=threading.Lock())
    def get_plugin_by_name(self, plugin_name, node_id=None, verify_single=True, verify_exists=True):
        """
        Finds plugin_name in the online plugin list
        :param plugin_name: str for plugin_name or plugin_unique_name.
        :param node_id: str uuid of the node adapter is attached to.
        :param verify_single: If True, will raise if many instances are found.
        :param verify_exists: If True, will raise if no instances are found.
        :return: if verify_single: single plugin data or None; if not verify_single: all plugin datas
        """
        # using requests directly so the api key won't be sent, so the core will give a list of the plugins
        plugins_available = self.get_available_plugins_from_core_uncached()
        if node_id is not None:
            found_plugins = [x
                             for x
                             in plugins_available.values()
                             if (x['plugin_name'] == plugin_name and x[NODE_ID] == node_id)]
        else:
            found_plugins = [x
                             for x
                             in plugins_available.values()
                             if plugin_name in (x[PLUGIN_UNIQUE_NAME], x['plugin_name'])]

        if verify_single:
            if len(found_plugins) == 0:
                if verify_exists:
                    raise PluginNotFoundException(
                        'There is no plugin {0} currently registered'.format(plugin_name))
                return None
            if len(found_plugins) != 1:
                raise RuntimeError(
                    'There are {0} plugins or {1}, there should only be one'.format(len(found_plugins), plugin_name))
            return found_plugins[0]

        if verify_exists and (not found_plugins):
            raise PluginNotFoundException(
                'There is no plugin {0} currently registered'.format(plugin_name))
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
        version_object = {'plugin_name': self.plugin_name,
                          'plugin_unique_name': self.plugin_unique_name,
                          'plugin': self.version,
                          NODE_ID: self.node_id,
                          'axonius-libs': self.lib_version}

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

    # pylint: disable=no-self-use
    @add_rule('debug/run_gc/<generation>', methods=['POST'])
    def run_gc(self, generation: int):
        """
        Runs GC for the given generation
        :param generation: generation to collect
        :return: see gc.collect
        """
        return jsonify(gc.collect(int(generation)))

    @add_rule('debug/gc_stats', methods=['GET'])
    def gc_stats(self):
        """
        Get GC stats
        """
        threshold = gc.get_threshold()
        count = gc.get_count()
        stats = gc.get_stats()
        return jsonify({
            'threshold': threshold,
            'count': count,
            'stats': stats
        })
    # pylint: enable=no-self-use

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
            if self.plugin_name == 'execution':
                # This is a special case for the execution_controller plugin. In that case, The EC plugin knows how to
                # handle other actions such as reset_update. In case of ec plugin, we know for sure what is the
                # callback, we use this fact to just call the callback and not search for it on the _open_actions
                # list (because the current action id will not be there)

                # This is a TERRIBLE hack ofir did and everyone hates that
                # pylint: disable=no-member
                self.ec_callback(action_id)
                # pylint: enable=no-member
                return ''

            with self._open_actions_lock:
                if action_id not in self._open_actions:
                    logger.error(f'Got unrecognized action_id update. Action ID: {action_id}. Was it resolved?')
                    return return_error('Unrecognized action_id {action_id}. Was it resolved?', 404)

                # We recognize this action id, should call its callback
                action_promise, started_time = self._open_actions[action_id]
                # logger.info(f'action id {action_id} returned after time {datetime.now() - started_time}')
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

        except Exception as e:
            logger.exception('General exception in action callback')
            raise e

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
        uri = f'action/{action_type}?axon_id={axon_id}'

        result = self.request_remote_plugin(uri,
                                            plugin_unique_name=EXECUTION_PLUGIN_NAME,
                                            method='POST',
                                            data=json.dumps(data))

        try:
            result.raise_for_status()
            action_id = result.json()['action_id']
        except Exception as e:
            err_msg = f'Failed to request remote plugin, got response {result.status_code}: {result.content}'
            logger.exception(err_msg)
            raise ValueError(f'{err_msg}. Exception is {e}')

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
                    err_msg = f'Timeout {TIMEOUT_FOR_EXECUTION_THREADS_IN_SECONDS} reached for ' \
                              f'action_id {action_id}, rejecting the promise.'
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
        return self.mongo_client

    def _get_collection(self, collection_name, db_name=None) -> Collection:
        """
        Returns all configs for the current plugin.

        :param str collection_name: The name of the collection we want to get
        :param str db_name: The name of the db. By default it is the unique plugin name

        :return: list(dict)
        """
        if not db_name:
            db_name = self.plugin_unique_name
        return self._get_db_connection()[db_name][collection_name]

    def get_appropriate_view(self, historical, entity_type: EntityType) -> Tuple[Collection, bool]:
        """
        Returns the appropriate collection given entity time and historical date, if an historical collection
        exists for given date, then the 2nd argument will return as True
        historical collections are snapshots of an entities collection in a given date, they allow for an easier access
        to the entity collection on the given date.
        """
        if historical:
            h_col_name = f'historical_{entity_type.value.lower()}_{historical.strftime("%Y_%m_%d")}'
            if (datetime.now() - historical).days > 30:
                return self._historical_entity_views_db_map[entity_type], True
            # if for any reason the historical day collection wasn't created fall back to regular history collection
            if h_col_name not in self.aggregator_db_connection.list_collection_names():
                return self._historical_entity_views_db_map[entity_type], True
            return self.aggregator_db_connection[h_col_name], False
        return self._entity_db_map[entity_type], False

    def _grab_file(self, field_data):
        """
        Fetches the file pointed by `field_data` from the DB.
        The user should not assume anything about the internals of the file.
        :param self:
        :param field_data:
        :return: stream like object
        """
        if field_data and field_data.get('uuid'):
            return self.db_files.get_file(ObjectId(field_data['uuid']))
        return None

    def _grab_file_contents(self, field_data, stored_locally=True, alternative_db_name=None) -> Optional[bytes]:
        """
        Fetches the file pointed by `field_data` from the DB.
        The user should not assume anything about the internals of the file.
        :param self:
        :param field_data:
        :return: stream like object
        """
        contents = self._grab_file(field_data)
        if contents:
            return contents.read()
        return None

    @property
    def plugin_type(self):
        return 'Plugin'

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
            logger.exception(f'Timeout for {client_name} on {self.plugin_unique_name}')
            raise AdapterException(f'Fetching has timed out')

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    def __do_save_data_from_plugin(self, client_name, data_of_client, entity_type: EntityType,
                                   should_log_info: bool = True, plugin_identity: Tuple[str, str, str] = None) -> int:
        """
        Saves all given data from adapter (devices, users) into the DB for the given client name
        :param plugin_identity: tuple of (plugin_type, plugin_name, plguin_unique_name) from which these entity came.
                                if none, we assume the current plugin name and unique name.
        :return: Device count saved
        """
        multilocker = LazyMultiLocker()
        db_to_use = self._entity_db_map.get(entity_type)
        raw_db_to_use = self._raw_adapter_entity_db_map.get(entity_type)

        assert db_to_use and raw_db_to_use, f'got unexpected {entity_type}'
        try:
            plugin_type, plugin_name, plugin_unique_name = plugin_identity
        except Exception:
            plugin_type, plugin_name, plugin_unique_name = self.plugin_type, self.plugin_name, self.plugin_unique_name
            plugin_identity = (plugin_type, plugin_name, plugin_unique_name)

        def insert_data_to_db(data_to_update, parsed_to_insert):
            """
            Insert data (devices/users/...) into the DB
            :return:
            """
            try:
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
                    array_filters = None

                    if self._is_last_seen_prioritized:
                        last_seen_from_data = data_to_update.get(f'adapters.$.data.{LAST_SEEN_FIELD}')
                        if last_seen_from_data:
                            array_filters = [
                                {
                                    f'i.{PLUGIN_UNIQUE_NAME}': parsed_to_insert[PLUGIN_UNIQUE_NAME],
                                    'i.data.id': parsed_to_insert['data']['id'],
                                    f'i.data.{LAST_SEEN_FIELD}': {
                                        '$lte': last_seen_from_data
                                    }
                                }
                            ]
                        else:
                            array_filters = [{
                                f'i.{PLUGIN_UNIQUE_NAME}': parsed_to_insert[PLUGIN_UNIQUE_NAME],
                                'i.data.id': parsed_to_insert['data']['id'],
                                '$or': [
                                    {
                                        f'i.data.{LAST_SEEN_FIELD}': {
                                            '$exists': False
                                        }
                                    },
                                    {
                                        f'i.data.{LAST_SEEN_FIELD}': None
                                    }
                                ]
                            }]

                        # updating the saving query to adhere to array_filter semantics
                        data_to_update = {
                            k.replace('adapters.$', 'adapters.$[i]'): v
                            for k, v
                            in data_to_update.items()
                        }

                    # Inserts 'raw' into the DB and removes it from the device
                    raw_db_to_use.update_one(
                        {
                            PLUGIN_UNIQUE_NAME: parsed_to_insert[PLUGIN_UNIQUE_NAME],
                            'id': parsed_to_insert['data']['id'],
                        },
                        {
                            '$set': {
                                'raw_data': parsed_to_insert['data'].pop('raw', {})
                            }
                        },
                        upsert=True
                    )

                    # trying to update the device if it is already in the DB
                    update_result = db_to_use.update_one({
                        'adapters.quick_id': get_preferred_quick_adapter_id(parsed_to_insert[PLUGIN_UNIQUE_NAME],
                                                                            parsed_to_insert['data']['id'])
                    }, {
                        '$set': data_to_update
                    }, array_filters=array_filters)

                    if update_result.matched_count > 0 and update_result.modified_count == 0:
                        # This means that a device is found but already has a newer instance in the DB,
                        # so the device is discarded
                        logger.debug(f'Dropping {data_to_update} due to oldness')
                        return

                    if update_result.modified_count == 0:
                        # if it's not in the db
                        # save first fetch time for adapter data
                        if parsed_to_insert['data'].get(FETCH_TIME):
                            parsed_to_insert['data'][FIRST_FETCH_TIME] = parsed_to_insert['data'].get(FETCH_TIME)
                        if correlates:
                            # for scanner adapters this is case B - see 'scanner_adapter_base.py'
                            # we need to add this device to the list of adapters in another device
                            correlate_plugin_unique_name, correlated_id = correlates
                            update_result = db_to_use.update_one({
                                'adapters.quick_id': get_preferred_quick_adapter_id(correlate_plugin_unique_name,
                                                                                    correlated_id)
                            }, {
                                '$addToSet': {
                                    'adapters': parsed_to_insert
                                },
                                '$inc': {
                                    ADAPTERS_LIST_LENGTH: 1
                                }
                            })
                            if update_result.modified_count == 0:
                                logger.error('No devices update for case B for scanner device '
                                             f'{parsed_to_insert["data"]["id"]} from '
                                             f'{parsed_to_insert[PLUGIN_UNIQUE_NAME]}')
                        else:
                            # this is regular first-seen device, make its own value
                            try:
                                internal_axon_id = get_preferred_internal_axon_id_from_dict(
                                    parsed_to_insert, entity_type)
                                db_to_use.insert_one({
                                    'internal_axon_id': internal_axon_id,
                                    'accurate_for_datetime': datetime.now(),
                                    'adapters': [parsed_to_insert],
                                    'tags': [],
                                    ADAPTERS_LIST_LENGTH: 1,
                                    HAS_NOTES: False,
                                })
                            except DuplicateKeyError:
                                logger.warning(f'Duplicate key error on {entity_type}, {parsed_to_insert}',
                                               exc_info=True)
                            except OperationFailure:
                                logger.critical(f'Operational failure on {entity_type}, {parsed_to_insert}')
            except Exception as e:
                logger.exception(f'insert_data_to_db failed, exception: {str(e)}')
                raise

        if should_log_info is True:
            logger.info(f'Starting to fetch data (devices/users) for {client_name}')
        try:
            time_before_client = datetime.now()

            inserted_data_count = 0
            promises = []

            def insert_quickpath_to_db(devices):
                # trying to update the device if it is already in the DB
                raw_db_to_use.bulk_write([
                    ReplaceOne(filter={
                        PLUGIN_UNIQUE_NAME: plugin_unique_name,
                        'id': device['id'],
                    }, replacement={
                        PLUGIN_UNIQUE_NAME: plugin_unique_name,
                        'id': device['id'],
                        'raw_data': device.pop('raw', {})
                    }, upsert=True)
                    for device
                    in devices])

                all_parsed = [self._create_axonius_entity(
                    client_name,
                    data,
                    entity_type,
                    plugin_identity
                ) for data in devices]

                for parsed in all_parsed:
                    if parsed['data'].get(FETCH_TIME):
                        parsed['data'][FIRST_FETCH_TIME] = parsed['data'].get(FETCH_TIME)

                for adapter_entity in all_parsed:
                    for key in adapter_entity['data']:
                        self.__existing_fields[entity_type].add(key)

                # Pylint contradicts autopep8
                # pylint: disable=bad-continuation
                insertion_iterable = ({
                    'internal_axon_id': get_preferred_internal_axon_id_from_dict(parsed_to_insert, entity_type),
                    'accurate_for_datetime': datetime.now(),
                    'adapters': [parsed_to_insert],
                    'tags': [],
                    HAS_NOTES: False,
                    ADAPTERS_LIST_LENGTH: 1,
                }
                    for parsed_to_insert
                    in all_parsed)
                # pylint: enable=bad-continuation

                db_to_use.insert_many(insertion_iterable, ordered=False)

            inserter = self.__first_time_inserter
            # quickest way to find if there are any devices from this plugin in the DB
            # pylint: disable=bad-continuation
            if inserter and not\
                    self._is_last_seen_prioritized and \
                    db_to_use.count_documents({
                        f'adapters.{PLUGIN_UNIQUE_NAME}': plugin_unique_name
                    }, limit=1) == 0:
                # pylint: enable=bad-continuation
                logger.info('Fast path! First run.')
                # DB is empty! no need for slow path, can just bulk-insert all.
                for devices in chunks(500, data_of_client['parsed']):
                    promises.append(Promise(functools.partial(run_in_executor_helper,
                                                              inserter,
                                                              insert_quickpath_to_db,
                                                              args=[devices])))

                    inserted_data_count += len(devices)
                    logger.info(f'Over {inserted_data_count} to DB')

            else:
                # DB is not empty. Should go for slow path.
                # Here we have all the devices a single client sees
                for data in data_of_client['parsed']:
                    parsed_to_insert = self._create_axonius_entity(
                        client_name,
                        data,
                        entity_type,
                        plugin_identity
                    )

                    for key in parsed_to_insert['data']:
                        self.__existing_fields[entity_type].add(key)
                    self.__existing_fields[entity_type].add(FIRST_FETCH_TIME)

                    # Note that this updates fields that are present. If some fields are not present but are present
                    # in the db they will stay there.
                    data_to_update = {f'adapters.$.{key}': value
                                      for key, value in parsed_to_insert.items() if key != 'data'}

                    fields_to_update: Iterable[str] = data.keys() - ['id']

                    for field in fields_to_update:
                        if not field == 'raw':
                            field_of_data = data.get(field, [])
                            data_to_update[f'adapters.$.data.{field}'] = field_of_data
                    data_to_update['accurate_for_datetime'] = datetime.now()

                    inserted_data_count += 1
                    promises.append(Promise(functools.partial(run_in_executor_helper,
                                                              self._common_executor,
                                                              insert_data_to_db,
                                                              args=[data_to_update, parsed_to_insert])))

                    if inserted_data_count % 1000 == 0:
                        promises = [p for p in promises if p.is_pending or p.is_rejected]
                        logger.info(f'Entities went through: {inserted_data_count}; ' +
                                    f'promises active: {len(promises)}; ' +
                                    f'in DB: {inserted_data_count - len(promises)}')
                        while len(promises) > 2000:
                            # If we have too many promises we can clog up the memory, so let's wait until
                            # we have fewer
                            logger.debug(f'Waiting... {len(promises)} active promises')
                            time.sleep(2)
                            promises = [p for p in promises if p.is_pending or p.is_rejected]

                    if inserted_data_count % 10000 == 0:
                        logger.info(f'Saving field names to db..')
                        self._save_field_names_to_db(entity_type)

            promise_all = Promise.all(promises)
            Promise.wait(promise_all, timedelta(minutes=20).total_seconds())
            if promise_all.is_rejected:
                logger.error(f'Error in insertion of {entity_type} to DB', exc_info=promise_all.reason)

            if entity_type == EntityType.Devices:
                added_pretty_ids_count = self._add_pretty_id_to_missing_adapter_devices()
                logger.info(f'{added_pretty_ids_count} devices had their pretty_id set')

            time_for_client = datetime.now() - time_before_client
            total_seconds = time_for_client.total_seconds()
            if self._notify_on_adapters is True and (total_seconds or inserted_data_count) \
                    and not 'general_info' in plugin_name and not should_log_info:
                self.create_notification(
                    f'Finished aggregating {entity_type} for client {client_name}, '
                    f' aggregation took {str(total_seconds)} seconds and returned {inserted_data_count}.')
                self.send_external_info_log(f'Finished aggregating {entity_type} for client {client_name}, '
                                            f' aggregation took {str(total_seconds)} seconds and '
                                            f'returned {inserted_data_count}.')
            if should_log_info is True:
                logger.info(
                    f'Finished aggregating {entity_type} for client {client_name}, '
                    f' aggregation took {str(total_seconds)} seconds and returned {inserted_data_count}.')

        except Exception as e:
            logger.exception(f'Thread {threading.current_thread()} encountered error: {e}')
            raise
        finally:
            # whether or not it was successful, next time we shouldn't try first-time optimization and
            # go full slow path
            self.__first_time_inserter = None

        if should_log_info is True:
            logger.info(f'Finished inserting {entity_type} of client {client_name}')

        return inserted_data_count

    # pylint: enable=too-many-locals
    # pylint: enable=too-many-branches
    # pylint: enable=too-many-statements

    def _get_nodes_table(self):
        def get_single_node_data(node_id, is_master=False):
            node_metadata = db_connection['core']['nodes_metadata'].find_one({NODE_ID: node_id})
            last_seen = ''
            try:
                last_seen = self.request_remote_plugin(f'nodes/last_seen/{node_id}').json().get('last_seen')
            except Exception as e:
                logger.warning(f'Error getting node {node_id} last seen: {e}')
            node = {NODE_ID: node_id,
                    'last_seen': last_seen
                    }

            if node_metadata:
                node['node_name'] = node_metadata.get('node_name', '')
                node['tags'] = node_metadata.get('tags', {})
                node[NODE_USER_PASSWORD] = node_metadata.get(NODE_USER_PASSWORD, '')
                node['hostname'] = node_metadata.get('hostname', '')
                node['ips'] = node_metadata.get('ips', '')
                node['status'] = node_metadata.get('status', ACTIVATED_NODE_STATUS)
                node['is_master'] = is_master
                node['use_as_environment_name'] = False

                if is_master:
                    node['use_as_environment_name'] = node_metadata.get('use_as_environment_name', False)
            return node

        db_connection = self._get_db_connection()
        nodes = []

        master_id = self.node_id
        # Get all the node ids connected to this master.
        node_ids = self.core_configs_collection.distinct(NODE_ID)

        # Remove master node_id and deal with it separately to have it on the top.
        node_ids.remove(master_id)
        nodes.append(get_single_node_data(master_id, True))

        # Gather all the rest.
        for current_node in node_ids:
            nodes.append(get_single_node_data(current_node))

        return nodes

    def _get_adapter_unique_name(self, adapter_name: str, node_id: str) -> str:
        response = self.request_remote_plugin(
            f'find_plugin_unique_name/nodes/{node_id}/plugins/{adapter_name}')  # .json().get(
        # 'plugin_unique_name')

        if response.status_code != 200 or not response.text:
            raise RuntimeError(f'Unable to find adapter for instance \'{node_id}\'')

        return response.json().get(PLUGIN_UNIQUE_NAME)

    @staticmethod
    def _create_axonius_entity(
            client_name: str,
            data: dict,
            entity_type: EntityType,
            plugin_identity: Tuple[str, str, str]) -> dict:
        """
        Virtual.
        Creates an axonius entity ('Parsed data')
        :param client_name: the name of the client
        :param data: the parsed data
        :param entity_type: the type of the entity (see EntityType)
        :param plugin_identity: a tuple of (plugin_type, plugin_name, plugin_unique_name) consisting the identity
        :return: dict
        """

        plugin_type, plugin_name, plugin_unique_name = plugin_identity

        # Remove large ints from the data object, since mongodb can not handle integers that are larger than 8 bytes
        data = remove_large_ints(data, data.get('id', f'{plugin_unique_name}_unidentified_device'))

        parsed_to_insert = {
            'client_used': client_name,
            'plugin_type': plugin_type,
            'plugin_name': plugin_name,
            'plugin_unique_name': plugin_unique_name,
            'type': 'entitydata',
            'accurate_for_datetime': datetime.now(),
            'data': data,
            # The justification for this field is that MongoDB doesn't support a multikey compound index
            # as that would require a cartesian product of all the data in the array.
            # This field implements that using a single hashed field.
            'quick_id': get_preferred_quick_adapter_id(plugin_unique_name, data['id'])
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
                'data.pretty_id': {'$exists': False}
            }
        }}, projection={
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
            self.devices_db.update_one({
                '_id': _id,
                'adapters.quick_id': get_preferred_quick_adapter_id(self.plugin_unique_name, adapter_id)
            }, {'$set':
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
                                                             'plugin_name': self.plugin_name,
                                                             'plugin_unique_name': self.plugin_unique_name,
                                                             'plugin_type': self.plugin_type})
        except pymongo.errors.PyMongoError as e:
            logger.exception(f'Error in pymongo. details: {e}')
        except pymongo.errors.DocumentTooLarge:
            # wanna see my 'something too large'?
            logger.warning(f'Got DocumentTooLarge with client.')

    # pylint: disable=too-many-locals
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

        # it's complicated why we need this
        # https://axonius.atlassian.net/browse/AX-2643
        # generally, in some cases (Labels created by someone which is not the GUI, e.g. general_info)
        # we want to completely fake it as if it's a GUI label

        # this will become either the actual plugin name, or the fake one given in additional_data
        virtual_plugin_unique_name = additional_data[PLUGIN_UNIQUE_NAME]
        virtual_plugin_name = additional_data[PLUGIN_NAME]

        additional_data['accurate_for_datetime'] = datetime.now()
        update_accurate_for_datetime = {
            'accurate_for_datetime': datetime.now()
        }
        with _entities_db.start_session() as db_session:
            entities_candidates_list = list(db_session.find({'$or': [
                {
                    'adapters.quick_id': get_preferred_quick_adapter_id(associated_plugin_unique_name, associated_id)
                }
                for associated_plugin_unique_name, associated_id in associated_adapters
            ]}))

            if len(entities_candidates_list) != 1:
                raise TagDeviceError(f'A tag must be associated with just one adapter, '
                                     f'0 != {len(entities_candidates_list)}')

            # take (assumed single) candidate
            entities_candidate = entities_candidates_list[0]

            if tag_type == 'adapterdata':
                relevant_adapter = [x for x in entities_candidate['adapters']
                                    if x[PLUGIN_UNIQUE_NAME] == associated_adapters[0][0]]
                assert relevant_adapter, 'Couldn\'t find adapter in axon device'
                additional_data['associated_adapter_plugin_name'] = relevant_adapter[0][PLUGIN_NAME]

            if tag_type == 'label':
                lables = db_session.find_one({'internal_axon_id': entities_candidate['internal_axon_id']},
                                             projection=['labels'])
                lables = lables['labels'] if 'labels' in lables else []
                if name in lables and data is False:
                    lables.remove(name)
                elif name not in lables and data is True:
                    lables.append(name)
                lables = list(set(lables))
                db_session.update_one(
                    {'internal_axon_id': entities_candidate['internal_axon_id']},
                    {
                        '$set': {
                            'labels': lables
                        }
                    }
                )

            elif any(x['name'] == name and
                     x[PLUGIN_UNIQUE_NAME] == virtual_plugin_unique_name and
                     x['type'] == tag_type
                     for x
                     in entities_candidate['tags']):

                # We found the tag. If action_if_exists is replace just replace it. but if its update, lets
                # make a deep merge here.
                if action_if_exists == 'update' and tag_type == 'adapterdata':
                    # Take the old value of this tag.
                    final_data = [
                        x['data'] for x in entities_candidate['tags'] if
                        x['plugin_unique_name'] == virtual_plugin_unique_name
                        and x['type'] == 'adapterdata'
                        and x['name'] == name
                    ]

                    if len(final_data) != 1:
                        msg = f'Got {name}/{tag_type} with ' \
                              f'action_if_exists=update, but final_data is not of length 1: {final_data}'
                        logger.error(msg)
                        raise TagDeviceError(msg)

                    final_data = final_data[0]

                    # Merge. Note that we deep merge dicts but not lists, since lists are like fields
                    # for us (for example ip). Usually when we get some list variable we get all of it so we don't need
                    # any update things
                    data = deep_merge_only_dict(data, final_data)
                    logger.debug('action if exists on tag!')

                tag_data = {
                    'association_type': 'Tag',
                    'associated_adapters': associated_adapters,
                    'name': name,
                    'data': data,
                    'type': tag_type,
                    'entity': entity.value,
                    'action_if_exists': action_if_exists,
                    **additional_data
                }

                result = db_session.update_one({
                    'internal_axon_id': entities_candidate['internal_axon_id'],
                    'tags': {
                        '$elemMatch':
                            {
                                'name': name,
                                'plugin_unique_name': virtual_plugin_unique_name,
                                'type': tag_type
                            }
                    }
                }, {
                    '$set': {
                        'tags.$': tag_data,
                        **update_accurate_for_datetime
                    }
                })

                if result.matched_count != 1:
                    msg = f'tried to update tag {tag_data}. ' \
                          f'expected matched_count == 1 but got {result.matched_count}'
                    logger.error(msg)
                    raise TagDeviceError(msg)
            else:
                tag_data = {
                    'association_type': 'Tag',
                    'associated_adapters': associated_adapters,
                    'name': name,
                    'data': data,
                    'type': tag_type,
                    'entity': entity.value,
                    'action_if_exists': action_if_exists,
                    **additional_data
                }

                result = db_session.update_one(
                    {'internal_axon_id': entities_candidate['internal_axon_id']},
                    {
                        '$set': update_accurate_for_datetime,
                        '$addToSet': {
                            'tags': tag_data
                        }
                    })

                if result.modified_count != 1:
                    msg = f'tried to add tag {tag_data}. expected modified_count == 1 but got {result.modified_count}'
                    logger.error(msg)
                    raise TagDeviceError(msg)
        return entities_candidates_list

    def _tag(self, entity: EntityType, identity_by_adapter, name, data, tag_type, action_if_exists,
             client_used,
             additional_data) -> List[dict]:
        """ Function for tagging adapter devices.
        This function will tag a wanted device. The tag will be related only to this adapter
        :param identity_by_adapter: a list of tuples of (adapter_unique_name, unique_id).
                                           e.g. [('ad-adapter-1234', 'CN=EC2AMAZ-3B5UJ01,OU=D....')]
        :param name: the name of the tag. should be a string.
        :param data: the data of the tag. could be any object.
        :param tag_type: the type of the tag. 'label' for a regular tag, 'data' for a data tag.
        :param entity: 'devices' or 'users' -> what is the entity we are tagging.
        :param action_if_exists: 'replace' to replace the tag, 'update' to update the tag (in case its a dict)
        :param client_used: an optional parameter to indicate client_used. This is important since we show this in
                            the gui (we can know where the data came from)
        :param additional_data: additional data to the dict sent to the aggregator
        :return: List of affected entities
        """

        assert action_if_exists == 'replace' or (action_if_exists == 'update' and tag_type == 'adapterdata') or \
            (action_if_exists == 'merge' and tag_type == 'data')
        additional_data = additional_data or {}

        if client_used is not None:
            assert isinstance(client_used, str)
            additional_data['client_used'] = client_used

        return self.__perform_tag(entity, identity_by_adapter, name, data, tag_type, action_if_exists, additional_data)

    @mongo_retry()
    def link_adapters(self, entity: EntityType, correlation: CorrelationResult,
                      entities_candidates_hint: List[str] = None) -> str:
        """
        Performs a correlation between the entities given by 'correlation'
        :param entity: The entity type to use
        :param correlation: The information of the correlation - see definition of CorrelationResult
        :param entities_candidates_hint: Optional: If passed, the code will ignore the associated_adapters
                                         passed and instead will use the internal_axon_ids given here
        :return: Internal axon ID of the entity built
        """
        _entities_db = self._entity_db_map[entity]
        with _entities_db.start_session() as db_session:
            try:
                with db_session.start_transaction():
                    if entities_candidates_hint:
                        entities_candidates = list(db_session.find({
                            'internal_axon_id': {
                                '$in': entities_candidates_hint
                            }
                        }))
                    else:
                        entities_candidates = list(db_session.find({'$or': [
                            {
                                'adapters.quick_id': get_preferred_quick_adapter_id(associated_plugin_unique_name,
                                                                                    associated_id)
                            }
                            for associated_plugin_unique_name, associated_id in correlation.associated_adapters
                        ]}))

                    if len(entities_candidates) < 2:
                        raise CorrelateException(f'No entities given or all entities given don\'t exist. '
                                                 f'Associated adapters: {correlation.associated_adapters}')

                    if len(entities_candidates) > MAX_LINK_AMOUNT:
                        logger.info('Data loss prevented: '
                                    f'Someone tried to link more than {MAX_LINK_AMOUNT} entities at once, '
                                    'which looks like a corrupt plugin, here are the first ten entities')
                        logger.info(entities_candidates[:MAX_LINK_AMOUNT])
                        raise CorrelateException('Way too many entities we\'re given')

                    collected_adapter_entities = [axonius_entity['adapters'] for axonius_entity in entities_candidates]
                    all_unique_adapter_entities_data = [v for d in collected_adapter_entities for v in d]
                    recalculate_adapter_oldness(all_unique_adapter_entities_data, entity)

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

                    labels_for_new_device = [label for entity in entities_candidates
                                             if 'labels' in entity for label in entity['labels']]

                    # Set indication if any of the original adapters has notes
                    has_notes = any(axonius_entity.get(HAS_NOTES) for axonius_entity in entities_candidates)

                    # Get other correlation reasons
                    correlation_reasons = [reason for candidate in entities_candidates if CORRELATION_REASONS
                                           in candidate for reason in candidate[CORRELATION_REASONS]]

                    # Check no duplicate reasons
                    current_correlation_reason = \
                        f'Between adapters: ' \
                        f'{",".join([x[0] for x in correlation.associated_adapters])}\n' \
                        f'Device IDs: {"$$$$".join([x[1] for x in correlation.associated_adapters])}\n' \
                        f'Reason: {correlation.data.get("Reason", None)}'

                    if current_correlation_reason not in correlation_reasons:
                        correlation_reasons.append(current_correlation_reason)

                    remaining_entity = max(entities_candidates, key=lambda x: len(x['adapters']))
                    internal_axon_id = remaining_entity['internal_axon_id']

                    # now, let us delete all other AxoniusDevices
                    db_session.delete_many({
                        '$or': [
                            {
                                'internal_axon_id': axonius_entity['internal_axon_id']
                            }
                            for axonius_entity
                            in entities_candidates]
                    })

                    if len(all_unique_adapter_entities_data) > 30:
                        logger.info(f'Over sized adapter link occurred on {internal_axon_id}, '
                                    f'has {len(all_unique_adapter_entities_data)} adapters')
                    adapters_by_plugin_name = defaultdict(int)
                    for adapter in all_unique_adapter_entities_data:
                        adapters_by_plugin_name[adapter[PLUGIN_UNIQUE_NAME]] += 1
                    if any(x > 10 for x in adapters_by_plugin_name.values()):
                        logger.info(f'Too many from a single adapter: {adapters_by_plugin_name} for {internal_axon_id}')

                    db_session.insert_one({
                        '_id': remaining_entity['_id'],
                        'internal_axon_id': internal_axon_id,
                        'accurate_for_datetime': datetime.now(),
                        'adapters': all_unique_adapter_entities_data,
                        ADAPTERS_LIST_LENGTH: len({x[PLUGIN_NAME] for x in all_unique_adapter_entities_data}),
                        CORRELATION_REASONS: correlation_reasons,
                        'labels': list(set(labels_for_new_device)),
                        HAS_NOTES: has_notes,
                        'tags': list(tags_for_new_device.values())  # Turn it to a list
                    })
            except CorrelateException:
                logger.exception('Unlink logic exception')
                raise

        return internal_axon_id

    @mongo_retry()
    def unlink_adapter(self, entity: EntityType, plugin_unique_name: str, adapter_id: str) -> Iterable[str]:
        """
        Unlinks a specific adapter from its axonius device
        :param entity: The entity type to use
        :param plugin_unique_name: The plugin unique name of the given adapter
        :param adapter_id: The ID of the given adapter
        :return: all internal_axon_ids altered
        """
        _entities_db = self._entity_db_map[entity]
        with _entities_db.start_session() as db_session:
            with db_session.start_transaction():
                return self.__perform_unlink_with_session(adapter_id, plugin_unique_name, db_session, entity)

    @staticmethod
    def _get_kept_and_pulled_tags(entity_to_split, adapter_entities_left_by_id):
        """
        Gets the tags to keep / remove from the entity to split
        :param entity_to_split: The entity to split
        :param adapter_entities_left_by_id: List of the adapter entities left
        :return: Tuple of tags to remove and tags to keep
        """
        try:
            # the old entity might and might not keep the tag:
            # if the tag contains an associated_adapter that is also part of the old entity
            # - then this tag is also associated with the old entity
            # if it does not
            # - this this tag is removed from the old entity
            # so now we generate a list of all tags that must be removed from the old entity
            # a tag will be removed if all of its associated_adapters are not in any of the
            # adapter entities left in the old device, i.e. all of its associated_adapters have moved
            tags_to_remove = [tag_from_old
                              for tag_from_old
                              in entity_to_split['tags']
                              if 'tags' in entity_to_split
                              if all(assoc_adapter not in adapter_entities_left_by_id
                                     for assoc_adapter
                                     in tag_from_old['associated_adapters']
                                     if 'associated_adapters' in tag_from_old)]

            # Get all of the tags that are STILL kept in the old entity
            # We use them to figure out if the old entity still has any notes
            tags_to_keep = [tag_from_old
                            for tag_from_old
                            in entity_to_split['tags']
                            if 'tags' in entity_to_split
                            if any(assoc_adapter in adapter_entities_left_by_id
                                   for assoc_adapter
                                   in tag_from_old['associated_adapters']
                                   if 'associated_adapters' in tag_from_old)]

            return tags_to_remove, tags_to_keep

        except Exception:
            logger.exception('Error accessing tags of the entity to split')

    # pylint: disable=too-many-locals
    @staticmethod
    def __perform_unlink_with_session(adapter_id: str, plugin_unique_name: str,
                                      db_session, entity_type: EntityType, entity_to_split=None) -> Tuple[str, str]:
        """
        Perform an unlink given a session on a particular adapter entity
        :param adapter_id: the id of the adapter to unlink
        :param plugin_unique_name: the plugin unique name of the adapter
        :param db_session: the session to use, this also implies the DB to use
        :param entity_type: the entity type
        :param entity_to_split: if not none, uses this as the entity (optimization)
        :return: Tuple of two strings that represent the internal_axon_ids altered
        """
        entity_to_split = entity_to_split or db_session.find_one({
            'adapters.quick_id': get_preferred_quick_adapter_id(plugin_unique_name, adapter_id)
        })
        if not entity_to_split:
            raise CorrelateException(f'Could not find given entity {plugin_unique_name}:{adapter_id}')
        if len(entity_to_split['adapters']) == 1:
            raise CorrelateException('Only one adapter entity in axonius entity, can\'t split that')
        adapter_to_extract = [x for x in entity_to_split['adapters'] if
                              x[PLUGIN_UNIQUE_NAME] == plugin_unique_name and
                              x['data']['id'] == adapter_id]
        if len(adapter_to_extract) != 1:
            logger.debug(f'Weird entity with {entity_to_split}')
            raise CorrelateException(f'Weird entity with {len(adapter_to_extract)} adapters')
        adapter_to_extract = adapter_to_extract[0]

        internal_axon_id = get_preferred_internal_axon_id_from_dict(adapter_to_extract, entity_type)
        new_axonius_entity = {
            'internal_axon_id': internal_axon_id,
            'accurate_for_datetime': datetime.now(),
            'adapters': [adapter_to_extract],
            'tags': []
        }

        update_internal_axon_id = False

        if internal_axon_id == entity_to_split['internal_axon_id']:
            selected_adapter_entity = [x
                                       for x
                                       in entity_to_split['adapters']
                                       if x[PLUGIN_UNIQUE_NAME] != adapter_to_extract[PLUGIN_UNIQUE_NAME] or
                                       x['data']['id'] != adapter_to_extract['data']['id']
                                       ][0]
            update_internal_axon_id = get_preferred_internal_axon_id_from_dict(selected_adapter_entity, entity_type)

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
                    newtag['associated_adapters'] = [[tag_plugin_unique_name, tag_adapter_id]]
                    new_axonius_entity['tags'].append(newtag)
        # remove the adapters one by one from the DB, and also keep track in memory
        adapter_entities_left = list(entity_to_split['adapters'])

        for adapter_to_remove_from_old in new_axonius_entity['adapters']:
            adapter_entities_left.remove(adapter_to_remove_from_old)

        recalculate_adapter_oldness(adapter_entities_left, entity_type)

        update_dict = {
            '$set': {
                'adapters': adapter_entities_left
            }
        }

        if update_internal_axon_id:
            update_dict['$set']['internal_axon_id'] = update_internal_axon_id

        update_dict['$set']['accurate_for_datetime'] = datetime.now()

        db_session.update_one({
            'internal_axon_id': entity_to_split['internal_axon_id']
        }, update_dict)

        if update_internal_axon_id:
            entity_to_split['internal_axon_id'] = update_internal_axon_id

        # generate a list of (unique_plugin_name, id) from the adapter entities left
        adapter_entities_left_by_id = [
            [adapter[PLUGIN_UNIQUE_NAME], adapter['data']['id']]
            for adapter
            in adapter_entities_left
        ]

        # Get tags to remove from the entity to split and tags to keep
        entity_to_split_tags = PluginBase._get_kept_and_pulled_tags(entity_to_split, adapter_entities_left_by_id)
        pull_those = entity_to_split_tags[0]
        kept_tags = entity_to_split_tags[1]

        set_query = {
            ADAPTERS_LIST_LENGTH: len(set(x[PLUGIN_NAME] for x in adapter_entities_left)),
            'accurate_for_datetime': datetime.now(),
            HAS_NOTES: any(tag.get('name', None) == NOTES_DATA_TAG and tag.get('data', None)
                           for tag in kept_tags)
        }
        if pull_those:
            pull_query = {
                'tags': {
                    '$or': [
                        {
                            PLUGIN_UNIQUE_NAME: pull_this_tag[PLUGIN_UNIQUE_NAME],
                            'name': pull_this_tag['name']
                        }
                        for pull_this_tag
                        in pull_those
                    ]

                }
            }
            full_query = {
                '$pull': pull_query,
                '$set': set_query
            }
        else:
            full_query = {
                '$set': set_query
            }
        db_session.update_one({
            'internal_axon_id': entity_to_split['internal_axon_id']
        }, full_query)
        new_axonius_entity[ADAPTERS_LIST_LENGTH] = len({x[PLUGIN_NAME] for x in new_axonius_entity['adapters']})
        new_axonius_entity[HAS_NOTES] = any(tag.get('name', None) == NOTES_DATA_TAG and tag.get('data', None)
                                            for tag in new_axonius_entity['tags']
                                            if 'tags' in new_axonius_entity)
        recalculate_adapter_oldness(new_axonius_entity['adapters'], entity_type)
        db_session.insert_one(new_axonius_entity)

        return internal_axon_id, entity_to_split['internal_axon_id']
    # pylint: disable=too-many-locals

    def __archive_axonius_device(self, plugin_unique_name, device_id, entity_type: EntityType, db_session=None):
        """
        Finds the axonius device with the given plugin_unique_name and device id,
        assumes that the axonius device has only this single adapter device.

        If you want to delete an adapter entity use delete_adapter_entity

        writes the device to the archive db, then deletes it
        """
        self._raw_adapter_entity_db_map[entity_type].find_one_and_delete({
            PLUGIN_UNIQUE_NAME: plugin_unique_name,
            'id': device_id
        })
        axonius_device = self._entity_db_map[entity_type].find_one_and_delete({
            'adapters.quick_id': get_preferred_quick_adapter_id(plugin_unique_name, device_id)
        }, session=db_session)
        if axonius_device is None:
            logger.error(f'Tried to delete nonexistent device: {plugin_unique_name}: {device_id}')
            return False
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
        db_filter = {
            'adapters.quick_id': get_preferred_quick_adapter_id(plugin_unique_name, adapter_id)
        }
        with _entities_db.start_session() as db_session:
            with db_session.start_transaction():
                axonius_entity = db_session.find_one(db_filter)
                if not axonius_entity:
                    logger.debug(f'{entity}, {plugin_unique_name}, {adapter_id} not found for deletion')

                    # If the transaction is playing with us
                    if _entities_db.count_documents(db_filter, limit=1):
                        raise CustomRetryOperation()

                    return

                # if the condition below isn't met it means
                # that the current adapterentity is the last adapter in the axoniusentity
                # in which case - there is no reason to unlink it, just to delete it
                amount_of_adapters = len(axonius_entity['adapters'])
                if amount_of_adapters > 1:
                    logger.debug(f'{entity}, {plugin_unique_name}, {adapter_id} has  {amount_of_adapters}')
                    self.__perform_unlink_with_session(adapter_id, plugin_unique_name, db_session, entity,
                                                       entity_to_split=axonius_entity)
        # By not having this a part of the transaction, we significantly mitigate
        try:
            self.__archive_axonius_device(plugin_unique_name, adapter_id, entity)
        except pymongo.errors.PyMongoError:
            logger.warning(f'Failed archiving axnoius device {plugin_unique_name}, {adapter_id}', exc_info=True)
        except Exception:
            logger.exception(f'Failed archiving axnoius device {plugin_unique_name}, {adapter_id}')

    def __add_many_labels_to_entity_huge(self, entity: EntityType, identity_by_adapter, labels,
                                         are_enabled=True, with_results=False):
        """
        See add_many_labels_to_entity for all the docs
        This is the optional optimization that delegates the work to the heavy lifting plugin because
        sometimes adding a lot of tags can take a long while on a non-SMP process.
        """
        for label in labels:
            # pylint: disable=cell-var-from-loop
            def perform_tag(specific_identities_chunk: Iterable[dict]):
                try:
                    res = self.request_remote_plugin('tag_entities', HEAVY_LIFTING_PLUGIN_NAME,
                                                     'post', json={
                                                         'entity': entity.value,
                                                         'identity_by_adapter': list(specific_identities_chunk),
                                                         'labels': [label],
                                                         'are_enabled': are_enabled,
                                                         'is_huge': False,
                                                         'with_results': with_results
                                                     })
                    if with_results:
                        return res.json()
                    return None
                except Exception:
                    logger.exception(f'Problem adding label: {label}')
            # pylint: enable=cell-var-from-loop

            yield from self._common_executor.map(perform_tag, chunks(1000, identity_by_adapter))

    def add_many_labels_to_entity(self, entity: EntityType, identity_by_adapter, labels,
                                  are_enabled=True, is_huge: bool = False, with_results: bool = False) -> List[dict]:
        """
        Tag many devices with many tags. if is_enabled = False, the labels are grayed out.
        :param is_huge: If True, will use heavy_lifting plugin for assistance
        :return: List of affected entities
        """
        if is_huge:
            return list(self.__add_many_labels_to_entity_huge(entity, identity_by_adapter, labels, are_enabled,
                                                              with_results))

        def perform_many_tags():
            for label in labels:
                for specific_identity in identity_by_adapter:
                    try:
                        yield from self.add_label_to_entity(entity, [specific_identity], label, are_enabled)
                    except Exception:
                        logger.exception(f'Problem adding label: {label} with identity: {specific_identity}')

        return list(perform_many_tags())

    def add_label_to_entity(self, entity: EntityType, identity_by_adapter, label, is_enabled=True,
                            additional_data=None) -> List[dict]:
        """
        A shortcut to __tag with type 'label' . if is_enabled = False, the label is grayed out.
        :return: List of affected entities
        """
        if additional_data is None:
            additional_data = {}

        # all labels belong to GUI
        additional_data[PLUGIN_UNIQUE_NAME], additional_data[PLUGIN_NAME] = GUI_PLUGIN_NAME, GUI_PLUGIN_NAME
        additional_data['label_value'] = label if is_enabled else ''

        result = self._tag(entity, identity_by_adapter, label, is_enabled, 'label', 'replace', None,
                           additional_data)
        return result

    def add_data_to_entity(self, entity: EntityType, identity_by_adapter, name, data, additional_data=None,
                           action_if_exists='replace') -> List[dict]:
        """
        A shortcut to __tag with type 'data'
        :return: List of affected entities
        """
        if additional_data is None:
            additional_data = {}
        result = self._tag(entity, identity_by_adapter, name, data, 'data', action_if_exists, None, additional_data)
        return result

    def add_adapterdata_to_entity(self, entity: EntityType, identity_by_adapter, data,
                                  action_if_exists='replace', client_used=None, additional_data=None) -> List[dict]:
        """
        A shortcut to __tag with type 'adapterdata'
        :return: List of affected entities
        """
        if additional_data is None:
            additional_data = {}
        result = self._tag(entity, identity_by_adapter, self.plugin_unique_name, data, 'adapterdata',
                           action_if_exists, client_used, additional_data)
        for key in data:
            self.__existing_fields[entity].add(key)
        return result

    @add_rule('update_config', methods=['POST'], should_authenticate=False)
    def update_config(self):
        return self._update_config_inner()

    def _global_config_updated(self):
        """
        hook that is called when global settings are updated
        """

    def _update_config_inner(self):
        self.renew_config_from_db()
        self.__renew_global_settings_from_db()
        self.update_fips_status()
        self._global_config_updated()
        return ''

    def get_opsgenie_connection(self):
        opsgenie_settings = self._opsgenie_settings
        if opsgenie_settings['enabled'] is not True:
            return None
        return OpsgenieConnection(domain=opsgenie_settings['domain'],
                                  apikey=opsgenie_settings['apikey'],
                                  verify_ssl=opsgenie_settings['verify_ssl'],
                                  https_proxy=opsgenie_settings.get('https_proxy'))

    def get_issue_types_names(self):
        jira_settings = self._jira_settings
        if jira_settings['enabled'] is not True:
            return []
        try:
            jira = JIRA(options={'server': jira_settings['domain'],
                                 'verify': jira_settings['verify_ssl']},
                        basic_auth=(jira_settings['username'], jira_settings['password']))
            return [issue_type.name for issue_type in jira.issue_types()]
        except Exception as e:
            logger.exception('Error in getting issue type')
            return []

    def get_jira_keys(self):
        jira_settings = self._jira_settings
        if jira_settings['enabled'] is not True:
            return []
        try:
            jira = JIRA(options={'server': jira_settings['domain'],
                                 'verify': jira_settings['verify_ssl']},
                        basic_auth=(jira_settings['username'], jira_settings['password']))
            return [project.key for project in jira.projects()]
        except Exception as e:
            logger.exception('Error in in getting projects keys')
            return []

    # pylint: disable=too-many-arguments
    def create_jira_ticket(self, project_key, summary, description, issue_type,
                           assignee=None, labels=None, components=None, csv_file_name=None, csv_bytes=None,
                           extra_fields=None):
        permalink = None
        jira_settings = self._jira_settings
        if jira_settings['enabled'] is not True:
            return 'Jira Settings missing'
        try:
            jira = JIRA(options={'server': jira_settings['domain'],
                                 'verify': jira_settings['verify_ssl']},
                        basic_auth=(jira_settings['username'], jira_settings['password']))
            issue_dict = {
                'project': {'key': project_key},
                'summary': summary,
                'description': description,
                'issuetype': {'name': issue_type},
            }
            if components and isinstance(components, str):
                components = components.split(',')
                issue_dict['components'] = [{'name': component} for component in components]
            if labels and isinstance(labels, str):
                issue_dict['labels'] = labels.split(',')
            if assignee:
                issue_dict['assignee'] = {'name': assignee}
            try:
                if extra_fields:
                    extra_fields_dict = json.loads(extra_fields)
                    if isinstance(extra_fields_dict, dict):
                        issue_dict.update(extra_fields_dict)
            except Exception:
                logger.exception(f'Problem parsing extra fields')
            issue = jira.create_issue(fields=issue_dict)
            try:
                permalink = issue.permalink()
            except Exception:
                logger.exception(f'Problem get permalink')
            if csv_file_name and csv_bytes:
                jira.add_attachment(issue=issue, attachment=csv_bytes, filename=csv_file_name)
            try:
                # In some cases only this flow works for assignee
                jira.assign_issue(issue, assignee)
            except Exception:
                pass
            return '', permalink
        except Exception as e:
            logger.exception('Error in Jira ticket')
            return str(e), permalink

    def send_external_info_log(self, message):
        try:
            self.send_syslog_message(message, 'info')
        except Exception:
            logger.exception(f'Problem sending syslog message {message}')
        try:
            self.send_https_log_message(message, timeout=5)
        except Exception:
            logger.exception(f'Problem sending https log message {message}')

    def send_syslog_message(self, message, log_level):
        syslog_settings = self._syslog_settings
        if syslog_settings['enabled'] is True:
            full_message = str({'data': message, 'timestamp': str(datetime.now().isoformat())})
            syslog_logger = logging.getLogger('axonius.syslog')
            # Starting the messages with the tag Axonius
            getattr(syslog_logger, log_level)(full_message)

    def send_https_log_message(self, message, authorization_header=None, files=None, timeout=60):
        https_log_setting = self._https_logs_settings
        if https_log_setting['enabled'] is True and https_log_setting.get('https_log_server'):
            full_message = str({'data': message, 'timestamp': str(datetime.now().isoformat())})
            host = https_log_setting.get('https_log_server')
            port = https_log_setting.get('https_log_port') or 443
            https_proxy = https_log_setting.get('https_proxy')
            url = RESTConnection.build_url(domain=host, port=port, use_domain_path=True).strip('/')
            proxies = dict()
            proxies['http'] = None
            proxies['https'] = https_proxy
            headers = None
            if authorization_header:
                headers = dict()
                headers['Authorization'] = authorization_header
            r = requests.post(url=url, data=full_message, proxies=proxies,
                              headers=headers, files=files, timeout=timeout)
            r.raise_for_status()

    def set_global_keyval(self, key: str, val):
        """
        A global key value table that is accessible to everyone.
        :param key: the name of the key
        :param val: the value. can be anything that mongo accepts.
        :return:
        """
        self._get_db_connection()[CORE_UNIQUE_NAME][GLOBAL_KEYVAL_COLLECTION].update_one(
            {'key': key},
            {'$set': {'key': key, 'val': val}},
            upsert=True
        )
        return True

    def get_global_keyval(self, key: str):
        try:
            doc = self._get_db_connection()[CORE_UNIQUE_NAME][GLOBAL_KEYVAL_COLLECTION].find_one({'key': key})
            return doc['val'] if doc else None
        except Exception:
            logger.exception(f'Warning - could not get keyval {key}')
            return None

    @property
    def keyval(self) -> dict:
        """
        Returns in memory dict
        """
        return self.__inmem_keyval

    def get_selected_entities(self, entity_type: EntityType, entities_selection: dict, mongo_filter: dict = None):
        """

        :param entities_selection: Represents the selection of entities.
                If include is True, then ids is the list of selected internal axon ids
                Otherwise, selected internal axon ids are all those fetched by the mongo filter excluding the ids list
        :param entity_type: Type of entity to fetch
        :param mongo_filter: Query to fetch entire data by
        :return: List of internal axon ids that were meant to be selected, according to given selection and filter
        """
        return self.get_selected_ids(self._entity_db_map[entity_type], entities_selection,
                                     mongo_filter, 'internal_axon_id')

    @staticmethod
    def get_selected_ids(mongo_collection, entities_selection: dict, mongo_filter: dict, id_field='_id'):
        """

        :param id_field: the field of the relevant id
        :param entities_selection: Represents the selection of entities.
                If include is True, then ids is the list of selected internal axon ids
                Otherwise, selected internal axon ids are all those fetched by the mongo filter excluding the ids list
        :param mongo_collection: Type of collection to bring from the mongo
        :param mongo_filter: Query to fetch entire data by
        :return: List of internal axon ids that were meant to be selected, according to given selection and filter
        """
        if entities_selection.get('include', True):
            return entities_selection['ids']
        return [entry[id_field] for entry in mongo_collection.find({
            '$and': [
                {id_field: {
                    '$nin': entities_selection['ids']
                }}, mongo_filter
            ]
        }, projection={id_field: 1})]

    def _adapters_with_feature(self, feature: str) -> Set[str]:
        """
        Returns all plugins unique names of plugins that have a specific feature
        """
        return set(x[PLUGIN_UNIQUE_NAME]
                   for x in
                   self.core_configs_collection.find(
                       filter={
                           'supported_features': feature,
                       },
                       projection={
                           PLUGIN_UNIQUE_NAME: 1
                       }))

    @property
    def mail_sender(self):
        email_settings = self._email_settings
        if email_settings['enabled'] is True:
            return EmailServer(email_settings['smtpHost'], email_settings['smtpPort'],
                               email_settings.get('smtpUser'), email_settings.get('smtpPassword'),
                               ssl_state=SSLState[email_settings.get('use_ssl', SSLState.Unencrypted.name)],
                               keyfile_data=self._grab_file_contents(email_settings.get('private_key'),
                                                                     stored_locally=False),
                               certfile_data=self._grab_file_contents(email_settings.get('cert_file'),
                                                                      stored_locally=False),
                               ca_file_data=self._grab_file_contents(email_settings.get('ca_file'),
                                                                     stored_locally=False),
                               source=email_settings.get('sender_address'))
        return None

    @property
    def vault_pwd_mgmt(self) -> AbstractVaultConnection:
        return self._vault_connection

    def check_password_fetch(self, adapter_field_name: str, vault_data: dict) -> bool:
        """
        Checks if the query correctly fetches a password from the requested vault.
        :param vault_data: The query data to use to fetch from vault.
        :param adapter_field_name: The field name for gui to recognize.
        :return: True if successfully fetched the password.
        """
        password = self.vault_pwd_mgmt.query_password(adapter_field_name, vault_data)
        return password is not None

    # Global settings
    # These are settings which are shared between all plugins. For example, all plugins should use the same
    # mail server when doing reports.
    # Adding or changing a settings requires a full restart of the system
    # and making sure you don't break a setting somebody else uses.

    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    def __renew_global_settings_from_db(self):
        # pylint: disable=global-statement,invalid-name
        logger.info(f'Reloading global settings')
        global limiter_settings
        config = self.plugins.core.configurable_configs[CORE_CONFIG_NAME]
        # pylint: disable=invalid-name
        self._email_settings = config['email_settings']
        self._getting_started_settings = config[GETTING_STARTED_CHECKLIST_SETTING]
        self._https_logs_settings = config['https_log_settings']
        self._notify_on_adapters = False
        self._adapter_errors_mail_address = config[NOTIFICATIONS_SETTINGS].get(ADAPTERS_ERRORS_MAIL_ADDRESS)
        self._adapter_errors_webhook = config[NOTIFICATIONS_SETTINGS].get(ADAPTERS_ERRORS_WEBHOOK_ADDRESS)
        self._email_prefix_correlation = config[CORRELATION_SETTINGS].get(CORRELATE_BY_EMAIL_PREFIX)
        self._ad_display_name_correlation = config[CORRELATION_SETTINGS].get(CORRELATE_AD_DISPLAY_NAME)
        self._username_aws_correlation = config[CORRELATION_SETTINGS].get(CORRELATE_AWS_USERNAME)
        self._correlate_only_on_username_domain = config[CORRELATION_SETTINGS].get(CORRELATE_BY_USERNAME_DOMAIN_ONLY)
        self._fetch_empty_vendor_software_vulnerabilites = (config.get(STATIC_ANALYSIS_SETTINGS) or {}).get(
            FETCH_EMPTY_VENDOR_SOFTWARE_VULNERABILITES) or False
        self._correlate_ad_sccm = config[CORRELATION_SETTINGS].get(CORRELATE_AD_SCCM, True)
        self._csv_full_hostname = config[CORRELATION_SETTINGS].get(CSV_FULL_HOSTNAME, True)
        self._correlate_by_snow_mac = config[CORRELATION_SETTINGS].get(CORRELATE_BY_SNOW_MAC, False)
        self._correlate_azure_ad_name_only = config[CORRELATION_SETTINGS].get(CORRELATE_BY_AZURE_AD_NAME_ONLY, False)
        self._correlate_snow_no_dash = config[CORRELATION_SETTINGS].get(CORRELATE_SNOW_NO_DASH, False)
        self._correlate_public_ip_only = config[CORRELATION_SETTINGS].get(CORRELATE_PUBLIC_IP_ONLY, False)
        self._allow_service_now_by_name_only = config[CORRELATION_SETTINGS].get(ALLOW_SERVICE_NOW_BY_NAME_ONLY, False)
        self._global_hostname_correlation = config[CORRELATION_SETTINGS].get(CORRELATE_GLOBALY_ON_HOSTNAME, False)
        self._jira_settings = config['jira_settings']
        self._opsgenie_settings = config.get('opsgenie_settings')
        self._proxy_settings = config[PROXY_SETTINGS]
        self._password_policy_settings = config[PASSWORD_SETTINGS]
        self._password_protection_settings = config[PASSWORD_BRUTE_FORCE_PROTECTION]
        limiter_settings = self._password_protection_settings
        self._vault_settings = config['vault_settings']
        self._aws_s3_settings = config.get('aws_s3_settings') or {}
        self._smb_settings = config.get('smb_settings') or {}
        self._global_ssl = config.get('global_ssl') or {}
        self._ssl_trust_settings = config.get('ssl_trust_settings') or {}
        self._static_analysis_settings = config.get(STATIC_ANALYSIS_SETTINGS) or {}
        self._correlation_schedule_settings = config[CORRELATION_SCHEDULE]
        self.update_fips_status()

        self._socket_recv_timeout = DEFAULT_SOCKET_RECV_TIMEOUT
        self._socket_read_timeout = DEFAULT_SOCKET_READ_TIMEOUT
        self._update_adapters_clients_periodically = config[AGGREGATION_SETTINGS].get(UPDATE_CLIENTS_STATUS, False)
        self._uppercase_hostnames = config[AGGREGATION_SETTINGS].get(UPPERCASE_HOSTNAMES) or False
        try:
            socket_read_timeout = int(config[AGGREGATION_SETTINGS].get(SOCKET_READ_TIMEOUT))
            if socket_read_timeout > 0:
                self._socket_read_timeout = socket_read_timeout
        except Exception:
            logger.exception(f'Could not set socket read timout')
        self._configured_session_timeout = (self._socket_read_timeout, self._socket_recv_timeout)

        # vault settings have to come after self._configured_session_timeout has been configured
        # because it uses it
        if self._vault_settings['enabled'] is True:
            self._vault_connection = self._vault_connection_factory()

        # enable: disable=invalid-name
        self._aggregation_max_workers = None
        try:
            max_workers = int(config[AGGREGATION_SETTINGS].get(MAX_WORKERS))
            if max_workers > 0:
                self._aggregation_max_workers = max_workers
        except Exception:
            pass

        current_syslog = getattr(self, '_syslog_settings', None)
        if current_syslog != config['syslog_settings']:
            logger.info('new syslog settings arrived')
            self.__create_syslog_handler(config['syslog_settings'])
            self._syslog_settings = config['syslog_settings']
        else:
            self._syslog_settings = current_syslog

        ssl_trust_settings = config.get('ssl_trust_settings') or {}
        if ssl_trust_settings.get('enabled'):
            try:
                for ca_file_index, ca_file in enumerate((ssl_trust_settings.get('ca_files') or [])):
                    ca_key = self._grab_file_contents(ca_file, stored_locally=False)
                    if not ca_key or b'-BEGIN CERTIFICATE-' not in ca_key or b'-END CERTIFICATE-' not in ca_key:
                        logger.error(f'Invalid SSL CA certificate at position {ca_file_index}, not updating')
                    elif b'ENCRYPTED' in ca_key:
                        logger.error(f'Encrypted SSL CA certificate at position {ca_file_index}, not updating')
                    else:
                        specific_ca_path = os.path.join(CA_CERT_PATH, f'customer_ca_{ca_file_index}.crt')
                        open(specific_ca_path, 'wb').write(ca_key)
                        os.chmod(CA_CERT_PATH, 0o666)
                        subprocess.check_call(['update-ca-certificates'])
                        logger.info(f'Successfully loaded CA certificates to the system.')
            except Exception:
                logger.exception(f'Could not load ssl certificates.')
        else:
            try:
                for ca_file_index in range(30):
                    specific_ca_path = os.path.join(CA_CERT_PATH, f'customer_ca_{ca_file_index}.crt')
                    if os.path.exists(specific_ca_path):
                        os.unlink(specific_ca_path)
                subprocess.check_call(['update-ca-certificates'])
            except Exception:
                logger.exception(f'Could not delete CA Certificate. bypassing')

        global_ssl = config['global_ssl']
        if global_ssl.get('enabled'):
            config_cert = self._grab_file_contents(global_ssl.get('cert_file'), stored_locally=False)
            config_key = self._grab_file_contents(global_ssl.get('private_key'), stored_locally=False)
            config_key_no_passphrase = get_private_key_without_passphrase(config_key, global_ssl.get('passphrase'))

            with open(SSL_CERT_PATH, 'rb') as fh:
                current_cert = fh.read()
            with open(SSL_KEY_PATH, 'rb') as fh:
                current_key = fh.read()

            if config_cert != current_cert or config_key_no_passphrase != current_key:
                with open(SSL_CERT_PATH, 'wb') as fh:
                    fh.write(config_cert)
                with open(SSL_KEY_PATH, 'wb') as fh:
                    fh.write(config_key_no_passphrase)

                # Restart Openresty (NGINX)
                subprocess.check_call(['openresty', '-s', 'reload'])

        else:
            current_cert = open(SSL_CERT_PATH, 'rb').read()
            axonius_cert = open(SSL_CERT_PATH_LIBS, 'rb').read()
            if current_cert != axonius_cert:
                with open(SSL_CERT_PATH, 'wb') as fh:
                    fh.write(axonius_cert)
                with open(SSL_KEY_PATH, 'wb') as fh:
                    with open(SSL_KEY_PATH_LIBS, 'rb') as fhr:
                        fh.write(fhr.read())

                # Restart Openresty (NGINX)
                subprocess.check_call(['openresty', '-s', 'reload'])

    # pylint: enable=too-many-branches
    # pylint: enable=too-many-statements

    def __create_syslog_handler(self, syslog_settings: dict):
        """
        Replaces the syslog handler used with the provided
        """
        try:
            # No syslog handler defined yet or settings changed.
            # We should replace the current handler with a new one.
            logger.info(f'Initializing new handler to syslog logger (deleting old if exist) from {syslog_settings}')
            syslog_port = syslog_settings.get('syslogPort') or 6514
            if not isinstance(syslog_port, int):
                raise TypeError(f'Syslog port is not an integer')

            syslog_logger = logging.getLogger('axonius.syslog')
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
                                                           syslog_port),
                                                  facility=logging.handlers.SysLogHandler.LOG_DAEMON,
                                                  ssl_kwargs=ssl_kwargs)
            else:
                syslog_handler = logging.handlers.SysLogHandler(
                    address=(syslog_settings['syslogHost'],
                             syslog_settings.get('syslogPort',
                                                 logging.handlers.SYSLOG_UDP_PORT)),
                    facility=logging.handlers.SysLogHandler.LOG_DAEMON)
            syslog_handler.setLevel(logging.INFO)
            syslog_logger.addHandler(syslog_handler)
        except Exception:
            logger.exception(f'Failed setting up syslog handler, no syslog handler has been set up, {syslog_settings}')

    def update_fips_status(self):
        try:
            feature_flags_config = self.feature_flags_config()
            if feature_flags_config and feature_flags_config.get(FeatureFlagsNames.EnableFIPS, False):
                MongoEncrypt.enable_fips()
            else:
                MongoEncrypt.disable_fips()
        except TypeError:
            # Probably first boot and gui didnt initialize yet
            MongoEncrypt.disable_fips()

    def feature_flags_config(self) -> dict:
        return self.plugins.gui.configurable_configs[FEATURE_FLAGS_CONFIG]

    @staticmethod
    def _compliance_expired(expiry_date):
        """
        Check whether system has a trial expiration that has passed
        """
        if not expiry_date:
            return False
        return parse_date(expiry_date) < parse_date(datetime.now())

    @singlethreaded()
    @cachetools.cached(cachetools.TTLCache(maxsize=1, ttl=5), lock=threading.Lock())
    def should_cloud_compliance_run(self) -> bool:
        if self.is_in_mock_mode:
            return False
        cloud_compliance_settings = self.feature_flags_config().get(FeatureFlagsNames.CloudCompliance) or {}
        # If we are in trial, or if the cloud compliance feature has been enabled, run this.
        is_cloud_compliance_enabled = cloud_compliance_settings.get(CloudComplianceNames.Enabled)
        is_cloud_compliance_visible = cloud_compliance_settings.get(CloudComplianceNames.Visible)
        is_cloud_compliance_expired = self._compliance_expired(cloud_compliance_settings.get(
            CloudComplianceNames.ExpiryDate))
        compliance_enabled = self.is_in_trial() or is_cloud_compliance_enabled
        return is_cloud_compliance_visible and compliance_enabled and not is_cloud_compliance_expired

    @singlethreaded()
    @cachetools.cached(cachetools.TTLCache(maxsize=1, ttl=5), lock=threading.Lock())
    def trial_expired(self):
        """
        Check whether system has a trial expiration that has passed
        """
        feature_flags_config = self.feature_flags_config()
        if not feature_flags_config.get(FeatureFlagsNames.TrialEnd):
            return False
        return parse_date(feature_flags_config[FeatureFlagsNames.TrialEnd]) < parse_date(datetime.now())

    @singlethreaded()
    @cachetools.cached(cachetools.TTLCache(maxsize=1, ttl=5), lock=threading.Lock())
    def contract_expired(self):
        """
        Check whether system has a contract expiration that has passed
        """
        feature_flags_config = self.feature_flags_config()
        if not feature_flags_config.get(FeatureFlagsNames.ExpiryDate):
            return False
        return parse_date(feature_flags_config[FeatureFlagsNames.ExpiryDate]) < parse_date(datetime.now()) and \
            feature_flags_config.get(FeatureFlagsNames.LockOnExpiry)

    def is_in_trial(self):
        """
        Returns True if we are in trial mode, but trial has not expired yet.
        :return:
        """
        feature_flags_config = self.feature_flags_config()
        # If there is no 'Trial End' then the system is licensed - we are not in trial.
        if not feature_flags_config.get(FeatureFlagsNames.TrialEnd):
            return False
        # If the trial did not end yet - we are not in trial.
        return parse_date(feature_flags_config[FeatureFlagsNames.TrialEnd]) > parse_date(datetime.now())

    @staticmethod
    def global_settings_schema():
        return {
            'items': [
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Configure custom SSL certificate',
                            'hidden': True,
                            'type': 'bool'
                        },
                        {
                            'name': 'hostname',
                            'title': 'Domain name',
                            'type': 'string'
                        },
                        *MANDATORY_SSL_CONFIG_SCHEMA,
                        {
                            'name': 'passphrase',
                            'title': 'Private key passphrase',
                            'description': 'An optional passphrase for the private key file',
                            'type': 'string',
                            'format': 'password'
                        }
                    ],
                    'name': 'global_ssl',
                    'title': 'GUI SSL Settings',
                    'hidden': True,
                    'type': 'array',
                    'required': ['enabled', 'hostname', 'cert_file', 'private_key']
                },
                {
                    'name': 'ssl_trust_settings',
                    'title': 'SSL Trust & CA Settings',
                    'type': 'array',
                    'hidden': True,
                    'required': ['enabled', 'ca_files'],
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Use custom CA certificate',
                            'type': 'bool'
                        },
                        {
                            'name': 'ca_files',
                            'title': 'CA Certificates',
                            'type': 'array',
                            'items': {
                                'type': 'file'
                            }
                        }
                    ]
                },
                {
                    'required': ['status', 'csr_file', 'subject_name', 'submission_date', 'key_file'],
                    'name': 'csr_settings',
                    'format': 'hidden',
                    'type': 'array',
                    'items': [
                        {
                            'name': 'status',
                            'type': 'bool'
                        },
                        {
                            'name': 'subject_name',
                            'type': 'string'
                        },
                        {
                            'name': 'submission_date',
                            'type': 'string',
                            'format': 'date-time'
                        },
                        {
                            'name': 'csr_file',
                            'type': 'file'
                        },
                        {
                            'name': 'key_file',
                            'type': 'file'
                        }
                    ]
                },
                {
                    'name': PROXY_SETTINGS,
                    'title': 'Proxy Settings',
                    'type': 'array',
                    'required': ['enabled', 'proxy_addr', 'proxy_port', PROXY_VERIFY],
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Proxy enabled',
                            'type': 'bool',
                            'required': True
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
                            'title': 'Proxy user name',
                            'type': 'string'
                        },
                        {
                            'name': PROXY_PASSW,
                            'title': 'Proxy password',
                            'type': 'string',
                            'format': 'password'
                        },
                        {
                            'name': PROXY_VERIFY,
                            'title': 'Verify SSL',
                            'type': 'bool'
                        }
                    ]
                },
                {
                    'name': TUNNEL_SETTINGS,
                    'type': 'array',
                    'required': [TUNNEL_EMAILS_RECIPIENTS],
                    'format': 'hidden',
                    'items': [
                        {
                            'name': TUNNEL_EMAILS_RECIPIENTS,
                            'type': 'array',
                            'items': []
                        },
                        {
                            'name': TUNNEL_PROXY_SETTINGS,
                            'type': 'array',
                            'items': [
                                {
                                    'name': 'enabled',
                                    'type': 'bool'
                                },
                                {
                                    'name': TUNNEL_PROXY_ADDR,
                                    'type': 'string'
                                },
                                {
                                    'name': TUNNEL_PROXY_PORT,
                                    'type': 'number'
                                },
                                {
                                    'name': TUNNEL_PROXY_USER,
                                    'type': 'string'
                                },
                                {
                                    'name': TUNNEL_PROXY_PASSW,
                                    'type': 'string'
                                }
                            ]
                        }
                    ]
                },
                {
                    'name': PASSWORD_SETTINGS,
                    'title': 'Password Policy Settings',
                    'type': 'array',
                    'required': ['enabled', PASSWORD_LENGTH_SETTING],
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Enforce password complexity',
                            'type': 'bool',
                            'required': True
                        },
                        {
                            'name': PASSWORD_LENGTH_SETTING,
                            'title': 'Minimum password length',
                            'type': 'number',
                        },
                        {
                            'name': PASSWORD_MIN_LOWERCASE,
                            'title': 'Minimum lowercase letters required',
                            'type': 'number',
                        },
                        {
                            'name': PASSWORD_MIN_UPPERCASE,
                            'title': 'Minimum uppercase letters required',
                            'type': 'number',
                        },
                        {
                            'name': PASSWORD_MIN_NUMBERS,
                            'title': 'Minimum numbers required',
                            'type': 'number',
                        },
                        {
                            'name': PASSWORD_MIN_SPECIAL_CHARS,
                            'title': 'Minimum special characters required',
                            'description': 'Special characters list: ~!@#$%^&*_-+=`|\\(){}[]:;"\'<>,.?/',
                            'type': 'number',
                        }
                    ]
                },
                {
                    'name': RESET_PASSWORD_SETTINGS,
                    'title': 'Password Reset Settings',
                    'type': 'array',
                    'required': [RESET_PASSWORD_LINK_EXPIRATION],
                    'items': [
                        {
                            'name': RESET_PASSWORD_LINK_EXPIRATION,
                            'title': 'Reset password link expiration (hours)',
                            'type': 'integer',
                            'min': 1,
                            'required': True,
                        },
                    ]
                },
                {
                    'name': PASSWORD_BRUTE_FORCE_PROTECTION,
                    'title': 'Password Brute Force Settings',
                    'type': 'array',
                    'required': ['enabled', 'conditional',
                                 PASSWORD_PROTECTION_ALLOWED_RETRIES, PASSWORD_PROTECTION_LOCKOUT_MIN],
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Enable Brute force protection',
                            'type': 'bool',
                            'required': True
                        },
                        {
                            'name': PASSWORD_PROTECTION_ALLOWED_RETRIES,
                            'title': 'Maximum attempts',
                            'description': 'Maximum attempts value must be greater than 4',
                            'type': 'number',
                        },
                        {
                            'name': PASSWORD_PROTECTION_LOCKOUT_MIN,
                            'title': 'Window size in minutes',
                            'type': 'number',
                        },
                        {
                            'name': 'conditional',
                            'title': 'Lock type',
                            'type': 'string',
                            'enum': [
                                {
                                    'name': PASSWORD_PROTECTION_BY_IP,
                                    'title': 'IP address'
                                },
                                {
                                    'name': PASSWORD_PROTECTION_BY_USERNAME,
                                    'title': 'User name'
                                }
                            ]
                        }
                    ]
                },
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Use Password Manager',
                            'type': 'bool'
                        },
                        {
                            'name': 'conditional',
                            'title': 'Password Manager',
                            'enum': [
                                {
                                    'name':  VaultProvider.CyberArk.value,
                                    'title': 'CyberArk Vault'
                                },
                                {
                                    'name': VaultProvider.Thycotic.value,
                                    'title': 'Thycotic Secret Server'
                                }
                            ],
                            'type': 'string'
                        },
                        {
                            'name': VaultProvider.CyberArk.value,
                            'type': 'array',
                            'items': [
                                {
                                    'name': CYBERARK_DOMAIN,
                                    'title': 'CyberArk domain',
                                    'type': 'string'
                                },
                                {
                                    'name': CYBERARK_PORT,
                                    'title': 'Port',
                                    'type': 'integer',
                                    'format': CYBERARK_PORT
                                },
                                {
                                    'name': CYBERARK_APP_ID,
                                    'title': 'Application ID',
                                    'type': 'string',
                                },
                                {
                                    'name': CYBERARK_CERT_KEY,
                                    'title': 'Certificate key',
                                    'type': 'file'
                                }
                            ],
                            'required': [CYBERARK_DOMAIN, CYBERARK_APP_ID, CYBERARK_CERT_KEY, CYBERARK_PORT]
                        },
                        {
                            'name': VaultProvider.Thycotic.value,
                            'type': 'array',
                            'items': [
                                {
                                    'name': THYCOTIC_SS_HOST,
                                    'title': 'Thycotic Secret Server URL',
                                    'type': 'string'
                                },
                                {
                                    'name': THYCOTIC_SS_USERNAME,
                                    'title': 'User name',
                                    'type': 'string',
                                },
                                {
                                    'name': THYCOTIC_SS_PASSWORD,
                                    'title': 'Password',
                                    'type': 'string',
                                    'format': 'password'
                                },
                                {
                                    'name': THYCOTIC_SS_PORT,
                                    'title': 'Port',
                                    'type': 'integer',
                                    'format': THYCOTIC_SS_PORT
                                },
                                {
                                    'name': THYCOTIC_SS_VERIFY_SSL,
                                    'title': 'Verify SSL',
                                    'type': 'bool',
                                }
                            ],
                            'required': [THYCOTIC_SS_HOST, THYCOTIC_SS_USERNAME, THYCOTIC_SS_PASSWORD]
                        }
                    ],
                    'name': 'vault_settings',
                    'title': 'Enterprise Password Management Settings',
                    'type': 'array',
                    'required': ['enabled']
                },
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Send emails',
                            'type': 'bool'
                        },
                        {
                            'name': 'smtpHost',
                            'title': 'Email host',
                            'type': 'string'
                        },
                        {
                            'name': 'smtpPort',
                            'title': 'Port',
                            'type': 'integer',
                            'format': 'port'
                        },
                        {
                            'name': 'smtpUser',
                            'title': 'User name',
                            'type': 'string'
                        },
                        {
                            'name': 'smtpPassword',
                            'title': 'Password',
                            'type': 'string',
                            'format': 'password'
                        },
                        *COMMON_SSL_CONFIG_SCHEMA,
                        {
                            'name': 'sender_address',
                            'title': 'Sender address',
                            'type': 'string'
                        }
                    ],
                    'name': 'email_settings',
                    'title': 'Email Settings',
                    'type': 'array',
                    'required': ['enabled', 'smtpHost', 'smtpPort']
                },
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Use Syslog',
                            'type': 'bool'
                        },
                        {
                            'name': 'syslogHost',
                            'title': 'Syslog host',
                            'type': 'string'
                        },
                        {
                            'name': 'syslogPort',
                            'title': 'Port',
                            'type': 'integer',
                            'format': 'port'
                        },
                        *COMMON_SSL_CONFIG_SCHEMA
                    ],
                    'name': 'syslog_settings',
                    'title': 'Syslog Settings',
                    'type': 'array',
                    'required': ['enabled', 'syslogHost']
                },
                {
                    'https_log_settings': {
                        'enabled': False,
                        'https_log_server': None
                    },
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Use HTTPS logs',
                            'type': 'bool'
                        },
                        {
                            'name': 'https_log_server',
                            'title': 'HTTPS logs host',
                            'type': 'string'
                        },
                        {
                            'name': 'https_log_port',
                            'title': 'Port',
                            'type': 'integer',
                            'format': 'port'
                        },
                        {
                            'name': 'https_proxy',
                            'title': 'HTTPS proxy',
                            'type': 'string'
                        }
                    ],
                    'name': 'https_log_settings',
                    'title': 'HTTPS Logs Settings',
                    'type': 'array',
                    'required': ['enabled', 'https_log_server']
                },
                {
                    'type': 'array',
                    'title': 'Atlassian Opsgenie Settings',
                    'name': 'opsgenie_settings',
                    'required': ['enabled', 'domain',
                                 'apikey', 'verify_ssl'],
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Use Opsgenie',
                            'type': 'bool'
                        },
                        {
                            'name': 'domain',
                            'title': 'Opsgenie API domain',
                            'type': 'string'
                        },
                        {
                            'name': 'apikey',
                            'title': 'API Key',
                            'type': 'string',
                            'format': 'password'
                        },
                        {
                            'name': 'verify_ssl',
                            'title': 'Verify SSL',
                            'type': 'bool'
                        },
                        {
                            'name': 'https_proxy',
                            'title': 'HTTPS proxy',
                            'type': 'string'
                        },
                    ],
                },
                {
                    'type': 'array',
                    'title': 'Jira Settings',
                    'name': 'jira_settings',
                    'required': ['enabled', 'domain',
                                 'username', 'password', 'verify_ssl'],
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Use Jira',
                            'type': 'bool'
                        },
                        {
                            'name': 'domain',
                            'title': 'Jira domain',
                            'type': 'string'
                        },
                        {
                            'name': 'username',
                            'title': 'User name',
                            'type': 'string'
                        },
                        {
                            'name': 'password',
                            'title': 'API key',
                            'type': 'string',
                            'format': 'password'
                        },
                        {
                            'name': 'verify_ssl',
                            'title': 'Verify SSL',
                            'type': 'bool'
                        }
                    ],
                },
                {
                    'items': [
                        {
                            'name': ADAPTERS_ERRORS_MAIL_ADDRESS,
                            'title': 'Adapters errors email address',
                            'type': 'string'
                        },
                        {
                            'name': ADAPTERS_ERRORS_WEBHOOK_ADDRESS,
                            'title': 'Adapters errors webhook address',
                            'type': 'string'
                        }
                    ],
                    'name': NOTIFICATIONS_SETTINGS,
                    'title': 'Notifications Settings',
                    'type': 'array',
                    'required': []
                },
                {
                    'items': [
                        {
                            'name': CORRELATE_BY_EMAIL_PREFIX,
                            'title': 'Correlate users by email prefix',
                            'type': 'bool'
                        },
                        {
                            'name': CORRELATE_AD_DISPLAY_NAME,
                            'title': 'Correlate users by AD display name',
                            'type': 'bool'
                        },
                        {
                            'name': CORRELATE_AWS_USERNAME,
                            'title': 'Correlate users by AWS username',
                            'type': 'bool'
                        },
                        {
                            'name': CORRELATE_BY_USERNAME_DOMAIN_ONLY,
                            'title': 'Correlate users by user name and domain only',
                            'type': 'bool'
                        },
                        {
                            'name': CORRELATE_AD_SCCM,
                            'title': 'Correlate Microsoft Active Directory (AD) and '
                                     'Microsoft SCCM data based on Distinguished Names',
                            'type': 'bool'
                        },
                        {
                            'name': CSV_FULL_HOSTNAME,
                            'type': 'bool',
                            'title': 'Correlate devices by exact hostnames when no MAC and no IPs'
                        },
                        {
                            'name': CORRELATE_BY_SNOW_MAC,
                            'type': 'bool',
                            'title': 'Correlate ServiceNow adapter based on MAC address only'
                        },
                        {
                            'name': CORRELATE_BY_AZURE_AD_NAME_ONLY,
                            'type': 'bool',
                            'title': 'Correlate Microsoft Azure AD based on asset name only'
                        },
                        {
                            'name': CORRELATE_SNOW_NO_DASH,
                            'type': 'bool',
                            'title': 'Correlate ServiceNow network devices based on first name before any dash'
                        },
                        {
                            'name': CORRELATE_PUBLIC_IP_ONLY,
                            'type': 'bool',
                            'title': 'Correlate devices based on public IP only'
                        },
                        {
                            'name': ALLOW_SERVICE_NOW_BY_NAME_ONLY,
                            'type': 'bool',
                            'title': 'Correlate ServiceNow by name only'
                        },
                        {
                            'name': CORRELATE_GLOBALY_ON_HOSTNAME,
                            'type': 'bool',
                            'title': 'Correlate Globally based on Hostname only'
                        }
                    ],
                    'name': CORRELATION_SETTINGS,
                    'title': 'Correlation Settings',
                    'type': 'array',
                    'required': [CORRELATE_BY_EMAIL_PREFIX, CORRELATE_AD_DISPLAY_NAME, CORRELATE_PUBLIC_IP_ONLY,
                                 CORRELATE_AD_SCCM, CSV_FULL_HOSTNAME, CORRELATE_BY_AZURE_AD_NAME_ONLY,
                                 CORRELATE_SNOW_NO_DASH, CORRELATE_AWS_USERNAME,
                                 CORRELATE_GLOBALY_ON_HOSTNAME, ALLOW_SERVICE_NOW_BY_NAME_ONLY,
                                 CORRELATE_BY_SNOW_MAC, CORRELATE_BY_USERNAME_DOMAIN_ONLY]
                },
                {
                    'items': [
                        {
                            'name': CORRELATION_SCHEDULE_ENABLED,
                            'title': 'Enable correlation schedule',
                            'type': 'bool'
                        },
                        {
                            'name': CORRELATION_SCHEDULE_HOURS_INTERVAL,
                            'title': 'Number of hours between correlations',
                            'type': 'number'
                        }
                    ],
                    'name': CORRELATION_SCHEDULE,
                    'title': 'Correlation Schedule',
                    'type': 'array',
                    'required': [CORRELATION_SCHEDULE_HOURS_INTERVAL, CORRELATION_SCHEDULE_ENABLED]
                },
                {
                    'items': [
                        {
                            'name': FETCH_EMPTY_VENDOR_SOFTWARE_VULNERABILITES,
                            'title': 'Fetch software vulnerabilities even when the vendor name is unknown',
                            'type': 'bool'
                        },
                        {
                            'name': DEVICE_LOCATION_MAPPING,
                            'type': 'array',
                            'items': [
                                {
                                    'name': 'enabled',
                                    'title': 'Enable device location mapping',
                                    'type': 'bool'
                                },
                                {
                                    'name': CSV_IP_LOCATION_FILE,
                                    'title': 'Device location mapping CSV file',
                                    'type': 'file'
                                }
                            ],
                            'required': ['enabled', CSV_IP_LOCATION_FILE]
                        }
                    ],
                    'name': STATIC_ANALYSIS_SETTINGS,
                    'title': 'Data Enrichment Settings',
                    'type': 'array',
                    'required': [FETCH_EMPTY_VENDOR_SOFTWARE_VULNERABILITES, DEVICE_LOCATION_MAPPING]
                },
                {
                    'items': [
                        {
                            'name': MAX_WORKERS,
                            'title': 'Maximum adapters to execute asynchronously',
                            'type': 'integer',
                        },
                        {
                            'name': SOCKET_READ_TIMEOUT,
                            'title': 'Socket read-timeout in seconds',
                            'type': 'integer'
                        },
                        {
                            'name': UPPERCASE_HOSTNAMES,
                            'title': 'Convert all hostnames to uppercase',
                            'type': 'bool'
                        },
                        {
                            'name': UPDATE_CLIENTS_STATUS,
                            'title': 'Update adapters connections status periodically (every 1:30 hours)',
                            'type': 'bool'
                        }
                    ],
                    'name': AGGREGATION_SETTINGS,
                    'title': 'Aggregation Settings',
                    'type': 'array',
                    'required': [MAX_WORKERS, SOCKET_READ_TIMEOUT, UPPERCASE_HOSTNAMES, UPDATE_CLIENTS_STATUS]
                },
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Enable Getting Started with Axonius checklist',
                            'type': 'bool'
                        },
                    ],
                    'name': 'getting_started_checklist',
                    'title': 'Getting Started with Axonius Settings',
                    'type': 'array',
                    'required': ['enabled']
                },
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Enable Amazon S3 integration',
                            'type': 'bool'
                        },
                        {
                            'name': 'bucket_name',
                            'title': 'Amazon S3 bucket name',
                            'type': 'string'
                        },
                        {
                            'name': 'aws_access_key_id',
                            'title': 'AWS Access Key Id',
                            'type': 'string'
                        },
                        {
                            'name': 'aws_secret_access_key',
                            'title': 'AWS Secret Access Key',
                            'type': 'string',
                            'format': 'password'
                        },
                        {
                            'name': 'enable_backups',
                            'title': 'Enable backup to Amazon S3',
                            'type': 'bool'
                        },
                        {
                            'name': 'preshared_key',
                            'title': 'Backup encryption passphrase',
                            'type': 'string',
                            'format': 'password'
                        },
                    ],
                    'name': 'aws_s3_settings',
                    'title': 'Amazon S3 Settings',
                    'type': 'array',
                    'required': ['enabled', 'enable_backups', 'bucket_name']
                },
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Enable SMB integration',
                            'type': 'bool',
                        },
                        {
                            'name': 'enable_backups',
                            'title': 'Enable SMB data transfer',
                            'type': 'bool',
                        },
                        {
                            'name': 'ip',
                            'title': 'SMB host IP',
                            'type': 'string',
                        },
                        {
                            'name': 'port',
                            'title': 'SMB port',
                            'type': 'string',
                        },
                        {
                            'name': 'share_path',
                            'title': 'SMB share path',
                            'type': 'string',
                        },
                        {
                            'name': 'username',
                            'title': 'User name',
                            'type': 'string',
                        },
                        {
                            'name': 'password',
                            'title': 'Password',
                            'type': 'string',
                            'format': 'password',
                        },
                        {
                            'name': 'preshared_key',
                            'title': 'Data encryption passphrase',
                            'type': 'string',
                            'format': 'password',
                        },
                        {
                            'name': 'use_nbns',
                            'title': 'Use "NetBIOS over TCP" (NBT)',
                            'type': 'bool',
                            'description': ('When checked, a backwards-compatible'
                                            ' "NetBIOS over TCP/IP" (default port: 139) approach is used,'
                                            ' but requires exact NetBIOS host name field.'
                                            ' Otherwise, the newer Direct hosted "NetBIOS-less" SMB'
                                            ' (default port: 445) is used.')
                        },
                        {
                            'name': 'hostname',
                            'title': 'NetBIOS host name',
                            'type': 'string',
                            # Note: description taken from smb.SMBConnection.SMBConnection
                            'description': ('Required when "NetBIOS over TCP" is used.'
                                            ' The NetBIOS machine name of the remote server.'
                                            ' On windows, you can find out the machine name by right-clicking on'
                                            ' the "My Computer" and selecting "Properties".'
                                            ' This parameter must be the same as what has been configured'
                                            ' on the remote server, or else the connection will be rejected.')
                        },
                    ],
                    'name': 'smb_settings',
                    'title': 'SMB Settings',
                    'type': 'array',
                    'required': ['enabled',
                                 'enable_backups',
                                 'ip',
                                 'share_path',
                                 'preshared_key',
                                 'use_nbns']
                },
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Enable advanced API settings',
                            'type': 'bool'
                        },
                        {
                            'name': 'enable_destroy',
                            'title': 'Enable API destroy endpoints',
                            'type': 'bool'
                        },
                    ],
                    'name': 'api_settings',
                    'title': 'API Settings',
                    'type': 'array',
                    'required': ['enabled', 'enable_destroy'],
                },
            ],
            'pretty_name': 'Global Settings',
            'name': 'global_settings',
            'type': 'array'
        }

    @staticmethod
    def global_settings_defaults():
        return {
            'jira_settings': {
                'enabled': False,
                'domain': None,
                'username': None,
                'password': None,
                'verify_ssl': False
            },
            'opsgenie_settings': {
                'enabled': False,
                'domain': OPSGENIE_DEFAULT_DOMAIN,
                'apikey': None,
                'verify_ssl': False,
                'https_proxy': None
            },
            'email_settings': {
                'enabled': False,
                'smtpHost': None,
                'smtpPort': None,
                'smtpUser': None,
                'smtpPassword': None,
                **COMMON_SSL_CONFIG_SCHEMA_DEFAULTS,
                'sender_address': None
            },
            'syslog_settings': {
                'enabled': False,
                'syslogHost': None,
                'syslogPort': logging.handlers.SYSLOG_UDP_PORT,
                **COMMON_SSL_CONFIG_SCHEMA_DEFAULTS
            },
            'global_ssl': {
                'enabled': False,
                'hostname': None,
                **MANDATORY_SSL_CONFIG_SCHEMA_DEFAULTS,
                'passphrase': ''
            },
            'ssl_trust_settings': {
                'enabled': False,
                'ca_files': []
            },
            'csr_settings': {
                'status': False,
                'csr_file': '',
                'subject_name': '',
                'submission_date': ''
            },
            'https_log_settings': {
                'enabled': False,
                'https_log_server': None,
                'https_log_port': 443,
                'https_proxy': None
            },
            PROXY_SETTINGS: {
                'enabled': False,
                PROXY_ADDR: '',
                PROXY_PORT: 8080,
                PROXY_USER: '',
                PROXY_PASSW: '',
                PROXY_VERIFY: True
            },
            PASSWORD_SETTINGS: {
                'enabled': False,
                PASSWORD_LENGTH_SETTING: 10,
                PASSWORD_MIN_LOWERCASE: 1,
                PASSWORD_MIN_UPPERCASE: 1,
                PASSWORD_MIN_NUMBERS: 1,
                PASSWORD_MIN_SPECIAL_CHARS: 0
            },
            TUNNEL_SETTINGS: {
                TUNNEL_EMAILS_RECIPIENTS: [],
                TUNNEL_PROXY_SETTINGS: {
                    'enabled': False,
                    TUNNEL_PROXY_ADDR: '',
                    TUNNEL_PROXY_PORT: 8080,
                    TUNNEL_PROXY_USER: '',
                    TUNNEL_PROXY_PASSW: ''
                }
            },
            RESET_PASSWORD_SETTINGS: {
                RESET_PASSWORD_LINK_EXPIRATION: 48,
            },
            PASSWORD_BRUTE_FORCE_PROTECTION: {
                'enabled': False,
                PASSWORD_PROTECTION_ALLOWED_RETRIES: 20,
                PASSWORD_PROTECTION_LOCKOUT_MIN: 5,
                'conditional': PASSWORD_PROTECTION_BY_IP
            },
            VAULT_SETTINGS: {
                PASSWORD_MANGER_ENABLED: False,
                PASSWORD_MANGER_ENUM: PASSWORD_MANGER_CYBERARK_VAULT,
                PASSWORD_MANGER_CYBERARK_VAULT: {
                    CYBERARK_DOMAIN: None,
                    CYBERARK_PORT: None,
                    CYBERARK_APP_ID: None,
                    CYBERARK_CERT_KEY: None
                },
                PASSWORD_MANGER_THYCOTIC_SS_VAULT: {
                    THYCOTIC_SS_HOST: None,
                    THYCOTIC_SS_PORT: None,
                    THYCOTIC_SS_USERNAME: None,
                    THYCOTIC_SS_PASSWORD: None,
                    THYCOTIC_SS_VERIFY_SSL: False
                }
            },
            NOTIFICATIONS_SETTINGS: {
                ADAPTERS_ERRORS_MAIL_ADDRESS: None,
                ADAPTERS_ERRORS_WEBHOOK_ADDRESS: None
            },
            CORRELATION_SETTINGS: {
                CORRELATE_BY_EMAIL_PREFIX: False,
                CORRELATE_AD_DISPLAY_NAME: False,
                CORRELATE_AWS_USERNAME: True,
                CORRELATE_BY_USERNAME_DOMAIN_ONLY: False,
                CORRELATE_AD_SCCM: False,
                CSV_FULL_HOSTNAME: False,
                CORRELATE_BY_SNOW_MAC: False,
                CORRELATE_BY_AZURE_AD_NAME_ONLY: False,
                CORRELATE_SNOW_NO_DASH: False,
                CORRELATE_PUBLIC_IP_ONLY: False,
                ALLOW_SERVICE_NOW_BY_NAME_ONLY: False,
                CORRELATE_GLOBALY_ON_HOSTNAME: False
            },
            CORRELATION_SCHEDULE: {
                CORRELATION_SCHEDULE_ENABLED: False,
                CORRELATION_SCHEDULE_HOURS_INTERVAL: 8
            },
            STATIC_ANALYSIS_SETTINGS: {
                FETCH_EMPTY_VENDOR_SOFTWARE_VULNERABILITES: False,
                DEVICE_LOCATION_MAPPING: {
                    'enabled': False,
                    CSV_IP_LOCATION_FILE: None
                }
            },
            AGGREGATION_SETTINGS: {
                MAX_WORKERS: 20,
                SOCKET_READ_TIMEOUT: 5,
                UPPERCASE_HOSTNAMES: False,
                UPDATE_CLIENTS_STATUS: False
            },
            'getting_started_checklist': {
                'enabled': False,
            },
            'aws_s3_settings': {
                'enabled': False,
                'enable_backups': False,
                'bucket_name': None,
                'preshared_key': None,
                'aws_access_key_id': None,
                'aws_secret_access_key': None
            },
            'smb_settings': {
                'enabled': False,
                'enable_backups': False,
                'hostname': None,
                'ip': None,
                'port': None,
                'share_path': None,
                'username': None,
                'password': None,
                'preshared_key': None,
                'use_nbns': False,
            },
            'api_settings': {
                'enabled': False,
                'enable_destroy': False,
            },
        }

    @staticmethod
    @singlethreaded()
    @cachetools.cached(cachetools.LRUCache(maxsize=1), lock=threading.Lock())
    def get_db_encryption_key() -> bytes:
        """
        Get DB encryption key from env var
        :return: encryption key data
        """
        logger.debug('Getting DB encryption key')
        b64_key = os.environ.get(DB_KEY_ENV_VAR_NAME)
        if not b64_key:
            logger.critical(f'Error: DB encryption key was not found')
        return base64.b64decode(b64_key)

    def db_encrypt(self, data_to_encrypt):
        """
       Encrypt data using mongoclient encryption
       :param data_to_encrypt: data to encrypt
       :return: encrypted data
       """
        enc = MongoEncrypt.get_db_encryption(self._get_db_connection(), KEYS_COLLECTION, self.get_db_encryption_key())
        # encrypt data by creating a unique key for the plugin_unique_name (if not exists)
        encrypted = MongoEncrypt.db_encrypt(enc, self.plugin_unique_name, data_to_encrypt)
        return encrypted

    def db_decrypt(self, data_to_decrypt: Any) -> Any:
        """
        Decrypt data using mongo client encryption
        :param data_to_decrypt: data to decrypt
        :return: Decrypted data
        """
        enc_key = self.get_db_encryption_key()
        enc = MongoEncrypt.get_db_encryption(self._get_db_connection(), KEYS_COLLECTION, enc_key)
        decrypted = MongoEncrypt.db_decrypt(enc, data_to_decrypt)
        return decrypted

    def _encrypt_client_config(self, client_config: dict):
        """
        Encrypt plugins client_config dict values
        :param client_config: client_config to encrypt
        :return: None
        """
        if not client_config:
            return
        for key, val in client_config.items():
            if val:
                client_config[key] = self.db_encrypt(val)

    def _decrypt_client_config(self, client_config: dict):
        """
        Decrypt plugins client_config dict values
        :param client_config: client_config to decrypt
        :return: None
        """
        if not client_config:
            return
        for key, val in client_config.items():
            if val:
                client_config[key] = self.db_decrypt(val)

    @rev_cached(ttl=3600 * 6)
    def clients_labels(self) -> dict:
        """
        :return: dictionary of connection label to tuple of client_id , plugin_unique_name
        { connection_label  : [ (client_id,plugin_unique_name) ] }
        """
        clients_label = defaultdict(list)
        labels_from_db = self.adapter_client_labels_db.find({})
        for client in labels_from_db:
            client_id = client.get(CLIENT_ID)
            conn_label = client.get(CONNECTION_LABEL)
            plugin_unique_name = client.get(PLUGIN_UNIQUE_NAME)

            if client_id and conn_label:
                clients_label[conn_label].append((client_id, plugin_unique_name))
        return clients_label

    def _vault_connection_factory(self) -> AbstractVaultConnection:
        """
        initialize vault connection

        :return: AbstractVaultConnection - instance of vault connection
        """
        if self._vault_settings.get(PASSWORD_MANGER_ENUM) == PASSWORD_MANGER_THYCOTIC_SS_VAULT:
            thycotic_secret_server_vault = self._vault_settings.get(PASSWORD_MANGER_THYCOTIC_SS_VAULT)
            return ThycoticVaultConnection(host=thycotic_secret_server_vault.get(THYCOTIC_SS_HOST),
                                           port=thycotic_secret_server_vault.get(THYCOTIC_SS_PORT),
                                           username=thycotic_secret_server_vault.get(THYCOTIC_SS_USERNAME),
                                           password=thycotic_secret_server_vault.get(THYCOTIC_SS_PASSWORD),
                                           verify_ssl=thycotic_secret_server_vault.get(THYCOTIC_SS_VERIFY_SSL, False)
                                           )

        if self._vault_settings.get(PASSWORD_MANGER_ENUM) == PASSWORD_MANGER_CYBERARK_VAULT:
            cyberark_vault = self._vault_settings.get(PASSWORD_MANGER_CYBERARK_VAULT)
            return CyberArkVaultConnection(domain=cyberark_vault.get(CYBERARK_DOMAIN),
                                           port=int(cyberark_vault.get(CYBERARK_PORT)),
                                           cyberark_appid=cyberark_vault.get(CYBERARK_APP_ID),
                                           cert=self._grab_file_contents(cyberark_vault.get(CYBERARK_CERT_KEY),
                                                                         stored_locally=False))

        raise RuntimeError(f'Invalid Vault connection selection --> {PASSWORD_MANGER_ENUM}')

    def log_activity(self, category: AuditCategory, action: AuditAction, params: Dict[str, str] = None,
                     activity_type: AuditType = AuditType.Info, user_id: ObjectId = None):
        """
        Create an activity log of a predefined Category and Action

        :param category: Classifying the area of the activity
        :param action: Leading to the activity
        :param params: Specifying subjects of the activity
        :param activity_type: Indicating the source of the activity
        :param user_id: The user performing the activity - leave empty for system activity
        """
        self.log_activity_default(category.value, action.value, params, activity_type, user_id)

    def log_activity_default(self, category: str, action: str, params: Dict[str, str],
                             activity_type: AuditType, user_id: ObjectId = None):
        """
        Creates a new document in the 'activity_logs' collection, with given properties,
        along with current time for the date the activity happened.

        :param category: String representation of the category
        :param action: String representation of the action
        :param params: Specifying subject of the activity
        :param activity_type: Indicating the source of the activity
        :param user_id: The user performing the activity - leave empty for system activity
        """
        new_activity_log = dict(category=category,
                                action=action,
                                params=params,
                                timestamp=datetime.now(),
                                user=user_id,
                                type=activity_type.value)
        self._audit_collection.insert_one(new_activity_log)

    @property
    def _audit_collection(self):
        return self._get_collection(AUDIT_COLLECTION, CORE_UNIQUE_NAME)
