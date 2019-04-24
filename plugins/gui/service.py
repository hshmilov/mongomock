import configparser
import io
import json
import logging
import os
import secrets
import shutil
import tarfile
import threading
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool
from typing import Dict, Iterable, Tuple
from uuid import uuid4

import gridfs
import ldap3
import pymongo
import requests
from apscheduler.executors.pool import \
    ThreadPoolExecutor as ThreadPoolExecutorApscheduler
from apscheduler.triggers.cron import CronTrigger
from bson import ObjectId
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta
from flask import (after_this_request, has_request_context, jsonify,
                   make_response, redirect, request, send_file, session)
from passlib.hash import bcrypt
from urllib3.util.url import parse_url
import OpenSSL

from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.clients.ldap.exceptions import LdapException
from axonius.clients.ldap.ldap_connection import LdapConnection
from axonius.clients.rest.connection import RESTConnection
from axonius.consts import adapter_consts
from axonius.consts.core_consts import CORE_CONFIG_NAME
from axonius.consts.gui_consts import (ADAPTERS_DATA, ENCRYPTION_KEY_PATH,
                                       EXEC_REPORT_EMAIL_CONTENT,
                                       EXEC_REPORT_FILE_NAME,
                                       EXEC_REPORT_THREAD_ID,
                                       EXEC_REPORT_GENERATE_PDF_THREAD_ID,
                                       LOGGED_IN_MARKER_PATH,
                                       PREDEFINED_ROLE_ADMIN,
                                       PREDEFINED_ROLE_READONLY,
                                       PREDEFINED_ROLE_RESTRICTED,
                                       RANGE_UNIT_DAYS, ROLES_COLLECTION,
                                       SPECIFIC_DATA,
                                       TEMP_MAINTENANCE_THREAD_ID,
                                       USERS_COLLECTION,
                                       USERS_CONFIG_COLLECTION,
                                       ChartFuncs,
                                       ChartMetrics,
                                       ChartRangeTypes,
                                       ChartRangeUnits,
                                       ChartViews,
                                       Signup,
                                       ResearchStatus,
                                       PROXY_ERROR_MESSAGE,
                                       FeatureFlagsNames,
                                       REPORTS_DELETED,
                                       SIGNUP_TEST_CREDS,
                                       SIGNUP_TEST_COMPANY_NAME)
from axonius.consts.metric_consts import ApiMetric, Query, SystemMetric
from axonius.consts.plugin_consts import (AGGREGATOR_PLUGIN_NAME,
                                          AXONIUS_USER_NAME,
                                          CONFIGURABLE_CONFIGS_COLLECTION,
                                          CORE_UNIQUE_NAME,
                                          DASHBOARD_COLLECTION,
                                          DEVICE_CONTROL_PLUGIN_NAME, GUI_NAME,
                                          GUI_SYSTEM_CONFIG_COLLECTION,
                                          METADATA_PATH, NODE_ID, NODE_NAME,
                                          NODE_USER_PASSWORD, NOTES_DATA_TAG,
                                          PLUGIN_NAME, PLUGIN_UNIQUE_NAME,
                                          STATIC_CORRELATOR_PLUGIN_NAME,
                                          STATIC_USERS_CORRELATOR_PLUGIN_NAME,
                                          SYSTEM_SCHEDULER_PLUGIN_NAME,
                                          SYSTEM_SETTINGS,
                                          PROXY_SETTINGS)
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.consts.scheduler_consts import (Phases, ResearchPhases,
                                             SchedulerState)
from axonius.consts.report_consts import (ACTIONS_FIELD, ACTIONS_MAIN_FIELD, ACTIONS_SUCCESS_FIELD,
                                          ACTIONS_FAILURE_FIELD, ACTIONS_POST_FIELD, TRIGGERS_FIELD,
                                          LAST_TRIGGERED_FIELD, TIMES_TRIGGERED_FIELD, LAST_UPDATE_FIELD,
                                          NOT_RAN_STATE)

from axonius.devices.device_adapter import DeviceAdapter
from axonius.email_server import EmailServer
from axonius.entities import AXONIUS_ENTITY_BY_CLASS
from axonius.fields import Field
from axonius.logging.metric_helper import log_metric
from axonius.mixins.configurable import Configurable
from axonius.mixins.triggerable import Triggerable, TriggerStates, StoredJobStateCompletion, RunIdentifier
from axonius.plugin_base import EntityType, PluginBase, return_error
from axonius.thread_pool_executor import LoggedThreadPoolExecutor
from axonius.types.correlation import (MAX_LINK_AMOUNT, CorrelationReason,
                                       CorrelationResult)
from axonius.types.enforcement_classes import TriggerPeriod
from axonius.types.ssl_state import (COMMON_SSL_CONFIG_SCHEMA,
                                     COMMON_SSL_CONFIG_SCHEMA_DEFAULTS,
                                     SSLState)
from axonius.users.user_adapter import UserAdapter
from axonius.utils import gui_helpers
from axonius.utils.axonius_query_language import (convert_db_entity_to_view_entity,
                                                  parse_filter)
from axonius.utils.datetime import next_weekday, time_from_now
from axonius.utils.files import create_temp_file, get_local_config_file
from axonius.utils.gui_helpers import (Permission, PermissionLevel,
                                       PermissionType, ReadOnlyJustForGet,
                                       add_labels_to_entities,
                                       beautify_user_entry, check_permissions,
                                       deserialize_db_permissions,
                                       get_entity_labels,
                                       get_historized_filter, entity_fields)
from axonius.utils.metric import remove_ids
from axonius.utils.mongo_administration import (get_collection_capped_size,
                                                get_collection_stats)
from axonius.utils.mongo_chunked import get_chunks_length
from axonius.utils.mongo_retries import mongo_retry
from axonius.utils.mongo_escaping import escape_dict
from axonius.utils.parsing import bytes_image_to_base64
from axonius.utils.proxy_utils import to_proxy_string
from axonius.utils.revving_cache import rev_cached
from axonius.utils.threading import run_and_forget
from axonius.consts import report_consts
from gui.api import API
from gui.cached_session import CachedSessionInterface
from gui.feature_flags import FeatureFlags
from gui.gui_logic.adapter_data import adapter_data
from gui.gui_logic.ec_helpers import extract_actions_from_ec
from gui.gui_logic.fielded_plugins import get_fielded_plugins
from gui.gui_logic.filter_utils import filter_archived
from gui.gui_logic.get_ec_historical_data_for_entity import (TaskData,
                                                             get_all_task_data)
from gui.gui_logic.historical_dates import (all_historical_dates,
                                            first_historical_date)
from gui.gui_logic.views_data import get_views, get_views_count
from gui.okta_login import OidcData, try_connecting_using_okta
from gui.report_generator import ReportGenerator
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser


# pylint: disable=line-too-long,superfluous-parens,too-many-statements,too-many-lines,keyword-arg-before-vararg,invalid-name,too-many-instance-attributes,inconsistent-return-statements,no-self-use,dangerous-default-value,unidiomatic-typecheck,inconsistent-return-statements,no-else-return,no-self-use,unnecessary-pass,useless-return,cell-var-from-loop,logging-not-lazy,singleton-comparison,redefined-builtin,comparison-with-callable,too-many-return-statements,too-many-boolean-expressions,logging-format-interpolation,fixme

# TODO: the following ones are real errors, we should fix them first
# pylint: disable=invalid-sequence-index,method-hidden

logger = logging.getLogger(f'axonius.{__name__}')

SAML_SETTINGS_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config', 'saml_settings.json'))

DEVICE_ADVANCED_FILEDS = ['installed_software', 'software_cves',
                          'security_patches', 'available_security_patches', 'network_interfaces',
                          'users', 'connected_hardware', 'local_admins', 'hard_drives', 'connected_devices',
                          'plugin_and_severities', 'tenable_sources', 'registry_information', 'processes',
                          'services', 'shares', 'port_security', 'direct_connected_devices']

USER_ADVANCED_FILEDS = ['associated_devices']


def has_customer_login_happened():
    return LOGGED_IN_MARKER_PATH.is_file()


def session_connection(func, required_permissions: Iterable[Permission], enforce_trial=True):
    """
    Decorator stating that the view requires the user to be connected
    :param required_permissions: The set (or list...) of Permission required for this api call or none
    :param enforce_trial: Restrict if system has a trial expiration date configure and it has passed
    """

    def wrapper(self, *args, **kwargs):
        user = session.get('user')
        if user is None:
            return return_error('You are not connected', 401)
        permissions = user.get('permissions')
        if ((not check_permissions(permissions, required_permissions, request.method) and not user.get('admin')) or
                (enforce_trial and PluginBase.Instance.trial_expired() and user.get('user_name') != AXONIUS_USER_NAME)):
            return return_error('You are lacking some permissions for this request', 401)

        oidc_data: OidcData = session.get('oidc_data')
        if oidc_data:
            try:
                oidc_data.beautify()
            except Exception:
                # TBD: Which exception exactly are raised
                session['user'] = None
                return return_error('Your OIDC sessions has expired', 401)

        if has_request_context():
            path = request.path
            cleanpath = remove_ids(path)
            method = request.method
            if method != 'GET':
                log_metric(logger, ApiMetric.REQUEST_PATH, cleanpath, method=request.method)

        return func(self, *args, **kwargs)

    return wrapper


# Caution! These decorators must come BEFORE @add_rule
def gui_add_rule_logged_in(rule, required_permissions: Iterable[Permission] = None, enforce_trial=True,
                           *args, **kwargs):
    """
    A URL mapping for GUI endpoints that use the browser session for authentication,
    see add_rule_custom_authentication for more information.
    :param required_permissions: see session_connection for docs
    """
    required_permissions = set(required_permissions or [])

    def session_connection_permissions(*args, **kwargs):
        return session_connection(*args, **kwargs, required_permissions=required_permissions,
                                  enforce_trial=enforce_trial)

    return gui_helpers.add_rule_custom_authentication(rule, session_connection_permissions, *args, **kwargs)


def gzipped_downloadable(filename, extension):
    filename = filename.format(date.today())

    def gzipped_downloadable_wrapper(f):
        def view_func(*args, **kwargs):
            @after_this_request
            def zipper(response):
                response.direct_passthrough = False

                if (response.status_code < 200 or
                        response.status_code >= 300 or
                        'Content-Encoding' in response.headers):
                    return response
                uncompressed = io.BytesIO(response.data)
                compressed = io.BytesIO()

                tar = tarfile.open(mode='w:gz', fileobj=compressed)
                tarinfo = tarfile.TarInfo(f'{filename}.{extension}')
                tarinfo.size = len(response.data)
                tar.addfile(tarinfo, fileobj=uncompressed)
                tar.close()

                response.data = compressed.getbuffer()
                if 'Content-Disposition' not in response.headers:
                    response.headers['Content-Disposition'] = f'attachment;filename={filename}.tar.gz'
                return response

            return f(*args, **kwargs)

        return view_func

    return gzipped_downloadable_wrapper


# this is a magic that means that the value shouldn't be changed, i.e. when used by passwords
# that aren't sent to the client from the server and if they aren't modified we need to not change them
UNCHANGED_MAGIC_FOR_GUI = ['unchanged']


def clear_passwords_fields(data, schema):
    """
    Assumes "data" is organized according to schema and nullifies all password fields
    """
    if not data:
        return data
    if schema.get('format') == 'password':
        return UNCHANGED_MAGIC_FOR_GUI
    if schema['type'] == 'array':
        items = schema['items']
        if isinstance(items, list):
            for item in schema['items']:
                if item['name'] in data:
                    data[item['name']] = clear_passwords_fields(data[item['name']], item)
        elif isinstance(items, dict):
            for index, date_item in enumerate(data):
                data[index] = clear_passwords_fields(data[index], items)
        else:
            raise TypeError('Weird schema')
        return data
    return data


def refill_passwords_fields(data, data_from_db):
    """
    Uses `data_from_db` to fill out "incomplete" (i.e. "unchanged") data in `data`
    """
    if data == UNCHANGED_MAGIC_FOR_GUI:
        return data_from_db
    if data_from_db is None:
        return data
    if isinstance(data, dict):
        for key in data.keys():
            if key in data_from_db:
                data[key] = refill_passwords_fields(data[key], data_from_db[key])
        return data

    return data


def filter_by_name(names, additional_filter=None):
    """
    Returns a filter that filters in objects by names
    :param additional_filter: optional - allows another filter to be made
    """
    base_names = {'name': {'$in': names}}
    if additional_filter:
        return {'$and': [base_names, additional_filter]}
    return base_names


def _get_date_ranges(start: datetime, end: datetime) -> Iterable[Tuple[date, date]]:
    """
    Generate date intervals from the given datetimes according to the amount of threads
    """
    start = start.date()
    end = end.date()

    thread_count = min([cpu_count(), (end - start).days]) or 1
    interval = (end - start) / thread_count

    for i in range(thread_count):
        start = start + (interval * i)
        end = start + (interval * (i + 1))
        yield (start, end)


if os.environ.get('HOT', None) == 'true':
    session = None


class GuiService(Triggerable, FeatureFlags, PluginBase, Configurable, API):
    class MyDeviceAdapter(DeviceAdapter):
        pass

    class MyUserAdapter(UserAdapter):
        pass

    DEFAULT_AVATAR_PIC = '/src/assets/images/users/avatar.png'
    ALT_AVATAR_PIC = '/src/assets/images/users/alt_avatar.png'
    DEFAULT_USER = {'user_name': 'admin',
                    'password':
                        '$2b$12$SjT4qshlg.uUpsgE3vHwp.7A0UtkGEoWfUR0wFet3WZuXTnMgOCIK',
                    'first_name': 'administrator', 'last_name': '',
                    'pic_name': DEFAULT_AVATAR_PIC,
                    'permissions': {},
                    'admin': True,
                    'source': 'internal',
                    'api_key': secrets.token_urlsafe(),
                    'api_secret': secrets.token_urlsafe()
                    }

    ALTERNATIVE_USER = {'user_name': AXONIUS_USER_NAME,
                        'password':
                            '$2b$12$HQTyeTlepuCDC.5ZJ0TFo.U9ZUBARAEFU5pjhcnY.GfWaQWydcn8G',
                        'first_name': 'axonius', 'last_name': '',
                        'pic_name': ALT_AVATAR_PIC,
                        'permissions': {},
                        'admin': True,
                        'source': 'internal',
                        'api_key': secrets.token_urlsafe(),
                        'api_secret': secrets.token_urlsafe()
                        }

    def __add_defaults(self):
        self._add_default_roles()
        if self.__users_config_collection.find_one({}) is None:
            self.__users_config_collection.insert_one({
                'external_default_role': PREDEFINED_ROLE_RESTRICTED
            })

        current_user = self.__users_collection.find_one({'user_name': 'admin'})
        if current_user is None:
            # User doesn't exist, this must be the installation process
            self.__users_collection.update({'user_name': 'admin'}, self.DEFAULT_USER, upsert=True)

        alt_user = self.__users_collection.find_one({'user_name': AXONIUS_USER_NAME})
        if alt_user is None:
            self.__users_collection.update({'user_name': AXONIUS_USER_NAME}, self.ALTERNATIVE_USER, upsert=True)

        self.add_default_views(EntityType.Devices, 'default_views_devices.ini')
        self.add_default_views(EntityType.Users, 'default_views_users.ini')
        self._mark_demo_views()
        self.add_default_dashboard_charts('default_dashboard_charts.ini')
        if not self.system_collection.count_documents({'type': 'server'}):
            self.system_collection.insert_one({'type': 'server', 'server_name': 'localhost'})
        if not self.system_collection.count_documents({'type': 'maintenance'}):
            self.system_collection.insert_one({
                'type': 'maintenance', 'provision': True, 'analytics': True, 'troubleshooting': True
            })

    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__),
                         requested_unique_plugin_name=GUI_NAME, *args, **kwargs)
        self.__all_sessions = {}
        self.wsgi_app.config['SESSION_COOKIE_SECURE'] = True
        self.wsgi_app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
        self.wsgi_app.session_interface = CachedSessionInterface(self.__all_sessions)

        self.__users_collection = self._get_collection(USERS_COLLECTION)
        self.__roles_collection = self._get_collection(ROLES_COLLECTION)
        self.__users_config_collection = self._get_collection(USERS_CONFIG_COLLECTION)

        self.reports_config_collection.create_index([('name', pymongo.HASHED)])

        self.__add_defaults()

        # Start exec reports scheduler
        self.exec_report_locks = {}

        self._client_insertion_threadpool = LoggedThreadPoolExecutor(max_workers=20)  # Only for client insertion

        self._job_scheduler = LoggedBackgroundScheduler(executors={'default': ThreadPoolExecutorApscheduler(1)})
        current_exec_reports_setting = self._get_exec_report_settings(self.reports_config_collection)
        for current_exec_report_setting in current_exec_reports_setting:
            self._schedule_exec_report(current_exec_report_setting)
        self._job_scheduler.start()
        if self._maintenance_config.get('timeout'):
            next_run_time = self._maintenance_config['timeout']
            logger.info(f'Creating a job for stopping the maintenance access at {next_run_time}')
            self._job_scheduler.add_job(func=self._stop_temp_maintenance,
                                        trigger='date',
                                        next_run_time=next_run_time,
                                        name=TEMP_MAINTENANCE_THREAD_ID,
                                        id=TEMP_MAINTENANCE_THREAD_ID,
                                        max_instances=1)

        self.metadata = self.load_metadata()
        self.encryption_key = self.load_encryption_key()
        self.__aggregate_thread_pool = ThreadPool(processes=cpu_count())
        self._set_first_time_use()

        self._trigger('clear_dashboard_cache', blocking=False)

        if os.environ.get('HOT', None) == 'true':
            # pylint: disable=W0603
            global session
            user_db = self.__users_collection.find_one({'user_name': 'admin'})
            user_db['permissions'] = deserialize_db_permissions(user_db['permissions'])
            session = {'user': user_db}

    @staticmethod
    def is_proxy_allows_web(config):
        if config['enabled'] is False:
            return True

        proxies = None
        try:
            logger.info(f'checking the following proxy config {config}')
            proxy_string = to_proxy_string(config)
            if proxy_string:
                proxy_string = to_proxy_string(config)
                proxies = {'https': f'https://{proxy_string}'}

            test_request = requests.get('https://manage.chef.io', proxies=proxies, timeout=7)
            retcode = test_request.status_code
            if retcode == 200:
                logger.info('Proxy test passed')
                return True
            else:
                logger.error(f'proxy test failed with code {retcode}')
                return False
        except Exception:
            logger.exception(f'proxy test failed')
            return False

    def _mark_demo_views(self):
        """
        Search and update all relevant views - containing 'DEMO - ' in their name, i.e created for tour.
        Added the mark 'predefined' to separate from those saved by user
        :return:
        """
        for entity in EntityType:
            self.gui_dbs.entity_query_views_db_map[entity].update({
                'name': {
                    '$regex': 'DEMO - '
                }
            }, {
                '$set': {
                    'predefined': True
                }
            })

    def load_metadata(self):
        try:
            metadata_bytes = ''
            if os.path.exists(METADATA_PATH):
                with open(METADATA_PATH, 'r', encoding='UTF-8') as metadata_file:
                    metadata_bytes = metadata_file.read().strip().replace('\\', '\\\\')
                    return json.loads(metadata_bytes)
        except Exception:
            logger.exception(f'Bad __build_metadata file {metadata_bytes}')
            return ''

    def load_encryption_key(self):
        try:
            if os.path.exists(ENCRYPTION_KEY_PATH):
                with open(ENCRYPTION_KEY_PATH, 'r') as encryption_key_file:
                    encryption_key_bytes = encryption_key_file.read().strip()
                    return str(encryption_key_bytes)
        except Exception:
            logger.exception(f'Bad __encryption_key file {encryption_key_bytes}')
            return ''

    def add_default_views(self, entity_type: EntityType, default_views_ini_path):
        """
        Adds default views.
        :param entity_type: EntityType
        :param default_views_ini_path: the file path with the views
        :return:
        """
        # Load default views and save them to the DB
        try:
            config = configparser.ConfigParser()
            config.read(os.path.abspath(os.path.join(os.path.dirname(__file__), f'configs/{default_views_ini_path}')))

            # Save default views
            for name, view in config.items():
                if name == 'DEFAULT':
                    # ConfigParser always has a fake DEFAULT key, skip it
                    continue
                try:
                    self._insert_view(
                        self.gui_dbs.entity_query_views_db_map[entity_type], name, json.loads(view['view']))
                except Exception:
                    logger.exception(f'Error adding default view {name}')
        except Exception:
            logger.exception(f'Error adding default views')

    def add_default_dashboard_charts(self, default_dashboard_charts_ini_path):
        try:
            config = configparser.ConfigParser()
            config.read(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                     f'configs/{default_dashboard_charts_ini_path}')))

            for name, data in config.items():
                if name == 'DEFAULT':
                    # ConfigParser always has a fake DEFAULT key, skip it
                    continue
                try:
                    dashboard_collection = self._get_collection(DASHBOARD_COLLECTION)
                    if dashboard_collection.find_one({'name': name}):
                        logger.info(f'dashboard with {name} already exists, not adding')
                        continue

                    self._insert_dashboard_chart(dashboard_name=name,
                                                 dashboard_metric=data['metric'],
                                                 dashboard_view=data['view'],
                                                 dashboard_data=json.loads(data['config']),
                                                 hide_empty=bool(data.get('hide_empty', 0)))
                except Exception as e:
                    logger.exception(f'Error adding default dashboard chart {name}. Reason: {repr(e)}')
        except Exception as e:
            logger.exception(f'Error adding default dashboard chart. Reason: {repr(e)}')

    def _insert_view(self, views_collection, name, mongo_view):
        existed_view = views_collection.find_one({
            'name': name
        })
        if existed_view is not None and not existed_view.get('archived'):
            logger.info(f'view {name} already exists id: {existed_view["_id"]}')
            if not existed_view.get('predefined'):
                views_collection.update_one({'name': name}, {
                    '$set': {
                        'predefined': True
                    }
                })
            return existed_view['_id']

        result = views_collection.replace_one({'name': name}, {
            'name': name,
            'view': mongo_view,
            'query_type': 'saved',
            'timestamp': datetime.now(),
            'predefined': True
        }, upsert=True)
        logger.info(f'Added view {name} id: {result.upserted_id}')
        return result.upserted_id

    def _upsert_report_config(self, name, report, clear_generated_report):

        existed_report = self.reports_config_collection.find_one({'name': name})

        new_report = {**report}

        if clear_generated_report:
            new_report[report_consts.LAST_GENERATED_FIELD] = None

        result = self.reports_config_collection.replace_one({'name': name},
                                                            new_report, upsert=True)
        if existed_report is not None and not existed_report.get('archived'):
            logger.info(f'Updated report {name} id: {result.upserted_id}')
        else:
            logger.info(f'Added report {name} id: {result.upserted_id}')
        return result

    def _delete_report_configs(self, reports):
        reports_collection = self.reports_config_collection
        ids = self.get_selected_ids(reports_collection, reports, {})
        for report_id in ids:
            existed_report = reports_collection.find_one({'_id': ObjectId(report_id)})
            if existed_report is None or existed_report.get('archived'):
                logger.info(f'Report with id {report_id} does not exists')
                return
            name = existed_report['name']
            result = reports_collection.delete_one({'name': name, '_id': ObjectId(report_id)})
            exec_report_thread_id = EXEC_REPORT_THREAD_ID.format(name)
            exec_report_job = self._job_scheduler.get_job(exec_report_thread_id)
            if exec_report_job:
                self._job_scheduler.remove_job(exec_report_job.id)
            logger.info(f'Deleted report {name} id: {report_id}')
        return REPORTS_DELETED

    def _insert_dashboard_chart(self, dashboard_name, dashboard_metric, dashboard_view, dashboard_data,
                                hide_empty=False):
        dashboard_collection = self._get_collection(DASHBOARD_COLLECTION)
        existed_dashboard_chart = dashboard_collection.find_one({'name': dashboard_name})
        if existed_dashboard_chart is not None and not existed_dashboard_chart.get('archived'):
            logger.info(f'Report {dashboard_name} already exists under id: {existed_dashboard_chart["_id"]}')
            return

        result = dashboard_collection.replace_one({'name': dashboard_name},
                                                  {'name': dashboard_name,
                                                   'metric': dashboard_metric,
                                                   'view': dashboard_view,
                                                   'config': dashboard_data,
                                                   'hide_empty': hide_empty}, upsert=True)
        logger.info(f'Added report {dashboard_name} id: {result.upserted_id}')

    def _set_first_time_use(self):
        """
        Check the clients db of each registered adapter to determine if there is any connected adapter.
        We regard no connected adapters as a fresh system, that should offer user a tutorial.
        Answer is saved in a private member that is read by the frontend via a designated endpoint.

        """
        plugins_available = self.get_available_plugins_from_core()
        self.__is_system_first_use = True
        db_connection = self._get_db_connection()
        adapters_from_db = db_connection['core']['configs'].find({
            'plugin_type': {
                '$in': [
                    'Adapter', 'ScannerAdapter'
                ]
            }
        }).sort([(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
        for adapter in adapters_from_db:
            if adapter[PLUGIN_UNIQUE_NAME] in plugins_available and db_connection[adapter[PLUGIN_UNIQUE_NAME]][
                    'clients'].count_documents({}, limit=1):
                self.__is_system_first_use = False

    def _add_default_roles(self):
        if self.__roles_collection.find_one({'name': PREDEFINED_ROLE_ADMIN}) is None:
            # Admin role doesn't exists - let's create it
            self.__roles_collection.insert_one({
                'name': PREDEFINED_ROLE_ADMIN, 'predefined': True, 'permissions': {
                    p.name: PermissionLevel.ReadWrite.name for p in PermissionType
                }
            })
        if self.__roles_collection.find_one({'name': PREDEFINED_ROLE_READONLY}) is None:
            # Read-only role doesn't exists - let's create it
            self.__roles_collection.insert_one({
                'name': PREDEFINED_ROLE_READONLY, 'predefined': True, 'permissions': {
                    p.name: PermissionLevel.ReadOnly.name for p in PermissionType
                }
            })
        if self.__roles_collection.find_one({'name': PREDEFINED_ROLE_RESTRICTED}) is None:
            # Restricted role doesn't exists - let's create it. Everything restricted except the Dashboard.
            permissions = {
                p.name: PermissionLevel.Restricted.name for p in PermissionType
            }
            permissions[PermissionType.Dashboard.name] = PermissionLevel.ReadOnly.name
            self.__roles_collection.insert_one({
                'name': PREDEFINED_ROLE_RESTRICTED, 'predefined': True, 'permissions': permissions
            })

    ########
    # DATA #
    ########

    def _fetch_historical_entity(self, entity_type: EntityType, entity_id, history_date: datetime = None,
                                 projection=None):
        return convert_db_entity_to_view_entity(self._get_appropriate_view(history_date, entity_type).
                                                find_one(get_historized_filter(
                                                    {
                                                        'internal_axon_id': entity_id
                                                    },
                                                    history_date), projection=projection))

    def _user_entity_by_id(self, entity_id, history_date: datetime = None):
        return self._entity_by_id(EntityType.Users, entity_id, USER_ADVANCED_FILEDS, history_date)

    def _device_entity_by_id(self, entity_id, history_date: datetime = None):
        return self._entity_by_id(EntityType.Devices, entity_id, DEVICE_ADVANCED_FILEDS, history_date)

    def _entity_by_id(self, entity_type: EntityType, entity_id, advanced_fields=[], history_date: datetime = None):
        """
        Retrieve or delete device by the given id, from current devices DB or update it
        Currently, update works only for tags because that is the only edit operation user has
        :return:
        """
        entity = self._fetch_historical_entity(entity_type, entity_id, history_date)
        if entity is None:
            return return_error('Entity ID wasn\'t found', 404)
        for specific in entity['specific_data']:
            if not specific.get('data') or not specific['data'].get('raw'):
                continue
            new_raw = {}
            for k, v in specific['data']['raw'].items():
                if type(v) != bytes:
                    new_raw[k] = v
            specific['data']['raw'] = new_raw

        # Fix notes to have the expected format of user id
        for item in entity['generic_data']:
            if item.get('name') == 'Notes' and item.get('data'):
                item['data'] = [{**note, **{'user_id': str(note['user_id'])}} for note in item['data']]

        generic_fields = gui_helpers.entity_fields(entity_type)['generic']
        basic_generic_fields = [field['name'] for field in filter(
            lambda field: field['name'] != 'adapters' and field['name'] != 'labels' and not any(
                [category in field['name'].split('.') for category in advanced_fields]), generic_fields)]

        def _advanced_generic_data(category):
            category_schema = next(filter(lambda field: category == field['name'].split('.')[-1], generic_fields), {})
            if not category_schema:
                logger.debug(f'category_schema is empty {generic_fields}')
                return None
            category_data = gui_helpers.parse_entity_fields(entity, [category_schema['name']])
            if category_schema['name'] not in category_data:
                logger.warning(
                    f'category schema name is not in category data, {category_schema["name"]} : {category_data}')
                return None
            # Flatten items of this advanced field list, for presentation in table
            fields = [field['name'] for field in category_schema['items']]
            return gui_helpers.merge_entities_fields(category_data[category_schema['name']], fields)

        # Specific is returned as is, to show all adapter datas.
        # Generic fields are divided to basic which are all merged through all adapter datas
        # and advanced, of which the main field is merged and data is given in original structure.
        return jsonify({
            'specific': entity['specific_data'],
            'generic': {
                'basic': gui_helpers.parse_entity_fields(entity, basic_generic_fields),
                'advanced': [{
                    'name': category,
                    'data': _advanced_generic_data(category)
                } for category in advanced_fields],
                'data': entity['generic_data']
            },
            'labels': entity['labels'],
            'internal_axon_id': entity['internal_axon_id'],
            'accurate_for_datetime': entity.get('accurate_for_datetime', None),
            'tasks': TaskData.schema().dump(list(get_all_task_data(entity['internal_axon_id'])), many=True)
        })

    def _disable_entity(self, entity_type: EntityType, mongo_filter):
        entity_map = {
            EntityType.Devices: ('Devicedisabelable', 'devices/disable'),
            EntityType.Users: ('Userdisabelable', 'users/disable')
        }
        if entity_type not in entity_map:
            raise Exception('Weird entity type given')

        featurename, urlpath = entity_map[entity_type]

        entities_selection = self.get_request_data_as_object()
        if not entities_selection:
            return return_error('No entity selection provided')
        entity_disabelables_adapters, entity_ids_by_adapters = self._find_entities_by_uuid_for_adapter_with_feature(
            entities_selection, featurename, entity_type, mongo_filter)

        err = ''
        for adapter_unique_name in entity_disabelables_adapters:
            entitys_by_adapter = entity_ids_by_adapters.get(adapter_unique_name)
            if entitys_by_adapter:
                response = self.request_remote_plugin(urlpath, adapter_unique_name, method='POST',
                                                      json=entitys_by_adapter)
                if response.status_code != 200:
                    logger.error(f'Error on disabling on {adapter_unique_name}: {response.content}')
                    err += f'Error on disabling on {adapter_unique_name}: {response.content}\n'

        return return_error(err, 500) if err else ('', 200)

    def _find_entities_by_uuid_for_adapter_with_feature(self, entities_selection, feature, entity_type: EntityType,
                                                        mongo_filter):
        """
        Find all entity from adapters that have a given feature, from a given set of entities
        :return: plugin_unique_names of entity with given features, dict of plugin_unique_name -> id of adapter entity
        """
        db_connection = self._get_db_connection()
        query_op = '$in' if entities_selection['include'] else '$nin'
        entities = list(self._entity_db_map.get(entity_type).find({
            '$and': [
                {'internal_axon_id': {
                    query_op: entities_selection['ids']
                }}, mongo_filter
            ]}))
        entities_ids_by_adapters = {}
        for axonius_device in entities:
            for adapter_entity in axonius_device['adapters']:
                entities_ids_by_adapters.setdefault(adapter_entity[PLUGIN_UNIQUE_NAME], []).append(
                    adapter_entity['data']['id'])

                # all adapters that are disabelable and that theres atleast one
                entitydisabelables_adapters = [x[PLUGIN_UNIQUE_NAME]
                                               for x in
                                               db_connection['core']['configs'].find(
                                                   filter={
                                                       'supported_features': feature,
                                                       PLUGIN_UNIQUE_NAME: {
                                                           '$in': list(entities_ids_by_adapters.keys())
                                                       }
                                                   },
                                                   projection={
                                                       PLUGIN_UNIQUE_NAME: 1
                                                   })]
        return entitydisabelables_adapters, entities_ids_by_adapters

    def _enforce_entity(self, entity_type: EntityType, mongo_filter):
        """
        Trigger selected Enforcement with a static list of entities, as selected by user
        """
        post_data = request.get_json()
        response = self._trigger_remote_plugin('reports', 'run', blocking=False, data={
            'report_name': post_data['enforcement'],
            'input': {
                'entity': entity_type.name,
                'filter': escape_dict(mongo_filter),
                'selection': post_data['entities']
            }
        })
        return '', 200

    def _entity_views(self, method, entity_type: EntityType, limit, skip, mongo_filter):
        """
        Save or fetch views over the entities db
        :return:
        """
        entity_views_collection = self.gui_dbs.entity_query_views_db_map[entity_type]
        if method == 'GET':
            mongo_filter['query_type'] = mongo_filter.get('query_type', 'saved')
            return [gui_helpers.beautify_db_entry(entry)
                    for entry
                    in get_views(entity_type, limit, skip, mongo_filter)]

        if method == 'POST':
            view_data = self.get_request_data_as_object()
            if not view_data.get('name'):
                return return_error(f'Name is required in order to save a view', 400)
            if not view_data.get('view'):
                return return_error(f'View data is required in order to save one', 400)
            view_data['timestamp'] = datetime.now()
            update_result = entity_views_collection.find_one_and_replace({
                'name': view_data['name']
            }, view_data, upsert=True, return_document=pymongo.ReturnDocument.AFTER)

            return str(update_result['_id'])

        if method == 'DELETE':
            query_ids = self.get_selected_ids(entity_views_collection, self.get_request_data_as_object(), mongo_filter)
            entity_views_collection.update_many({'_id': {'$in': [ObjectId(i) for i in query_ids]}},
                                                {'$set': {'archived': True}})
            return ''

    def _entity_labels(self, db, namespace, mongo_filter):
        """
        GET Find all tags that currently belong to devices, to form a set of current tag values
        POST Add new tags to the list of given devices
        DELETE Remove old tags from the list of given devices
        :return:
        """
        if request.method == 'GET':
            return jsonify(get_entity_labels(db))

        # Now handling POST and DELETE - they determine if the label is an added or removed one
        entities_and_labels = self.get_request_data_as_object()
        if not entities_and_labels.get('entities'):
            return return_error('Cannot label entities without list of entities.', 400)
        if not entities_and_labels.get('labels'):
            return return_error('Cannot label entities without list of labels.', 400)
        try:
            select_include = entities_and_labels['entities'].get('include', True)
            select_ids = entities_and_labels['entities'].get('ids', [])
            internal_axon_ids = select_ids if select_include else [entry['internal_axon_id'] for entry in db.find({
                '$and': [
                    mongo_filter, {
                        'internal_axon_id': {
                            '$nin': select_ids
                        }
                    }
                ]
            }, projection={'internal_axon_id': 1})]
            add_labels_to_entities(
                db, namespace, internal_axon_ids, entities_and_labels['labels'], request.method == 'DELETE')
        except Exception as e:
            logger.exception(f'Tagging did not complete')
            return return_error(f'Tagging did not complete. First error: {e}', 400)

        return str(len(internal_axon_ids)), 200

    def __delete_entities_by_internal_axon_id(self, entity_type: EntityType, entities_selection, mongo_filter):
        self._entity_db_map[entity_type].delete_many({'internal_axon_id': {
            '$in': self.get_selected_entities(entity_type, entities_selection, mongo_filter)
        }})
        self._trigger('clear_dashboard_cache', blocking=False)

        return '', 200

    def _save_query_to_history(self, entity_type: EntityType, view_filter, skip, limit, sort, projection):
        """
        After a query (e.g. find all devices) has been made in the GUI we want to save it in the history
        for the user's comfort.
        :param entity_type: The type of the entity queried
        :param view_filter: the filter passed by @gui_helpers.filtered
        :param skip: the "skip" used by the user from @gui_helpers.paginated()
        :param limit: the "limit" used by the users from @gui_helpers.paginated()
        :param sort: the "sort" from @gui_helpers.sorted_endpoint()
        :param projection: the "mongo_projection" from @gui_helpers.projected()
        :return: None
        """
        if (session.get('user') or {}).get('user_name') == AXONIUS_USER_NAME:
            return

        if request.args.get('is_refresh') != '1':
            filter_obj = request.args.get('filter')
            log_metric(logger, Query.QUERY_GUI, filter_obj)
            history = request.args.get('history')
            if history:
                log_metric(logger, Query.QUERY_HISTORY, str(history))

        if view_filter and not skip:
            # getting the original filter text on purpose - we want to pass it
            view_filter = request.args.get('filter')
            mongo_sort = {'desc': -1, 'field': ''}
            if sort:
                field, desc = next(iter(sort.items()))
                mongo_sort = {'desc': int(desc), 'field': field}
            self.gui_dbs.entity_query_views_db_map[entity_type].replace_one(
                {'name': {'$exists': False}, 'view.query.filter': view_filter},
                {
                    'view': {
                        'page': 0,
                        'pageSize': limit,
                        'fields': list((projection or {}).keys()),
                        'coloumnSizes': [],
                        'query': {
                            'filter': view_filter,
                            'expressions': json.loads(request.args.get('expressions', '[]'))
                        },
                        'sort': mongo_sort
                    },
                    'query_type': 'history',
                    'timestamp': datetime.now()
                },
                upsert=True)

    def _entity_custom_data(self, entity_type: EntityType, mongo_filter):
        """
        Adds misc adapter data to the data as given in the request
        POST data:
        {
            'selection': {
                'ids': list of ids, 'include': true / false
            },
            'data': {...}
        }
        :param entity_type: the entity type to use
        """
        post_data = request.get_json()
        entities = list(self._entity_db_map[entity_type].find(filter={
            'internal_axon_id': {
                '$in': self.get_selected_entities(entity_type, post_data['selection'], mongo_filter)
            }
        }, projection={
            'internal_axon_id': True,
            f'adapters.{PLUGIN_UNIQUE_NAME}': True,
            'adapters.data.id': True
        }))

        entity_to_add = self._new_device_adapter() if entity_type == EntityType.Devices else self._new_user_adapter()
        errors = {}
        for k, v in post_data['data'].items():
            allowed_types = [str, int, bool, float]
            if type(v) not in allowed_types:
                errors[k] = f'{k} is of type {type(v)} which is not allowed'
            try:
                if not entity_to_add.set_static_field(k, v):
                    # Save the field with a canonized name and title as received
                    new_field_name = '_'.join(k.split(' ')).lower()
                    entity_to_add.declare_new_field(new_field_name, Field(type(v), k))
                    setattr(entity_to_add, new_field_name, v)
            except Exception:
                errors[k] = f'Value {v} not compatible with field {k}'

        if len(errors) > 0:
            return return_error(errors, 400)

        entity_to_add_dict = entity_to_add.to_dict()

        with ThreadPool(5) as pool:
            def tag_adapter(entity):
                try:
                    self.add_adapterdata_to_entity(entity_type,
                                                   [(x[PLUGIN_UNIQUE_NAME], x['data']['id'])
                                                    for x
                                                    in entity['adapters']],
                                                   entity_to_add_dict,
                                                   action_if_exists='update')
                except Exception as e:
                    logger.exception(e)

            pool.map(tag_adapter, entities)

        self._save_field_names_to_db(entity_type)
        self._trigger('clear_dashboard_cache', blocking=False)
        entity_fields.clean_cache()

    def __get_entity_hyperlinks(self, entity_type: EntityType) -> Dict[str, str]:
        """
        Get all hyperlinks codes from all adapters for the given entity type
        :return: dict between the plugin_name and the JS code all entities
        """
        collection = self._all_fields_db_map[entity_type]
        documents = collection.find({
            'name': 'hyperlinks'
        }, projection={
            PLUGIN_NAME: 1,
            'code': 1
        })
        return {x[PLUGIN_NAME]: x['code'] for x in documents}

    def __link_many_entities(self, entity_type: EntityType, mongo_filter):
        """
        Link many given entities
        :param entity_type: the entity type
        :param mongo_filter: The mongo filter to use
        :return: The internal_axon_id of the new entity
        """
        post_data = request.get_json()
        internal_axon_ids = self.get_selected_entities(entity_type, post_data, mongo_filter)
        if len(internal_axon_ids) > MAX_LINK_AMOUNT:
            return return_error(f'Maximal amount of entities to link at once is {MAX_LINK_AMOUNT}')
        if len(internal_axon_ids) < 2:
            return return_error('Please choose at least two entities to link')
        correlation = CorrelationResult(associated_adapters=[], data={
            'reason': 'User correlated those',
            'original_entities': internal_axon_ids,
            'user_id': session['user']['_id']
        }, reason=CorrelationReason.UserManualLink)
        return self.link_adapters(entity_type, correlation, entities_candidates_hint=list(internal_axon_ids))

    def __unlink_axonius_entities(self, entity_type: EntityType, mongo_filter):
        """
        "Shatters" an axonius entity: Creates many axonius entities from each of the adapters entities.
        :param entity_type: the entity type
        :param mongo_filter: Which entities to run on
        """
        entities_selection = self.get_request_data_as_object()
        if not entities_selection:
            return return_error('No entity selection provided')
        db = self._entity_db_map[entity_type]
        projection = {
            'adapters.data.id': 1,
            f'adapters.{PLUGIN_UNIQUE_NAME}': 1
        }
        if entities_selection['include']:
            entities = db.find({
                'internal_axon_id': {
                    '$in': entities_selection['ids']
                }
            }, projection=projection)
        else:
            entities = db.find({
                '$and': [
                    {'internal_axon_id': {
                        '$nin': entities_selection['ids']
                    }}, mongo_filter
                ]
            }, projection=projection)

        for entity in entities:
            adapters = entity['adapters']
            if len(adapters) < 2:
                continue
            for adapter in adapters[:-1]:
                # Unlink all adapters except the last
                self.unlink_adapter(entity_type, adapter[PLUGIN_UNIQUE_NAME], adapter['data']['id'])

        return ''

    ##########
    # DEVICE #
    ##########

    @gui_helpers.timed_endpoint()
    @gui_helpers.historical()
    @gui_helpers.paginated()
    @gui_helpers.filtered_entities()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_add_rule_logged_in('devices', methods=['GET', 'DELETE'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             ReadOnlyJustForGet)})
    def get_devices(self, limit, skip, mongo_filter, mongo_sort, mongo_projection, history: datetime):
        if request.method == 'DELETE':
            return self.__delete_entities_by_internal_axon_id(
                EntityType.Devices, self.get_request_data_as_object(), mongo_filter)
        self._save_query_to_history(EntityType.Devices, mongo_filter, skip, limit, mongo_sort, mongo_projection)
        return jsonify(
            gui_helpers.get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection,
                                     EntityType.Devices,
                                     default_sort=self._system_settings.get('defaultSort') or True,
                                     history_date=history))

    @gui_helpers.historical()
    @gui_helpers.filtered_entities()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_add_rule_logged_in('devices/csv', required_permissions={Permission(PermissionType.Devices,
                                                                            PermissionLevel.ReadOnly)})
    def get_devices_csv(self, mongo_filter, mongo_sort, mongo_projection, history: datetime):
        csv_string = gui_helpers.get_csv(mongo_filter, mongo_sort, mongo_projection, EntityType.Devices,
                                         default_sort=self._system_settings.get('defaultSort') or True,
                                         history=history)
        output = make_response(csv_string.getvalue().encode('utf-8'))
        timestamp = datetime.now().strftime('%d%m%Y-%H%M%S')
        output.headers['Content-Disposition'] = f'attachment; filename=axonius-data_{timestamp}.csv'
        output.headers['Content-type'] = 'text/csv'
        return output

    @gui_helpers.timed_endpoint()
    @gui_helpers.historical()
    @gui_add_rule_logged_in('devices/<device_id>', methods=['GET'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadOnly)})
    def device_by_id(self, device_id, history: datetime):
        return self._device_entity_by_id(device_id, history_date=history)

    @gui_helpers.filtered_entities()
    @gui_helpers.historical()
    @gui_add_rule_logged_in('devices/count', required_permissions={Permission(PermissionType.Devices,
                                                                              PermissionLevel.ReadOnly)})
    def get_devices_count(self, mongo_filter, history: datetime):
        quick = request.args.get('quick') == 'True'
        return str(gui_helpers.get_entities_count(mongo_filter, self._get_appropriate_view(history, EntityType.Devices),
                                                  history_date=history, quick=quick))

    @gui_add_rule_logged_in('devices/fields', required_permissions={
        Permission(PermissionType.Devices, PermissionLevel.ReadOnly)})
    def device_fields(self):
        return jsonify(gui_helpers.entity_fields(EntityType.Devices))

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_add_rule_logged_in('devices/views', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Devices, ReadOnlyJustForGet)})
    def device_views(self, limit, skip, mongo_filter):
        """
        Save or fetch views over the devices db
        :return:
        """
        return jsonify(self._entity_views(request.method, EntityType.Devices, limit, skip, mongo_filter))

    @gui_helpers.filtered()
    @gui_add_rule_logged_in('devices/views/count', required_permissions={Permission(PermissionType.Devices,
                                                                                    PermissionLevel.ReadOnly)})
    def get_devices_views_count(self, mongo_filter):
        quick = request.args.get('quick') == 'True'
        return str(get_views_count(EntityType.Devices, mongo_filter, quick=quick))

    @gui_helpers.filtered_entities()
    @gui_add_rule_logged_in('devices/labels', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Devices, ReadOnlyJustForGet)})
    def device_labels(self, mongo_filter):
        return self._entity_labels(self.devices_db, self.devices, mongo_filter)

    @gui_helpers.filtered_entities()
    @gui_add_rule_logged_in('devices/disable', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadWrite)})
    def disable_device(self, mongo_filter):
        return self._disable_entity(EntityType.Devices, mongo_filter)

    @gui_helpers.filtered_entities()
    @gui_add_rule_logged_in('devices/enforce', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadWrite)})
    def enforce_device(self, mongo_filter):
        return self._enforce_entity(EntityType.Devices, mongo_filter)

    @gui_add_rule_logged_in('devices/<device_id>/notes', methods=['PUT', 'DELETE'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadWrite)})
    def device_notes(self, device_id):
        return self._entity_notes(EntityType.Devices, device_id)

    @gui_add_rule_logged_in('devices/<device_id>/notes/<note_id>', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadWrite)})
    def device_notes_update(self, device_id, note_id):
        return self._entity_notes_update(EntityType.Devices, device_id, note_id)

    @gui_helpers.filtered_entities()
    @gui_add_rule_logged_in('devices/custom', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadWrite)})
    def devices_custom_data(self, mongo_filter):
        """
        See self._entity_custom_data
        """
        result = self._entity_custom_data(EntityType.Devices, mongo_filter)
        if result:
            return result
        return '', 200

    @gui_add_rule_logged_in('devices/hyperlinks', required_permissions={Permission(PermissionType.Devices,
                                                                                   PermissionLevel.ReadOnly)})
    def device_hyperlinks(self):
        return jsonify(self.__get_entity_hyperlinks(EntityType.Devices))

    @gui_helpers.filtered_entities()
    @gui_add_rule_logged_in('devices/manual_link', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadWrite)})
    def devices_link(self, mongo_filter):
        return self.__link_many_entities(EntityType.Devices, mongo_filter)

    @gui_helpers.filtered_entities()
    @gui_add_rule_logged_in('devices/manual_unlink', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadWrite)})
    def devices_unlink(self, mongo_filter):
        return self.__unlink_axonius_entities(EntityType.Devices, mongo_filter)

    #########
    # USER #
    #########

    @gui_helpers.timed_endpoint()
    @gui_helpers.historical()
    @gui_helpers.paginated()
    @gui_helpers.filtered_entities()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_add_rule_logged_in('users', methods=['GET', 'DELETE'], required_permissions={Permission(PermissionType.Users,
                                                                                                 ReadOnlyJustForGet)})
    def get_users(self, limit, skip, mongo_filter, mongo_sort, mongo_projection, history: datetime):
        if request.method == 'DELETE':
            return self.__delete_entities_by_internal_axon_id(
                EntityType.Users, self.get_request_data_as_object(), mongo_filter)
        self._save_query_to_history(EntityType.Users, mongo_filter, skip, limit, mongo_sort, mongo_projection)
        return jsonify(
            gui_helpers.get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection,
                                     EntityType.Users,
                                     default_sort=self._system_settings['defaultSort'],
                                     history_date=history))

    @gui_helpers.historical()
    @gui_helpers.filtered_entities()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_add_rule_logged_in('users/csv', required_permissions={Permission(PermissionType.Users,
                                                                          PermissionLevel.ReadOnly)})
    def get_users_csv(self, mongo_filter, mongo_sort, mongo_projection, history: datetime):
        # Deleting image from the CSV (we dont need this base64 blob in the csv)
        if 'specific_data.data.image' in mongo_projection:
            del mongo_projection['specific_data.data.image']
        csv_string = gui_helpers.get_csv(mongo_filter, mongo_sort, mongo_projection, EntityType.Users,
                                         default_sort=self._system_settings['defaultSort'], history=history)
        output = make_response(csv_string.getvalue().encode('utf-8'))
        timestamp = datetime.now().strftime('%d%m%Y-%H%M%S')
        output.headers['Content-Disposition'] = f'attachment; filename=axonius-data_{timestamp}.csv'
        output.headers['Content-type'] = 'text/csv'
        return output

    @gui_helpers.timed_endpoint()
    @gui_helpers.historical()
    @gui_add_rule_logged_in('users/<user_id>', methods=['GET'], required_permissions={Permission(PermissionType.Users,
                                                                                                 PermissionLevel.ReadOnly)})
    def user_by_id(self, user_id, history: datetime):
        return self._user_entity_by_id(user_id, history_date=history)

    @gui_helpers.historical()
    @gui_helpers.filtered_entities()
    @gui_add_rule_logged_in('users/count', required_permissions={Permission(PermissionType.Users,
                                                                            PermissionLevel.ReadOnly)})
    def get_users_count(self, mongo_filter, history: datetime):
        quick = request.args.get('quick') == 'True'
        return str(gui_helpers.get_entities_count(mongo_filter, self._get_appropriate_view(history, EntityType.Users),
                                                  history_date=history, quick=quick))

    @gui_add_rule_logged_in('users/fields', required_permissions={
        Permission(PermissionType.Users, PermissionLevel.ReadOnly)})
    def user_fields(self):
        return jsonify(gui_helpers.entity_fields(EntityType.Users))

    @gui_helpers.filtered_entities()
    @gui_add_rule_logged_in('users/disable', methods=['POST'], required_permissions={Permission(PermissionType.Users,
                                                                                                PermissionLevel.ReadWrite)})
    def disable_user(self, mongo_filter):
        return self._disable_entity(EntityType.Users, mongo_filter)

    @gui_helpers.filtered_entities()
    @gui_add_rule_logged_in('users/enforce', methods=['POST'], required_permissions={Permission(PermissionType.Users,
                                                                                                PermissionLevel.ReadWrite)})
    def enforce_user(self, mongo_filter):
        return self._enforce_entity(EntityType.Users, mongo_filter)

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_add_rule_logged_in('users/views', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Users, ReadOnlyJustForGet)})
    def user_views(self, limit, skip, mongo_filter):
        return jsonify(self._entity_views(request.method, EntityType.Users, limit, skip, mongo_filter))

    @gui_helpers.filtered()
    @gui_add_rule_logged_in('users/views/count', required_permissions={Permission(PermissionType.Users,
                                                                                  PermissionLevel.ReadOnly)})
    def get_users_views_count(self, mongo_filter):
        quick = request.args.get('quick') == 'True'
        return str(get_views_count(EntityType.Users, mongo_filter, quick=quick))

    @gui_helpers.filtered_entities()
    @gui_add_rule_logged_in('users/labels', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Users,
                                                             ReadOnlyJustForGet)})
    def user_labels(self, mongo_filter):
        return self._entity_labels(self.users_db, self.users, mongo_filter)

    @gui_add_rule_logged_in('users/<user_id>/notes', methods=['PUT', 'DELETE'],
                            required_permissions={Permission(PermissionType.Users, PermissionLevel.ReadWrite)})
    def user_notes(self, user_id):
        return self._entity_notes(EntityType.Users, user_id)

    @gui_add_rule_logged_in('users/<user_id>/notes/<note_id>', methods=['POST'],
                            required_permissions={Permission(PermissionType.Users,
                                                             PermissionLevel.ReadWrite)})
    def user_notes_update(self, user_id, note_id):
        return self._entity_notes_update(EntityType.Users, user_id, note_id)

    @gui_helpers.filtered_entities()
    @gui_add_rule_logged_in('users/custom', methods=['POST'],
                            required_permissions={Permission(PermissionType.Users,
                                                             PermissionLevel.ReadWrite)})
    def users_custom_data(self, mongo_filter):
        """
        See self._entity_custom_data
        """
        self._entity_custom_data(EntityType.Users, mongo_filter)
        return '', 200

    @gui_add_rule_logged_in('users/hyperlinks', required_permissions={Permission(PermissionType.Users,
                                                                                 PermissionLevel.ReadOnly)})
    def user_hyperlinks(self):
        return jsonify(self.__get_entity_hyperlinks(EntityType.Users))

    @gui_helpers.filtered_entities()
    @gui_add_rule_logged_in('users/manual_link', methods=['POST'],
                            required_permissions={Permission(PermissionType.Users, PermissionLevel.ReadWrite)})
    def users_link(self, mongo_filter):
        return self.__link_many_entities(EntityType.Users, mongo_filter)

    @gui_helpers.filtered_entities()
    @gui_add_rule_logged_in('users/manual_unlink', methods=['POST'],
                            required_permissions={Permission(PermissionType.Users,
                                                             PermissionLevel.ReadWrite)})
    def users_unlink(self, mongo_filter):
        return self.__unlink_axonius_entities(EntityType.Users, mongo_filter)

    ###########
    # ADAPTER #
    ###########

    def _get_plugin_schemas(self, db_connection, plugin_unique_name):
        """
        Get all schemas for a given plugin
        :param db: a db connection
        :param plugin_unique_name: the unique name of the plugin
        :return: dict
        """

        clients_value = db_connection[plugin_unique_name]['adapter_schema'].find_one(sort=[('adapter_version',
                                                                                            pymongo.DESCENDING)])
        if clients_value is None:
            return {}
        return {'clients': clients_value.get('schema')}

    @gui_add_rule_logged_in('adapters', required_permissions={Permission(PermissionType.Adapters,
                                                                         PermissionLevel.ReadOnly)})
    def adapters(self):
        return jsonify(self._adapters())

    @rev_cached(ttl=10, remove_from_cache_ttl=60)
    def _adapters(self):
        """
        Get all adapters from the core
        :return:
        """
        plugins_available = self.get_available_plugins_from_core()
        db_connection = self._get_db_connection()
        adapters_from_db = db_connection[CORE_UNIQUE_NAME]['configs'].find(
            {
                'plugin_type': adapter_consts.ADAPTER_PLUGIN_TYPE
            }).sort([(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
        adapters_to_return = []
        for adapter in adapters_from_db:
            adapter_name = adapter[PLUGIN_UNIQUE_NAME]
            if adapter_name not in plugins_available:
                # Plugin not registered - unwanted in UI
                continue

            schema = self._get_plugin_schemas(db_connection, adapter_name).get('clients')
            nodes_metadata_collection = db_connection['core']['nodes_metadata']
            if not schema:
                # there might be a race - in the split second that the adapter is up
                # but it still hasn't written it's schema
                continue

            clients = [gui_helpers.beautify_db_entry(client)
                       for client
                       in db_connection[adapter_name]['clients'].find()
                       .sort([('_id', pymongo.DESCENDING)])]
            for client in clients:
                client['client_config'] = clear_passwords_fields(client['client_config'], schema)
                client[NODE_ID] = adapter[NODE_ID]
            status = ''
            if len(clients):
                status = 'success' if all(client.get('status') == 'success' for client in clients) \
                    else 'warning'

            node_name = nodes_metadata_collection.find_one({
                NODE_ID: adapter[NODE_ID]
            })

            node_name = '' if node_name is None else node_name.get(NODE_NAME)

            adapters_to_return.append({'plugin_name': adapter['plugin_name'],
                                       'unique_plugin_name': adapter_name,
                                       'status': status,
                                       'supported_features': adapter['supported_features'],
                                       'schema': schema,
                                       'clients': clients,
                                       NODE_ID: adapter[NODE_ID],
                                       NODE_NAME: node_name,
                                       'config': self.__extract_configs_and_schemas(db_connection,
                                                                                    adapter_name)
                                       })
        adapters = defaultdict(list)
        for adapter in adapters_to_return:
            plugin_name = adapter.pop('plugin_name')
            adapters[plugin_name].append(adapter)

        return adapters

    @gui_add_rule_logged_in('adapter_features')
    def adapter_features(self):
        """
        Getting the features of each registered adapter, as they are saved in core's "configs" db.
        This is needed for the case that user has permissions to disable entities but is restricted from adapters.
        The user would need to know which entities can be disabled, according to the features of their adapters.

        :return: Dict between unique plugin name of the adapter and their list of features
        """
        plugins_available = self.get_available_plugins_from_core()
        db_connection = self._get_db_connection()
        adapters_from_db = db_connection['core']['configs'].find({
            'plugin_type': {
                '$in': [
                    'Adapter', 'ScannerAdapter'
                ]
            }
        }).sort([(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
        adapters_by_unique_name = {}
        for adapter in adapters_from_db:
            adapter_name = adapter[PLUGIN_UNIQUE_NAME]
            if adapter_name not in plugins_available:
                # Plugin not registered - unwanted in UI
                continue
            adapters_by_unique_name[adapter_name] = adapter['supported_features']
        return jsonify(adapters_by_unique_name)

    def _test_client_connectivity(self, adapter_unique_name, data_from_db_for_unchanged=None):
        client_to_test = request.get_json(silent=True)
        if client_to_test is None:
            return return_error('Invalid client', 400)
        if data_from_db_for_unchanged:
            client_to_test = refill_passwords_fields(client_to_test, data_from_db_for_unchanged['client_config'])
        # adding client to specific adapter
        response = self.request_remote_plugin('client_test', adapter_unique_name, method='post', json=client_to_test)
        return response.text, response.status_code

    def _query_client_for_devices(self, adapter_unique_name, clients, data_from_db_for_unchanged=None):
        if clients is None:
            return return_error('Invalid client', 400)
        if data_from_db_for_unchanged:
            clients = refill_passwords_fields(clients, data_from_db_for_unchanged['client_config'])
        # adding client to specific adapter
        response = self.request_remote_plugin('clients', adapter_unique_name, method='put',
                                              json=clients)
        self._adapters.clean_cache()
        if response.status_code == 200:
            self._client_insertion_threadpool.submit(self._fetch_after_clients_thread, adapter_unique_name,
                                                     response.json()['client_id'], clients)
        return response.text, response.status_code

    def _fetch_after_clients_thread(self, adapter_unique_name, client_id, client_to_add):
        # if there's no aggregator, that's fine
        try:
            logger.info(f'Requesting {adapter_unique_name} to fetch data from newly added client {client_id}')

            def inserted_to_db(*_):
                logger.info(f'{adapter_unique_name} finished fetching data for {client_id}')
                self._trigger('clear_dashboard_cache', blocking=False)
                self._trigger_remote_plugin(STATIC_CORRELATOR_PLUGIN_NAME)
                self._trigger_remote_plugin(STATIC_USERS_CORRELATOR_PLUGIN_NAME)
                self._trigger('clear_dashboard_cache', blocking=False)

            def rejected(err):
                logger.exception(f'Failed fetching from {adapter_unique_name} for {client_to_add}', exc_info=err)

            self._async_trigger_remote_plugin(adapter_unique_name,
                                              'insert_to_db',
                                              data={
                                                  'client_name': client_id
                                              }).then(did_fulfill=inserted_to_db,
                                                      did_reject=rejected)

        except Exception:
            # if there's no aggregator, there's nothing we can do
            logger.exception(f'Error fetching devices from {adapter_unique_name} for client {client_to_add}')
            pass
        return

    @gui_add_rule_logged_in('adapters/<adapter_name>/<node_id>/upload_file', methods=['POST'],
                            required_permissions={Permission(PermissionType.Adapters,
                                                             PermissionLevel.ReadWrite)})
    def adapter_upload_file(self, adapter_name, node_id):
        adapter_unique_name = self.request_remote_plugin(
            f'find_plugin_unique_name/nodes/{node_id}/plugins/{adapter_name}').json().get('plugin_unique_name')

        return self._upload_file(adapter_unique_name)

    def _upload_file(self, plugin_unique_name):
        field_name = request.form.get('field_name')
        if not field_name:
            return return_error('Field name must be specified', 401)
        file = request.files.get('userfile')
        if not file or file.filename == '':
            return return_error('File must exist', 401)
        filename = file.filename
        db_connection = self._get_db_connection()
        fs = gridfs.GridFS(db_connection[plugin_unique_name])
        written_file = fs.put(file, filename=filename)
        return jsonify({'uuid': str(written_file)})

    @gui_add_rule_logged_in('adapters/<adapter_name>/clients', methods=['PUT', 'POST'],
                            required_permissions={Permission(PermissionType.Adapters,
                                                             PermissionLevel.ReadWrite)})
    def adapters_clients(self, adapter_name):
        return self._adapters_clients(adapter_name)

    def _adapters_clients(self, adapter_name):
        """
        Gets or creates clients in the adapter
        :param adapter_unique_name: the adapter to refer to
        :return:
        """
        clients = request.get_json(silent=True)
        node_id = clients.pop('instanceName', self.node_id)

        adapter_unique_name = self.request_remote_plugin(
            f'find_plugin_unique_name/nodes/{node_id}/plugins/{adapter_name}').json().get('plugin_unique_name')
        if request.method == 'PUT':
            def reset_cache_soon():
                time.sleep(5)
                entity_fields.clean_cache()
            if self.__is_system_first_use:
                run_and_forget(reset_cache_soon())

            self.__is_system_first_use = False
            return self._query_client_for_devices(adapter_unique_name, clients)
        else:
            return self._test_client_connectivity(adapter_unique_name)

    @gui_add_rule_logged_in('adapters/<adapter_name>/clients/<client_id>',
                            methods=['PUT', 'DELETE'], required_permissions={Permission(PermissionType.Adapters,
                                                                                        PermissionLevel.ReadWrite)})
    def adapters_clients_update(self, adapter_name, client_id=None):
        return self._adapters_clients_update(adapter_name, client_id)

    def _adapters_clients_update(self, adapter_name, client_id=None):
        """
        Create or delete credential sets (clients) in the adapter
        :param adapter_unique_name: the adapter to refer to
        :param client_id: UUID of client to delete if DELETE is used
        :return:
        """
        data = self.get_request_data_as_object()
        node_id = data.pop('instanceName', self.node_id)
        old_node_id = data.pop('oldInstanceName', None)
        adapter_unique_name = self.request_remote_plugin(f'find_plugin_unique_name/nodes/{old_node_id or node_id}/'
                                                         f'plugins/{adapter_name}').json().get('plugin_unique_name')
        if request.method == 'DELETE':
            delete_entities = request.args.get('deleteEntities', False)
            self.delete_client_data(adapter_unique_name, client_id,
                                    data.get('nodeId', None), delete_entities)

        client_from_db = self._get_collection('clients', adapter_unique_name).find_one({'_id': ObjectId(client_id)})
        if not client_from_db:
            return return_error('Server is already gone, please try again after refreshing the page')

        self.request_remote_plugin('clients/' + client_id, adapter_unique_name, method='delete')

        if request.method == 'PUT':
            if old_node_id != node_id:
                url = f'find_plugin_unique_name/nodes/{node_id}/plugins/{adapter_name}'
                adapter_unique_name = self.request_remote_plugin(url).json().get('plugin_unique_name')

            self._adapters.clean_cache()
            return self._query_client_for_devices(adapter_unique_name, data,
                                                  data_from_db_for_unchanged=client_from_db)

        self._adapters.clean_cache()
        return '', 200

    def delete_client_data(self, plugin_name, client_id, node_id, delete_entities=False):
        adapter_name = self.get_plugin_by_name(plugin_name, node_id)[
            PLUGIN_UNIQUE_NAME] if node_id is not None else plugin_name
        plugin_name = plugin_name if node_id is not None else self.get_plugin_by_name(plugin_name, node_id)[PLUGIN_NAME]
        logger.info(f'Delete request for {plugin_name} [{adapter_name}]'
                    f' and delete entities - {delete_entities}, client_id: {client_id}')
        if delete_entities:
            client_from_db = self._get_collection('clients', adapter_name). \
                find_one({'_id': ObjectId(client_id)})
            if client_from_db:
                # this is the "client_id" - i.e. AD server or AWS Access Key
                local_client_id = client_from_db['client_id']
                logger.info(f'client from db: {client_from_db}')
                for entity_type in EntityType:
                    res = self._entity_db_map[entity_type].update_many(
                        {
                            'adapters': {
                                '$elemMatch': {
                                    '$and': [
                                        {
                                            PLUGIN_NAME: plugin_name
                                        },
                                        {
                                            # and the device must be from this adapter
                                            'client_used': local_client_id
                                        }
                                    ]
                                }
                            }
                        },
                        {
                            '$set': {
                                'adapters.$[i].pending_delete': True
                            }
                        },
                        array_filters=[
                            {
                                '$and': [
                                    {f'i.{PLUGIN_NAME}': plugin_name},
                                    {'i.client_used': local_client_id}
                                ]
                            }
                        ]
                    )

                    logger.info(f'Set pending_delete on {res.modified_count} axonius entities '
                                f'(or some adapters in them) ' +
                                f'from {res.matched_count} matches')

                    entities_to_pass_to_be_deleted = list(self._entity_db_map[entity_type].find(
                        {
                            'adapters': {
                                '$elemMatch': {
                                    '$and': [
                                        {
                                            PLUGIN_NAME: plugin_name
                                        },
                                        {
                                            # and the device must be from this adapter
                                            'client_used': local_client_id
                                        }
                                    ]
                                }
                            }
                        },
                        projection={
                            'adapters.client_used': True,
                            'adapters.data.id': True,
                            f'adapters.{PLUGIN_UNIQUE_NAME}': True,
                            f'adapters.{PLUGIN_NAME}': True,
                        }))

                    def async_delete_entities(entity_type, entities_to_delete):
                        with ThreadPool(5) as pool:
                            def delete_adapters(entity):
                                try:
                                    for adapter in entity['adapters']:
                                        if adapter.get('client_used') == local_client_id and \
                                                adapter[PLUGIN_NAME] == plugin_name:
                                            logger.debug('deleting ' + adapter['data']['id'])
                                            self.delete_adapter_entity(entity_type, adapter[PLUGIN_UNIQUE_NAME],
                                                                       adapter['data']['id'])
                                except Exception as e:
                                    logger.exception(e)

                            pool.map(delete_adapters, entities_to_delete)
                            self._trigger('clear_dashboard_cache', blocking=False)

                    # while we can quickly mark all adapters to be pending_delete
                    # we still want to run a background task to delete them
                    tmp_entity_type = entity_type
                    run_and_forget(lambda: async_delete_entities(tmp_entity_type, entities_to_pass_to_be_deleted))

            self._trigger('clear_dashboard_cache', blocking=False)
            return client_from_db

    def run_actions(self, action_data, mongo_filter):
        # The format of data is defined in device_control\service.py::run_shell
        action_type = action_data['action_type']
        entities_selection = action_data['entities']
        action_data['internal_axon_ids'] = entities_selection['ids'] if entities_selection['include'] else [
            entry['internal_axon_id'] for entry in self.devices_db.find({
                '$and': [
                    mongo_filter, {
                        'internal_axon_id': {
                            '$nin': entities_selection['ids']
                        }
                    }
                ]
            }, projection={'internal_axon_id': 1})]
        del action_data['entities']

        try:
            if 'action_name' not in action_data or ('command' not in action_data and 'binary' not in action_data):
                return return_error('Some data is missing')

            self._trigger_remote_plugin(DEVICE_CONTROL_PLUGIN_NAME, priority=True, blocking=False,
                                        data=action_data)
            return '', 200
        except Exception as e:
            return return_error(f'Attempt to run action {action_type} caused exception. Reason: {repr(e)}', 400)

    @gui_helpers.filtered()
    @gui_add_rule_logged_in('actions/<action_type>', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadWrite)})
    def actions_run(self, action_type, mongo_filter):
        action_data = self.get_request_data_as_object()
        action_data['action_type'] = action_type
        return self.run_actions(action_data, mongo_filter)

    @gui_add_rule_logged_in('actions/upload_file', methods=['POST'],
                            required_permissions={Permission(PermissionType.Adapters,
                                                             PermissionLevel.ReadWrite)})
    def actions_upload_file(self):
        return self._upload_file(DEVICE_CONTROL_PLUGIN_NAME)

    # REPORTS
    def get_reports(self, limit, mongo_filter, mongo_sort, skip):
        sort = []
        for field, direction in mongo_sort.items():
            if field in [ACTIONS_MAIN_FIELD, ACTIONS_SUCCESS_FIELD, ACTIONS_FAILURE_FIELD, ACTIONS_POST_FIELD]:
                field = f'actions.{field}'
            sort.append((field, direction))
        if not sort:
            sort.append((LAST_UPDATE_FIELD, pymongo.DESCENDING))

        def beautify_report(report):
            beautify_object = {
                '_id': report['_id'],
                'name': report['name'],
                'last_updated': report.get('last_updated'),
                report_consts.LAST_GENERATED_FIELD: report.get(report_consts.LAST_GENERATED_FIELD)
            }
            if report.get('add_scheduling'):
                beautify_object['period'] = report.get('period').capitalize()
                if report.get('mail_properties'):
                    beautify_object['mailSubject'] = report.get('mail_properties').get('mailSubject')
            return gui_helpers.beautify_db_entry(beautify_object)
        reports_collection = self.reports_config_collection
        result = [beautify_report(enforcement) for enforcement in reports_collection.find(
            mongo_filter).sort(sort).skip(skip).limit(limit)]
        return result

    def _generate_and_schedule_report(self, report):
        generateReportThreadPool = LoggedThreadPoolExecutor(max_workers=1)
        generateReportThreadPool.submit(self._generate_and_save_report, report)
        if report.get('period'):
            self._schedule_exec_report(report)

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_add_rule_logged_in('reports', methods=['GET', 'PUT', 'DELETE'],
                            required_permissions={Permission(PermissionType.Reports,
                                                             ReadOnlyJustForGet)})
    def reports(self, limit, skip, mongo_filter, mongo_sort):
        """
        GET results in list of all currently configured enforcements, with their query id they were created with
        PUT Send report_service a new enforcement to be configured

        :return:
        """
        if request.method == 'GET':
            return jsonify(self.get_reports(limit, mongo_filter, mongo_sort, skip))

        if request.method == 'PUT':
            report_to_add = request.get_json()
            reports_collection = self.reports_config_collection
            report_name = report_to_add['name']
            report = reports_collection.find_one({
                'name': report_name
            })
            if report:
                return f'Report with "{report_name}" name already exists', 400

            report_to_add['last_updated'] = datetime.now()
            upsert_result = self._upsert_report_config(report_to_add['name'], report_to_add, False)
            self._generate_and_schedule_report(report_to_add)
            report_to_add['uuid'] = str(upsert_result.upserted_id)
            return jsonify(report_to_add), 201

        # Handle remaining method - DELETE
        return self._delete_report_configs(self.get_request_data_as_object()), 200

    @gui_helpers.filtered()
    @gui_add_rule_logged_in('reports/count', required_permissions={Permission(PermissionType.Enforcements,
                                                                              PermissionLevel.ReadOnly)})
    def reports_count(self, mongo_filter):
        reports_collection = self.reports_config_collection
        return jsonify(reports_collection.count_documents(mongo_filter))

    @gui_add_rule_logged_in('reports/<report_id>', methods=['GET', 'POST'],
                            required_permissions={Permission(PermissionType.Reports,
                                                             ReadOnlyJustForGet)})
    def report_by_id(self, report_id):
        """
        :param report_id:
        :return:
        """
        reports_collection = self.reports_config_collection
        if request.method == 'GET':
            report = reports_collection.find_one({
                '_id': ObjectId(report_id)
            })
            if not report:
                return return_error(f'Report with id {report_id} was not found', 400)

            return jsonify(gui_helpers.beautify_db_entry(report))

        # Handle remaining request - POST
        report_to_update = request.get_json(silent=True)
        report_to_update['last_updated'] = datetime.now()

        response = self._upsert_report_config(report_to_update['name'], report_to_update, True)
        self._generate_and_schedule_report(report_to_update)

        if response is None:
            return return_error('No response whether report was updated')

        return jsonify(report_to_update), 200

    ################
    # ENFORCEMENTS #
    ################

    def get_enforcements(self, limit, mongo_filter, mongo_sort, skip):
        sort = [(LAST_UPDATE_FIELD, pymongo.DESCENDING)] if not mongo_sort else list(mongo_sort.items())

        def beautify_enforcement(enforcement):
            actions = enforcement[ACTIONS_FIELD]
            trigger = enforcement[TRIGGERS_FIELD][0] if enforcement[TRIGGERS_FIELD] else None
            return gui_helpers.beautify_db_entry({
                '_id': enforcement['_id'], 'name': enforcement['name'],
                f'{ACTIONS_FIELD}.{ACTIONS_MAIN_FIELD}': actions[ACTIONS_MAIN_FIELD],
                f'{TRIGGERS_FIELD}.view.name': trigger['view']['name'] if trigger else '',
                f'{TRIGGERS_FIELD}.{LAST_TRIGGERED_FIELD}': trigger[LAST_TRIGGERED_FIELD] if trigger else '',
                f'{TRIGGERS_FIELD}.{TIMES_TRIGGERED_FIELD}': trigger[TIMES_TRIGGERED_FIELD] if trigger else '',
                LAST_UPDATE_FIELD: enforcement[LAST_UPDATE_FIELD]
            })

        return [beautify_enforcement(enforcement) for enforcement in self.enforcements_collection.find(
            mongo_filter).sort(sort).skip(skip).limit(limit)]

    def __process_enforcement_actions(self, actions):
        # This is a transitional method, i.e. it's here to maximize compatibility with previous versions
        @mongo_retry()
        def create_saved_action(action) -> str:
            """
            Create a saved action from the given action and returns its name
            """
            if not action or not action.get('name'):
                return ''
            with self.enforcements_saved_actions_collection.start_session() as transaction:
                if 'uuid' in action:
                    del action['uuid']
                    del action['date_fetched']
                transaction.insert_one(action)
                return action['name']

        actions[ACTIONS_MAIN_FIELD] = create_saved_action(actions[ACTIONS_MAIN_FIELD])
        actions[ACTIONS_SUCCESS_FIELD] = [create_saved_action(x) for x in actions.get(ACTIONS_SUCCESS_FIELD) or []]
        actions[ACTIONS_FAILURE_FIELD] = [create_saved_action(x) for x in actions.get(ACTIONS_FAILURE_FIELD) or []]
        actions[ACTIONS_POST_FIELD] = [create_saved_action(x) for x in actions.get(ACTIONS_POST_FIELD) or []]

    def put_enforcement(self, enforcement_to_add):
        self.__process_enforcement_actions(enforcement_to_add[ACTIONS_FIELD])

        if enforcement_to_add[TRIGGERS_FIELD] and not enforcement_to_add[TRIGGERS_FIELD][0].get('name'):
            enforcement_to_add[TRIGGERS_FIELD][0]['name'] = enforcement_to_add['name']
        response = self.request_remote_plugin('reports', 'reports', method='put', json=enforcement_to_add)
        return response.text, response.status_code

    def delete_enforcement(self, enforcement_selection):
        # Since other method types cause the function to return - here we have DELETE request
        if enforcement_selection is None or (not enforcement_selection.get('ids')
                                             and enforcement_selection.get('include')):
            logger.error('No enforcement provided to be deleted')
            return ''

        response = self.request_remote_plugin('reports', 'reports', method='DELETE',
                                              json=enforcement_selection['ids'] if enforcement_selection['include']
                                              else [str(report['_id'])
                                                    for report in self.enforcements_collection.find({
                                                        '_id': {
                                                            '$nin': [ObjectId(x) for x in enforcement_selection['ids']]
                                                        }
                                                    }, projection={'_id': 1})])
        if response is None:
            return return_error('No response whether enforcement was removed')
        return response.text, response.status_code

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_add_rule_logged_in('enforcements', methods=['GET', 'PUT', 'DELETE'],
                            required_permissions={Permission(PermissionType.Enforcements,
                                                             ReadOnlyJustForGet)})
    def enforcements(self, limit, skip, mongo_filter, mongo_sort):
        """
        GET results in list of all currently configured enforcements, with their query id they were created with
        PUT Send report_service a new enforcement to be configured

        :return:
        """
        if request.method == 'GET':
            return jsonify(self.get_enforcements(limit, mongo_filter, mongo_sort, skip))

        if request.method == 'PUT':
            enforcement_to_add = request.get_json(silent=True)
            return self.put_enforcement(enforcement_to_add)

        # Handle remaining method - DELETE
        return self.delete_enforcement(self.get_request_data_as_object())

    @gui_helpers.filtered()
    @gui_add_rule_logged_in('enforcements/count', required_permissions={Permission(PermissionType.Enforcements,
                                                                                   PermissionLevel.ReadOnly)})
    def enforcements_count(self, mongo_filter):
        return jsonify(self.enforcements_collection.count_documents(mongo_filter))

    @gui_add_rule_logged_in('enforcements/saved', required_permissions={Permission(PermissionType.Enforcements,
                                                                                   PermissionLevel.ReadOnly)})
    def saved_enforcements(self):
        """
        Returns a list of all existing Saved Enforcement names, in order to check duplicates
        """
        return jsonify([x['name'] for x in self.enforcements_collection.find({}, {
            'name': 1
        })])

    @gui_add_rule_logged_in('enforcements/<enforcement_id>', methods=['GET', 'POST'],
                            required_permissions={Permission(PermissionType.Enforcements,
                                                             ReadOnlyJustForGet)})
    def enforcement_by_id(self, enforcement_id):
        if request.method == 'GET':
            def get_saved_action(name):
                if not name:
                    return {}
                saved_action = self.enforcements_saved_actions_collection.find_one({
                    'name': name
                })
                if not saved_action:
                    return {}

                # fixing password to be 'unchanged'
                action_type = saved_action['action']['action_name']
                schema = self._get_actions_from_reports_plugin()[action_type]['schema']
                saved_action['action']['config'] = clear_passwords_fields(saved_action['action']['config'], schema)
                return gui_helpers.beautify_db_entry(saved_action)

            enforcement = self.enforcements_collection.find_one({
                '_id': ObjectId(enforcement_id)
            })
            if not enforcement:
                return return_error(f'Enforcement with id {enforcement_id} was not found', 400)

            actions = enforcement[ACTIONS_FIELD]
            actions[ACTIONS_MAIN_FIELD] = get_saved_action(actions[ACTIONS_MAIN_FIELD])
            actions[ACTIONS_SUCCESS_FIELD] = [get_saved_action(x) for x in actions.get(ACTIONS_SUCCESS_FIELD) or []]
            actions[ACTIONS_FAILURE_FIELD] = [get_saved_action(x) for x in actions.get(ACTIONS_FAILURE_FIELD) or []]
            actions[ACTIONS_POST_FIELD] = [get_saved_action(x) for x in actions.get(ACTIONS_POST_FIELD) or []]

            for trigger in enforcement[TRIGGERS_FIELD]:
                trigger['id'] = trigger['name']
            return jsonify(gui_helpers.beautify_db_entry(enforcement))

        # Handle remaining request - POST
        enforcement_to_update = request.get_json(silent=True)
        enforcement_actions_from_user = {
            x['name']: x
            for x
            in extract_actions_from_ec(enforcement_to_update['actions'])
        }

        # Remove old enforcement's actions
        enforcement_actions = self.enforcements_collection.find_one({
            '_id': ObjectId(enforcement_id)
        }, {
            'actions': 1
        })['actions']

        all_actions_from_db = extract_actions_from_ec(enforcement_actions)

        all_actions_query = {
            'name': {
                '$in': all_actions_from_db
            }
        }

        for action_from_db in self.enforcements_saved_actions_collection.find(all_actions_query,
                                                                              projection={
                                                                                  'name': 1,
                                                                                  'action.config': 1,
                                                                                  '_id': 0
                                                                              }):
            corresponding_user_action = enforcement_actions_from_user.get(action_from_db['name'])
            logger.debug(action_from_db)
            logger.debug(corresponding_user_action)
            if not corresponding_user_action:
                continue
            corresponding_user_action['action']['config'] = refill_passwords_fields(
                corresponding_user_action['action']['config'],
                action_from_db['action']['config'])

        self.enforcements_saved_actions_collection.delete_many(all_actions_query)

        self.__process_enforcement_actions(enforcement_to_update[ACTIONS_FIELD])
        response = self.request_remote_plugin(f'reports/{enforcement_id}', 'reports', method='post',
                                              json=enforcement_to_update)
        if response is None:
            return return_error('No response whether enforcement was updated')

        for trigger in enforcement_to_update['triggers']:
            trigger_res = self.request_remote_plugin(f'reports/{enforcement_id}/{trigger.get("id", trigger["name"])}',
                                                     'reports', method='post', json=trigger)
            if trigger_res is None or trigger_res.status_code == 500:
                logger.error(f'Failed to save trigger {trigger["name"]}')

        return response.text, response.status_code

    @gui_add_rule_logged_in('enforcements/<enforcement_id>/trigger', methods=['POST'],
                            required_permissions={Permission(PermissionType.Enforcements, PermissionLevel.ReadWrite)})
    def trigger_enforcement_by_id(self, enforcement_id):
        """
        Triggers a job for the requested enforcement with its first trigger
        """

        enforcement = self.enforcements_collection.find_one({
            '_id': ObjectId(enforcement_id)
        }, {
            'name': 1,
            TRIGGERS_FIELD: 1
        })
        response = self._trigger_remote_plugin('reports', 'run', data={
            'report_name': enforcement['name'],
            'configuration_name': enforcement[TRIGGERS_FIELD][0]['name'],
            'manual': True
        })
        return response.text, response.status_code

    @rev_cached(ttl=3600)
    def _get_actions_from_reports_plugin(self) -> dict:
        response = self.request_remote_plugin('reports/actions', 'reports', method='get')
        response.raise_for_status()
        return response.json()

    @gui_add_rule_logged_in('enforcements/actions', required_permissions={Permission(PermissionType.Enforcements,
                                                                                     PermissionLevel.ReadOnly)})
    def actions(self):
        """
        Returns all action names and their schema, as defined by the author of the class
        """
        response = self._get_actions_from_reports_plugin()

        return jsonify(response)

    @gui_add_rule_logged_in('enforcements/actions/saved', required_permissions={Permission(PermissionType.Enforcements,
                                                                                           PermissionLevel.ReadOnly)})
    def saved_actions(self):
        """
        Returns a list of all existing Saved Action names, in order to check duplicates
        """
        return jsonify([x['name'] for x in self.enforcements_saved_actions_collection.find({}, {
            'name': 1
        })])

    @staticmethod
    def __tasks_query(mongo_filter):
        """
        General query for all Complete / In progress task that also answer given mongo_filter
        """
        return {
            '$and': [{
                'job_name': 'run',
                '$or': [
                    {
                        'job_completed_state': StoredJobStateCompletion.Successful.name,
                        'result': {
                            '$ne': NOT_RAN_STATE
                        }
                    }, {
                        'job_completed_state': StoredJobStateCompletion.Running.name
                    }
                ]
            }, mongo_filter]
        }

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_add_rule_logged_in('tasks', required_permissions={Permission(PermissionType.Enforcements,
                                                                      PermissionLevel.ReadOnly)})
    def enforcement_tasks(self, limit, skip, mongo_filter, mongo_sort):

        def beautify_task(task):
            """
            Extract needed fields to build task as represented in the Frontend
            """
            success_rate = '0 / 0'
            status = 'In Progress'
            if task['job_completed_state'] == StoredJobStateCompletion.Successful.name:
                main_results = task['result'][ACTIONS_MAIN_FIELD]['action']['results']

                main_successful_count = get_chunks_length(self.enforcement_tasks_action_results_id_lists,
                                                          main_results['successful_entities'])

                main_unsuccessful_count = get_chunks_length(self.enforcement_tasks_action_results_id_lists,
                                                            main_results['unsuccessful_entities'])
                success_rate = f'{main_successful_count} / {main_successful_count + main_unsuccessful_count}'
                status = 'Completed'

            return gui_helpers.beautify_db_entry({
                '_id': task['_id'],
                'result.metadata.success_rate': success_rate,
                'post_json.report_name': task['post_json']['report_name'],
                'status': status,
                f'result.{ACTIONS_MAIN_FIELD}.name': task['result']['main']['name'],
                'result.metadata.trigger.view.name': task['result']['metadata']['trigger']['view']['name'],
                'started_at': task['started_at'] or '',
                'finished_at': task['finished_at'] or ''
            })

        if mongo_sort.get('status'):
            mongo_sort['job_completed_state'] = -1 * mongo_sort['status']
            del mongo_sort['status']
        sort = [('finished_at', pymongo.DESCENDING)] if not mongo_sort else list(mongo_sort.items())
        return jsonify([beautify_task(x) for x in self.enforcement_tasks_runs_collection.find(
            self.__tasks_query(mongo_filter)).sort(sort).skip(skip).limit(limit)])

    @gui_helpers.filtered()
    @gui_add_rule_logged_in('tasks/count', required_permissions={Permission(PermissionType.Enforcements,
                                                                            PermissionLevel.ReadOnly)})
    def enforcement_tasks_count(self, mongo_filter):
        """
        Counts how many 'run' tasks are documented in the trigger history of reports plugin
        """
        return jsonify(self.enforcement_tasks_runs_collection.count_documents(self.__tasks_query(mongo_filter)))

    @gui_add_rule_logged_in('tasks/<task_id>', required_permissions={Permission(PermissionType.Enforcements,
                                                                                PermissionLevel.ReadOnly)})
    def enforcement_task_by_id(self, task_id):
        """
        Fetch an entire 'run' record with all its results, according to given task_id
        """

        def beautify_task(task):
            """
            Find the configuration that triggered this task and merge its details with task details
            """

            def normalize_saved_action_results(saved_action_results):
                if not saved_action_results:
                    return

                saved_action_results['successful_entities'] = {
                    'length': get_chunks_length(self.enforcement_tasks_action_results_id_lists,
                                                saved_action_results['successful_entities']),
                    '_id': saved_action_results['successful_entities']
                }
                saved_action_results['unsuccessful_entities'] = {
                    'length': get_chunks_length(self.enforcement_tasks_action_results_id_lists,
                                                saved_action_results['unsuccessful_entities']),
                    '_id': saved_action_results['unsuccessful_entities']
                }

            def clear_saved_action_passwords(action):
                response = self.request_remote_plugin('reports/actions', 'reports', method='get')
                if not response:
                    return
                clear_passwords_fields(action['config'], response.json()[action['action_name']]['schema'])

            normalize_saved_action_results(task['result']['main']['action']['results'])
            clear_saved_action_passwords(task['result']['main']['action'])
            for key in [ACTIONS_SUCCESS_FIELD, ACTIONS_FAILURE_FIELD, ACTIONS_POST_FIELD]:
                arr = task['result'][key]
                for x in arr:
                    normalize_saved_action_results(x['action']['results'])

            task_metadata = task['result']['metadata']
            return gui_helpers.beautify_db_entry({
                '_id': task['_id'],
                'enforcement': task['post_json']['report_name'],
                'view': task_metadata['trigger']['view']['name'],
                'period': task_metadata['trigger']['period'],
                'condition': task_metadata['triggered_reason'],
                'started': task['started_at'],
                'finished': task['finished_at'],
                'result': task['result']
            })

        return jsonify(beautify_task(self.enforcement_tasks_runs_collection.find_one({
            '_id': ObjectId(task_id)
        })))

    ###########
    # PLUGINS #
    ###########

    @gui_add_rule_logged_in('plugins')
    def plugins(self):
        """
        Get all plugins configured in core and update each one's status.
        Status will be "error" if the plugin is not registered.
        Otherwise it will be "success", if currently running or "warning", if  stopped.

        :mongo_filter
        :return: List of plugins with
        """
        plugins_available = self.get_available_plugins_from_core()
        db_connection = self._get_db_connection()
        plugins_from_db = db_connection['core']['configs'].find({'plugin_type': 'Plugin'}).sort(
            [(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
        plugins_to_return = []
        for plugin in plugins_from_db:
            # TODO check supported features
            if plugin['plugin_type'] != 'Plugin' or plugin['plugin_name'] in [AGGREGATOR_PLUGIN_NAME,
                                                                              'gui',
                                                                              'watch_service',
                                                                              'execution',
                                                                              'system_scheduler']:
                continue

            processed_plugin = {'plugin_name': plugin['plugin_name'],
                                'unique_plugin_name': plugin[PLUGIN_UNIQUE_NAME],
                                'status': 'error',
                                'state': 'Disabled'
                                }
            if plugin[PLUGIN_UNIQUE_NAME] in plugins_available:
                processed_plugin['status'] = 'warning'
                response = self.request_remote_plugin(
                    'trigger_state/execute', plugin[PLUGIN_UNIQUE_NAME])
                if response.status_code != 200:
                    logger.error('Error getting state of plugin {0}'.format(
                        plugin[PLUGIN_UNIQUE_NAME]))
                    processed_plugin['status'] = 'error'
                else:
                    processed_plugin['state'] = response.json()
                    if processed_plugin['state']['state'] != 'Disabled':
                        processed_plugin['status'] = 'success'
            plugins_to_return.append(processed_plugin)

        return jsonify(plugins_to_return)

    @staticmethod
    def __extract_configs_and_schemas(db_connection, plugin_unique_name):
        """
        Gets the configs and configs schemas in a nice way for a specific plugin
        """
        plugin_data = {}
        schemas = list(db_connection[plugin_unique_name]['config_schemas'].find())
        configs = list(db_connection[plugin_unique_name][CONFIGURABLE_CONFIGS_COLLECTION].find())
        for schema in schemas:
            associated_config = [c for c in configs if c['config_name'] == schema['config_name']]
            if not associated_config:
                logger.error(f'Found schema without associated config for {plugin_unique_name}' +
                             f' - {schema["config_name"]}')
                continue
            associated_config = associated_config[0]
            plugin_data[associated_config['config_name']] = {
                'schema': schema['schema'],
                'config': associated_config['config']
            }
        return plugin_data

    @gui_add_rule_logged_in('plugins/configs/<plugin_name>/<config_name>', methods=['POST', 'GET'],
                            required_permissions={Permission(PermissionType.Settings, ReadOnlyJustForGet)},
                            enforce_trial=False)
    def plugins_configs_set(self, plugin_name, config_name):
        """
        Set a specific config on a specific plugin
        """
        db_connection = self._get_db_connection()
        config_collection = db_connection[plugin_name][CONFIGURABLE_CONFIGS_COLLECTION]
        if request.method == 'GET':
            schema_collection = db_connection[plugin_name]['config_schemas']
            schema = schema_collection.find_one({'config_name': config_name})['schema']
            config = clear_passwords_fields(config_collection.find_one({'config_name': config_name})['config'],
                                            schema)
            return jsonify({
                'config': config,
                'schema': schema
            })

        # Otherwise, handle POST
        config_to_set = request.get_json(silent=True)
        if config_to_set is None:
            return return_error('Invalid config', 400)

        config_from_db = config_collection.find_one({
            'config_name': config_name
        })

        if config_from_db:
            config_to_set = refill_passwords_fields(config_to_set, config_from_db['config'])

        if plugin_name == 'core' and config_name == CORE_CONFIG_NAME:
            email_settings = config_to_set.get('email_settings')
            if email_settings and email_settings.get('enabled') is True:
                if not email_settings.get('smtpHost') or not email_settings.get('smtpPort'):
                    return return_error('Host and Port are required to connect to email server', 400)
                email_server = EmailServer(email_settings['smtpHost'], email_settings['smtpPort'],
                                           email_settings.get('smtpUser'), email_settings.get('smtpPassword'),
                                           ssl_state=SSLState[email_settings.get(
                                               'use_ssl', SSLState.Unencrypted.name)],
                                           keyfile_data=self._grab_file_contents(email_settings.get('private_key'),
                                                                                 stored_locally=False),
                                           certfile_data=self._grab_file_contents(email_settings.get('cert_file'),
                                                                                  stored_locally=False),
                                           ca_file_data=self._grab_file_contents(email_settings.get('ca_file'),
                                                                                 stored_locally=False), )
                try:
                    with email_server:
                        # Just to test connection
                        logger.info(f'Connection to email server with host {email_settings["smtpHost"]}')
                except Exception:
                    message = f'Could not connect to mail server "{email_settings["smtpHost"]}"'
                    logger.exception(message)
                    return return_error(message, 400)

            proxy_settings = config_to_set.get(PROXY_SETTINGS)
            if not self.is_proxy_allows_web(proxy_settings):
                return return_error(PROXY_ERROR_MESSAGE, 400)

            global_ssl = config_to_set.get('global_ssl')
            if global_ssl and global_ssl.get('enabled') is True:
                config_cert = self._grab_file_contents(global_ssl.get('cert_file'), stored_locally=False)
                parsed_cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, config_cert)
                cn = dict(parsed_cert.get_subject().get_components())[b'CN'].decode('utf8')
                if cn != global_ssl['hostname']:
                    return return_error(f'Hostname does not match the hostname in the certificate file, '
                                        f'hostname in given cert is {cn}', 400)

        self._update_plugin_config(plugin_name, config_name, config_to_set)
        return ''

    @gui_add_rule_logged_in('plugins/configs/gui/FeatureFlags', methods=['POST', 'GET'], enforce_trial=False)
    def plugins_configs_feature_flags(self):
        plugin_name = GUI_NAME
        config_name = FeatureFlags.__name__

        if request.method == 'GET':
            db_connection = self._get_db_connection()
            config_collection = db_connection[plugin_name][CONFIGURABLE_CONFIGS_COLLECTION]
            schema_collection = db_connection[plugin_name]['config_schemas']
            return jsonify({
                'config': config_collection.find_one({'config_name': config_name})['config'],
                'schema': schema_collection.find_one({'config_name': config_name})['schema']
            })

        # Otherwise, handle POST
        if (session.get('user') or {}).get('user_name') != AXONIUS_USER_NAME:
            logger.error(f'Request to modify {FeatureFlags.__name__} from a regular user!')
            return return_error('Illegal Operation', 400)  # keep gui happy, but don't show/change the flags

        config_to_set = request.get_json(silent=True)
        if config_to_set is None:
            return return_error('Invalid config', 400)

        self._update_plugin_config(plugin_name, config_name, config_to_set)
        self.__invalidate_sessions()
        return ''

    @gui_add_rule_logged_in('configuration', methods=['GET'])
    def system_config(self):
        """
        Get only the GUIs settings as well as whether Mail Server and Syslog Server are enabled.
        This is needed for the case that user is restricted from the settings but can view pages that use them.
        The pages should render the same, so these settings must be permitted to read anyway.

        :return: Settings for the system and Global settings, indicating if Mail and Syslog are enabled
        """
        return jsonify({
            'system': self._system_settings,
            'global': {
                'mail': self._email_settings['enabled'] if self._email_settings else False,
                'syslog': self._syslog_settings['enabled'] if self._system_settings else False,
                'httpsLog': self._https_logs_settings['enabled'] if self._https_logs_settings else False,
                'jira': self._jira_settings['enabled'] if self._jira_settings else False
            }
        })

    def _update_plugin_config(self, plugin_name, config_name, config_to_set):
        """
        Update given configuration settings for given configuration name, under given plugin.
        Finally, updates the plugin on the change.

        :param plugin_name: Of whom to update the configuration
        :param config_name: To update
        :param config_to_set:
        """
        db_connection = self._get_db_connection()
        if self.request_remote_plugin('register', params={'unique_name': plugin_name}).status_code != 200:
            unique_plugins_names = self.request_remote_plugin(
                f'find_plugin_unique_name/nodes/None/plugins/{plugin_name}').json()
        else:
            unique_plugins_names = [plugin_name]
        for current_unique_plugin in unique_plugins_names:
            config_collection = db_connection[current_unique_plugin][CONFIGURABLE_CONFIGS_COLLECTION]
            config_collection.replace_one(filter={'config_name': config_name}, replacement={
                'config_name': config_name, 'config': config_to_set})
            self.request_remote_plugin('update_config', current_unique_plugin, method='POST')

    @gui_add_rule_logged_in('plugins/<plugin_unique_name>/<command>', methods=['POST'],
                            required_permissions={Permission(PermissionType.Adapters,
                                                             PermissionLevel.ReadOnly)})
    def run_plugin(self, plugin_unique_name, command):
        """
        Calls endpoint of given plugin_unique_name, according to given command
        The command should comply with the /supported_features of the plugin

        :param plugin_unique_name:
        :return:
        """
        request_data = self.get_request_data_as_object()
        response = self.request_remote_plugin(f'{command}/{request_data["trigger"]}', plugin_unique_name, method='post')
        if response and response.status_code == 200:
            return ''
        return response.json(), response.status_code

    @gui_add_rule_logged_in('plugins/<plugin_name>/upload_file', methods=['POST'],
                            required_permissions={Permission(PermissionType.Adapters,
                                                             PermissionLevel.ReadWrite)})
    def plugins_upload_file(self, plugin_name):
        return self._upload_file(plugin_name)

    @gui_add_rule_logged_in('config/<config_name>', methods=['POST', 'GET'],
                            required_permissions={Permission(PermissionType.Settings,
                                                             ReadOnlyJustForGet)})
    def configuration(self, config_name):
        """
        Get or set config by name
        :param config_name: Config to fetch
        :return:
        """
        configs_collection = self._get_collection('config')
        if request.method == 'GET':
            return jsonify(
                configs_collection.find_one({'name': config_name},
                                            )['value'])
        if request.method == 'POST':
            config_to_add = request.get_json(silent=True)
            if config_to_add is None:
                return return_error('Invalid filter', 400)
            configs_collection.update({'name': config_name},
                                      {'name': config_name, 'value': config_to_add},
                                      upsert=True)
            return ''

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_add_rule_logged_in('notifications', methods=['POST', 'GET'],
                            required_permissions={Permission(PermissionType.Dashboard, ReadOnlyJustForGet)})
    def notifications(self, limit, skip, mongo_filter, mongo_sort):
        """
        Get all notifications
        :param limit: limit for pagination
        :param skip: start index for pagination
        :return:
        """
        db = self._get_db_connection()
        notification_collection = db['core']['notifications']

        # GET
        if request.method == 'GET':
            should_aggregate = request.args.get('aggregate', False)
            if should_aggregate:
                pipeline = [{'$group': {'_id': '$title', 'count': {'$sum': 1}, 'date': {'$last': '$_id'},
                                        'severity': {'$last': '$severity'}, 'seen': {'$last': '$seen'}}},
                            {'$addFields': {'title': '$_id'}}]
                notifications = []
                for n in notification_collection.aggregate(pipeline):
                    n['_id'] = n['date']
                    notifications.append(gui_helpers.beautify_db_entry(n))
            else:
                sort = []
                for field, direction in mongo_sort.items():
                    sort.append(('_id' if field == 'date_fetched' else field, direction))
                if not sort:
                    sort.append(('_id', pymongo.DESCENDING))
                notifications = [gui_helpers.beautify_db_entry(n) for n in notification_collection.find(
                    mongo_filter, projection={'_id': 1, 'who': 1, 'plugin_name': 1, 'type': 1, 'title': 1,
                                              'seen': 1, 'severity': 1}).sort(sort).skip(skip).limit(limit)]

            return jsonify(notifications)
        # POST
        elif request.method == 'POST':
            # if no ID is sent all notifications will be changed to seen.
            notifications_to_see = request.get_json(silent=True)
            if notifications_to_see is None or len(notifications_to_see['notification_ids']) == 0:
                update_result = notification_collection.update_many(
                    {'seen': False}, {'$set': {'seen': notifications_to_see.get('seen', True)}})
            else:
                update_result = notification_collection.update_many(
                    {'_id': {'$in': [ObjectId(x) for x in notifications_to_see.get('notification_ids', [])]}
                     }, {'$set': {'seen': True}})
            return str(update_result.modified_count), 200

    @gui_helpers.filtered()
    @gui_add_rule_logged_in('notifications/count', methods=['GET'],
                            required_permissions={Permission(PermissionType.Dashboard, PermissionLevel.ReadOnly)})
    def notifications_count(self, mongo_filter):
        """
        Fetches from core's notification collection, according to given mongo_filter,
        and counts how many entries in retrieved cursor
        :param mongo_filter: Generated by the filtered() decorator, according to uri param "filter"
        :return: Number of notifications matching given filter
        """
        db = self._get_db_connection()
        notification_collection = db['core']['notifications']
        return str(notification_collection.count_documents(mongo_filter))

    @gui_add_rule_logged_in('notifications/<notification_id>', methods=['GET'],
                            required_permissions={Permission(PermissionType.Dashboard,
                                                             PermissionLevel.ReadOnly)})
    def notifications_by_id(self, notification_id):
        """
        Get all notification data
        :param notification_id: Notification ID
        :return:
        """
        db = self._get_db_connection()
        notification_collection = db['core']['notifications']
        return jsonify(
            gui_helpers.beautify_db_entry(notification_collection.find_one({'_id': ObjectId(notification_id)})))

    @gui_helpers.add_rule_unauth('get_login_options')
    def get_login_options(self):
        return jsonify({
            'okta': {
                'enabled': self._okta['enabled'],
                'client_id': self._okta['client_id'],
                'url': self._okta['url'],
                'gui2_url': self._okta['gui2_url']
            },
            'ldap': {
                'enabled': self.__ldap_login['enabled'],
                'default_domain': self.__ldap_login['default_domain']
            },
            'saml': {
                'enabled': self.__saml_login['enabled'],
                'idp_name': self.__saml_login['idp_name']
            }
        })

    @gui_helpers.add_rule_unauth('login', methods=['GET', 'POST'])
    def login(self):
        """
        Get current user or login
        :return:
        """
        if request.method == 'GET':
            user = session.get('user')
            if user is None:
                return return_error('Not logged in', 401)
            if 'pic_name' not in user:
                user['pic_name'] = self.DEFAULT_AVATAR_PIC
            user = dict(user)
            user['permissions'] = {
                k.name: v.name for k, v in user['permissions'].items()
            }
            log_metric(logger, 'LOGIN_MARKER', 0)
            user_name = user.get('user_name')
            source = user.get('source')
            if user_name != AXONIUS_USER_NAME:
                self.send_external_info_log(f'UI Login with user: {user_name} of source {source}')
            beautiful_user = beautify_user_entry(user)
            oidc_data: OidcData = session.get('oidc_data')

            if oidc_data:
                beautiful_user['oidc_data'] = oidc_data.beautify()

            return jsonify(beautiful_user), 200

        log_in_data = self.get_request_data_as_object()
        if log_in_data is None:
            return return_error('No login data provided', 400)
        user_name = log_in_data.get('user_name')
        password = log_in_data.get('password')
        remember_me = log_in_data.get('remember_me', False)
        if not isinstance(remember_me, bool):
            return return_error('remember_me isn\'t boolean', 401)
        user_from_db = self.__users_collection.find_one(filter_archived({
            'user_name': user_name,
            'source': 'internal'  # this means that the user must be a local user and not one from an external service
        }))
        if user_from_db is None:
            logger.info(f'Unknown user {user_name} tried logging in')
            return return_error('Wrong user name or password', 401)

        if not bcrypt.verify(password, user_from_db['password']):
            logger.info(f'User {user_name} tried logging in with wrong password')
            return return_error('Wrong user name or password', 401)
        if request and request.referrer and 'localhost' not in request.referrer \
                and '127.0.0.1' not in request.referrer \
                and 'diag-l.axonius.com' not in request.referrer \
                and user_name != AXONIUS_USER_NAME:
            self.system_collection.replace_one({'type': 'server'},
                                               {'type': 'server', 'server_name': parse_url(request.referrer).host},
                                               upsert=True)
        self.__perform_login_with_user(user_from_db, remember_me)
        return ''

    def __perform_login_with_user(self, user, remember_me=False):
        """
        Given a user, mark the current session as associated with it
        """
        user = dict(user)
        user_name = user.get('user_name')
        if not has_customer_login_happened() and user_name != AXONIUS_USER_NAME:
            logger.info('First customer login occurred.')
            LOGGED_IN_MARKER_PATH.touch()

        user['permissions'] = deserialize_db_permissions(user['permissions'])
        session['user'] = user
        session.permanent = remember_me

    def __exteranl_login_successful(self, source: str,
                                    username: str,
                                    first_name: str = None,
                                    last_name: str = None,
                                    picname: str = None,
                                    remember_me: bool = False,
                                    additional_userinfo: dict = None):
        """
        Our system supports external login systems, such as LDAP, and Okta.
        To generically support such systems with our permission model we must normalize the login mechanism.
        Once the code that handles the login with the external source finishes it must call this method
        to finalize the login.
        :param source: the name of the service that made the connection, i.e. 'LDAP'
        :param username: the username from the service, could also be an email
        :param first_name: the first name of the user (optional)
        :param last_name: the last name of the user (optional)
        :param picname: the URL of the avatar of the user (optional)
        :param remember_me: whether or not to remember the session after the browser has been closed
        :return: None
        """
        role_name = None
        config_doc = self.__users_config_collection.find_one({})
        if config_doc and config_doc.get('external_default_role'):
            role_name = config_doc['external_default_role']
        user = self.__create_user_if_doesnt_exist(username, first_name, last_name, picname, source,
                                                  role_name=role_name,
                                                  additional_userinfo=additional_userinfo)
        self.__perform_login_with_user(user, remember_me)

    def __create_user_if_doesnt_exist(self, username, first_name, last_name, picname=None, source='internal',
                                      password=None, role_name=None, additional_userinfo=None):
        """
        Create a new user in the system if it does not exist already
        :return: Created user
        """
        if source != 'internal' and password:
            password = bcrypt.hash(password)

        match_user = {
            'user_name': username,
            'source': source
        }
        user = self.__users_collection.find_one(filter_archived(match_user))
        if not user:
            user = {
                'user_name': username,
                'first_name': first_name,
                'last_name': last_name,
                'pic_name': picname or self.DEFAULT_AVATAR_PIC,
                'source': source,
                'password': password,
                'api_key': secrets.token_urlsafe(),
                'api_secret': secrets.token_urlsafe(),
                'additional_userinfo': additional_userinfo or {}
            }
            if role_name:
                # Take the permissions set from the defined role
                role_doc = self.__roles_collection.find_one(filter_archived({
                    'name': role_name
                }))
                if not role_doc or 'permissions' not in role_doc:
                    logger.error(f'The role {role_name} was not found and default permissions will be used.')
                else:
                    user['permissions'] = role_doc['permissions']
                    user['role_name'] = role_name
            if 'permissions' not in user:
                user['permissions'] = {
                    p.name: PermissionLevel.Restricted.name for p in PermissionType
                }
                user['permissions'][PermissionType.Dashboard.name] = PermissionLevel.ReadOnly.name

            self.__users_collection.replace_one(match_user, user, upsert=True)
            user = self.__users_collection.find_one(filter_archived(match_user))
        return user

    @gui_helpers.add_rule_unauth('okta-redirect')
    def okta_redirect(self):
        okta_settings = self._okta
        if not okta_settings['enabled']:
            return return_error('Okta login is disabled', 400)
        oidc = try_connecting_using_okta(okta_settings)
        if oidc is not None:
            session['oidc_data'] = oidc
            # Notice! If you change the first parameter, then our CURRENT customers will have their
            # users re-created next time they log in. This is bad! If you change this, please change
            # the upgrade script as well.
            self.__exteranl_login_successful(
                'okta',  # Look at the comment above
                oidc.claims['email'],
                oidc.claims.get('given_name', ''),
                oidc.claims.get('family_name', '')
            )

        return redirect('/', code=302)

    @gui_helpers.add_rule_unauth('login/ldap', methods=['POST'])
    def ldap_login(self):
        try:
            log_in_data = self.get_request_data_as_object()
            if log_in_data is None:
                return return_error('No login data provided', 400)
            user_name = log_in_data.get('user_name')
            password = log_in_data.get('password')
            domain = log_in_data.get('domain')
            ldap_login = self.__ldap_login
            if not ldap_login['enabled']:
                return return_error('LDAP login is disabled', 400)

            try:
                conn = LdapConnection(ldap_login['dc_address'], f'{domain}\\{user_name}', password,
                                      use_ssl=SSLState[ldap_login['use_ssl']],
                                      ca_file_data=create_temp_file(self._grab_file_contents(
                                          ldap_login['private_key'])) if ldap_login['private_key'] else None,
                                      cert_file=create_temp_file(self._grab_file_contents(
                                          ldap_login['cert_file'])) if ldap_login['cert_file'] else None,
                                      private_key=create_temp_file(self._grab_file_contents(
                                          ldap_login['ca_file'])) if ldap_login['ca_file'] else None)
            except LdapException:
                logger.exception('Failed login')
                return return_error('Failed logging into AD')
            except Exception:
                logger.exception('Unexpected exception')
                return return_error('Failed logging into AD')

            result = conn.get_user(user_name)
            if not result:
                return return_error('Failed login')
            user, groups = result
            needed_group = ldap_login['group_cn']
            groups_prefix = [group.split('.')[0] for group in groups]
            if needed_group:
                if needed_group.split('.')[0] not in groups_prefix:
                    return return_error(f'The provided user is not in the group {needed_group}')
            image = None
            try:
                thumbnail_photo = user.get('thumbnailPhoto') or \
                    user.get('exchangePhoto') or \
                    user.get('jpegPhoto') or \
                    user.get('photo') or \
                    user.get('thumbnailLogo')
                if thumbnail_photo is not None:
                    if type(thumbnail_photo) == list:
                        thumbnail_photo = thumbnail_photo[0]  # I think this can happen from some reason..
                    image = bytes_image_to_base64(thumbnail_photo)
            except Exception:
                logger.exception(f'Exception while setting thumbnailPhoto for user {user_name}')

            # Notice! If you change the first parameter, then our CURRENT customers will have their
            # users re-created next time they log in. This is bad! If you change this, please change
            # the upgrade script as well.
            self.__exteranl_login_successful('ldap',  # look at the comment above
                                             user.get('displayName') or user_name,
                                             user.get('givenName') or '',
                                             user.get('sn') or '',
                                             image or self.DEFAULT_AVATAR_PIC)
            return ''
        except ldap3.core.exceptions.LDAPException:
            return return_error('LDAP verification has failed, please try again')
        except Exception:
            logger.exception('LDAP Verification error')
            return return_error('An error has occurred while verifying your account')

    def __get_flask_request_for_saml(self, req):
        axonius_external_url = str(self.__saml_login.get('axonius_external_url') or '').strip()
        if axonius_external_url:
            # do not parse the original host port and scheme, parse the input we got
            self_url = RESTConnection.build_url(axonius_external_url).strip('/')
        else:
            self_url = RESTConnection.build_url(req.url).strip('/')

        url_data = parse_url(self_url)
        req_object = {
            'https': 'on' if url_data.scheme == 'https' else 'off',
            'http_host': url_data.host,
            'server_port': url_data.port,
            'script_name': req.path,
            'get_data': req.args.copy(),
            'post_data': req.form.copy()
        }

        return self_url, req_object

    def __get_saml_auth_object(self, req, settings, parse_idp):
        # If server is behind proxys or balancers use the HTTP_X_FORWARDED fields
        self_url, req_object = self.__get_flask_request_for_saml(req)

        with open(SAML_SETTINGS_FILE_PATH, 'rt') as f:
            saml_settings = json.loads(f.read())

        # configure service provider (us) settings
        saml_settings['sp']['entityId'] = f'{self_url}/api/login/saml/metadata/'
        saml_settings['sp']['assertionConsumerService']['url'] = f'{self_url}/api/login/saml/?acs'
        saml_settings['sp']['singleLogoutService']['url'] = f'{self_url}/api/logout/'

        # Now for the identity provider path.
        # At this point we must use the metadata file we have been provided in the settings, or use
        # the raw settings we have been provided.
        if parse_idp:
            # sometimes, the idp is not important (like when we are returning the metadata.
            if settings.get('metadata_url'):
                idp_settings = settings.get('idp_data_from_metadata')
                if not idp_settings:
                    raise ValueError('Metadata URL is invalid')

                if 'idp' not in idp_settings:
                    raise ValueError(f'Metadata XML does not contain "idp", please set the SAML config manually')

                saml_settings['idp'] = idp_settings['idp']
            else:
                try:
                    certificate = self._grab_file_contents(settings['certificate']).decode('utf-8').strip().splitlines()
                    if 'BEGIN CERTIFICATE' in certificate[0].upper():
                        # we must remove the header and footer
                        certificate = certificate[1:-1]

                    certificate = ''.join(certificate)

                    saml_settings['idp']['entityId'] = settings['entity_id']
                    saml_settings['idp']['singleSignOnService']['url'] = settings['sso_url']
                    saml_settings['idp']['x509cert'] = certificate
                except Exception:
                    logger.exception(f'Invalid SAML Settings: {saml_settings}')
                    raise ValueError(f'Invalid SAML settings, please check them!')

        try:
            auth = OneLogin_Saml2_Auth(req_object, saml_settings)
            return auth
        except Exception:
            logger.exception(f'Failed to create Saml2_Auth object, saml_settings: {saml_settings}')
            raise

    @gui_helpers.add_rule_unauth('login/saml/metadata/', methods=['GET', 'POST'])
    def saml_login_metadata(self):
        saml_settings = self.__saml_login
        # Metadata can always exist, no need to check if SAML has been activated.

        auth = self.__get_saml_auth_object(request, saml_settings, False)
        settings = auth.get_settings()
        metadata = settings.get_sp_metadata()
        errors = settings.validate_metadata(metadata)

        if len(errors) == 0:
            resp = make_response(metadata, 200)
            resp.headers['Content-Type'] = 'text/xml'
            resp.headers['Content-Disposition'] = 'attachment;filename=axonius_saml_metadata.xml'
            return resp
        else:
            return return_error(', '.join(errors))

    @gui_helpers.add_rule_unauth('login/saml/', methods=['GET', 'POST'])
    def saml_login(self):
        self_url, req = self.__get_flask_request_for_saml(request)
        saml_settings = self.__saml_login

        if not saml_settings['enabled']:
            return return_error('SAML-Based login is disabled', 400)

        auth = self.__get_saml_auth_object(request, saml_settings, True)

        if 'acs' in request.args:
            auth.process_response()
            errors = auth.get_errors()
            if len(errors) == 0:
                self_url_beginning = self_url

                if 'RelayState' in request.form and not request.form['RelayState'].startswith(self_url_beginning):
                    return redirect(auth.redirect_to(request.form['RelayState']))

                attributes = auth.get_attributes()
                name_id = auth.get_nameid() or \
                    attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name')

                given_name = attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname')
                surname = attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname')
                picture = None

                if not name_id:
                    logger.info(f'SAML Login failure, attributes are {attributes}')
                    raise ValueError(f'Error! SAML identity provider did not respond with attribute "name"')

                # Some of these attributes can come back as a list. If that is the case we just make things look nicer
                if isinstance(name_id, list) and len(name_id) == 1:
                    name_id = name_id[0]
                if isinstance(given_name, list) and len(given_name) == 1:
                    given_name = given_name[0]
                if isinstance(surname, list) and len(surname) == 1:
                    surname = surname[0]

                # Notice! If you change the first parameter, then our CURRENT customers will have their
                # users re-created next time they log in. This is bad! If you change this, please change
                # the upgrade script as well.
                self.__exteranl_login_successful('saml',  # look at the comment above
                                                 name_id,
                                                 given_name or name_id,
                                                 surname or '',
                                                 picture or self.DEFAULT_AVATAR_PIC)

                logger.info(f'SAML Login success with name id {name_id}')
                return redirect('/', code=302)
            else:
                return return_error(', '.join(errors) + f' - Last error reason: {auth.get_last_error_reason()}')

        else:
            return redirect(auth.login())

    @gui_add_rule_logged_in('logout', methods=['GET'])
    def logout(self):
        """
        Clears session, logs out
        :return:
        """
        logger.info(f'User {session} has logged out')
        session['user'] = None
        return ''

    @gui_helpers.paginated()
    @gui_add_rule_logged_in('system/users', methods=['GET', 'PUT'],
                            required_permissions={Permission(PermissionType.Settings, PermissionLevel.ReadWrite)})
    def system_users(self, limit, skip):
        """
        GET Returns all users of the system
        PUT Create a new user

        :param limit: limit for pagination
        :param skip: start index for pagination
        :return:
        """
        if request.method == 'GET':
            return jsonify(beautify_user_entry(n) for n in
                           self.__users_collection.find(filter_archived(
                               {
                                   'user_name': {
                                       '$ne': self.ALTERNATIVE_USER['user_name']
                                   }
                               })).sort([('_id', pymongo.ASCENDING)])
                           .skip(skip)
                           .limit(limit))
        # Handle PUT - only option left
        post_data = self.get_request_data_as_object()
        post_data['password'] = bcrypt.hash(post_data['password'])
        # Make sure user is unique by combo of name and source (no two users can have same name and same source)
        if self.__users_collection.find_one(filter_archived(
                {
                    'user_name': post_data['user_name'],
                    'source': 'internal'
                })):
            return return_error('User already exists', 400)
        self.__create_user_if_doesnt_exist(post_data['user_name'], post_data['first_name'], post_data['last_name'],
                                           picname=None, source='internal', password=post_data['password'],
                                           role_name=post_data.get('role_name'))
        return ''

    @gui_add_rule_logged_in('system/users/self/additional_userinfo', methods=['POST'])
    def system_users_additional_userinfo(self):
        """
        Updates the userinfo for the current user
        :return:
        """
        post_data = self.get_request_data_as_object()

        self.__users_collection.update_one({'_id': ObjectId(session['user']['_id'])},
                                           {'$set': {'additional_userinfo': post_data}})
        return '', 200

    @gui_add_rule_logged_in('system/users/<user_id>/password', methods=['POST'])
    def system_users_password(self, user_id):
        """
        Change a password for a specific user. It must be the same user as currently logged in to the system.
        Post data is expected to have the old password, matching the one in the DB

        :param user_id:
        :return:
        """
        post_data = self.get_request_data_as_object()
        user = session['user']
        if str(user['_id']) != user_id:
            return return_error('Login to your user first')

        if not bcrypt.verify(post_data['old'], user['password']):
            return return_error('Given password is wrong')

        self.__users_collection.update_one({'_id': ObjectId(user_id)},
                                           {'$set': {'password': bcrypt.hash(post_data['new'])}})
        self.__invalidate_sessions(user_id)
        return '', 200

    @gui_add_rule_logged_in('system/users/<user_id>/access', methods=['POST'],
                            required_permissions={Permission(PermissionType.Settings,
                                                             PermissionLevel.ReadWrite)})
    def system_users_access(self, user_id):
        """
        Change permissions for a specific user, given the correct permissions.
        Post data is expected to contain the permissions object and the role, if there is one.

        :param user_id:
        :return:
        """
        post_data = self.get_request_data_as_object()
        self.__users_collection.update_one({'_id': ObjectId(user_id)},
                                           {'$set': post_data})
        self.__invalidate_sessions(user_id)
        return ''

    @gui_add_rule_logged_in('system/users/<user_id>', methods=['DELETE'],
                            required_permissions={Permission(PermissionType.Settings,
                                                             PermissionLevel.ReadWrite)})
    def system_users_delete(self, user_id):
        """
        Deletes a user
        """
        self.__users_collection.update_one({'_id': ObjectId(user_id)},
                                           {'$set': {'archived': True}})
        self.__invalidate_sessions(user_id)
        return ''

    @gui_add_rule_logged_in('roles', methods=['GET', 'PUT', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Settings, PermissionLevel.ReadWrite)})
    def roles(self):
        """
        Service for getting the list of all roles from the DB or creating new roles.
        Roles' names serve as their unique keys

        :return: GET list of roles with their set of permissions
        """
        if request.method == 'GET':
            return jsonify(
                [gui_helpers.beautify_db_entry(entry) for entry in self.__roles_collection.find(filter_archived())])

        role_data = self.get_request_data_as_object()
        if 'name' not in role_data:
            logger.error('Name is required for saving a new role')
            return return_error('Name is required for saving a new role', 400)

        match_role = {
            'name': role_data['name']
        }
        existing_role = self.__roles_collection.find_one(filter_archived(match_role))
        if request.method != 'PUT' and not existing_role:
            logger.error(f'Role by the name {role_data["name"]} was not found')
            return return_error(f'Role by the name {role_data["name"]} was not found', 400)
        elif request.method == 'PUT' and existing_role:
            logger.error(f'Role by the name {role_data["name"]} already exists')
            return return_error(f'Role by the name {role_data["name"]} already exists', 400)

        match_user_role = {
            'role_name': role_data['name']
        }
        if request.method == 'DELETE':
            self.__roles_collection.update_one(match_role, {
                '$set': {
                    'archived': True
                }
            })
            self.__users_collection.update_many(match_user_role, {
                '$set': {
                    'role_name': ''
                }
            })
        else:
            # Handling 'PUT' and 'POST' similarly - new role may replace an existing, archived one
            self.__roles_collection.replace_one(match_role, role_data, upsert=True)
            self.__users_collection.update_many(match_user_role, {
                '$set': {
                    'permissions': role_data['permissions']
                }
            })
        return ''

    @gui_add_rule_logged_in('roles/default', methods=['GET', 'POST'],
                            required_permissions={Permission(PermissionType.Settings, PermissionLevel.ReadWrite)})
    def roles_default(self):
        """
        Receives a name of a role that will be assigned by default to every external user created

        :return:
        """
        if request.method == 'GET':
            config_doc = self.__users_config_collection.find_one({})
            if not config_doc or 'external_default_role' not in config_doc:
                return ''
            return config_doc['external_default_role']

        # Handle POST, the only option left
        default_role_data = self.get_request_data_as_object()
        if not default_role_data.get('name'):
            logger.error('Role name is required in order to set it as a default')
            return return_error('Role name is required in order to set it as a default')
        if self.__roles_collection.find_one(filter_archived(default_role_data)) is None:
            logger.error(f'Role {default_role_data["name"]} was not found and cannot be default')
            return return_error(f'Role {default_role_data["name"]} was not found and cannot be default')
        self.__users_config_collection.replace_one({}, {
            'external_default_role': default_role_data['name']
        }, upsert=True)
        return ''

    @gui_helpers.add_rule_unauth('get_constants')
    def get_constants(self):
        """
        Returns a dictionary between all string names and string values in the system.
        This is used to print "nice" spacted strings to the user while not using them as variable names
        """

        def dictify_enum(e):
            return {r.name: r.value for r in e}

        constants = dict()
        constants['permission_levels'] = dictify_enum(PermissionLevel)
        constants['permission_types'] = dictify_enum(PermissionType)
        order = [TriggerPeriod.all, TriggerPeriod.daily, TriggerPeriod.weekly, TriggerPeriod.monthly]
        constants['trigger_periods'] = [{x.name: x.value} for x in order]
        return jsonify(constants)

    @gui_helpers.add_rule_unauth('system/expired')
    def get_trial_expired(self):
        """
        Whether system has currently expired it's trial. If no trial expiration date, answer will be false.
        """
        return jsonify(self.trial_expired())

    def __invalidate_sessions(self, user_id: str = None):
        """
        Invalidate all sessions for this user except the current one
        """
        for k, v in self.__all_sessions.items():
            if k == session.sid:
                continue
            d = v.get('d')
            if not d:
                continue
            user = d.get('user')
            if user and (not user_id or str(d['user'].get('_id')) == user_id):
                d['user'] = None

    @gui_add_rule_logged_in('api_key', methods=['GET', 'POST'])
    def api_creds(self):
        """
        Get or change the API key
        """
        if request.method == 'POST':
            new_token = secrets.token_urlsafe()
            new_api_key = secrets.token_urlsafe()
            self.__users_collection.update_one(
                {
                    '_id': session['user']['_id'],
                },
                {
                    '$set': {
                        'api_key': new_api_key,
                        'api_secret': new_token
                    }
                }
            )
        api_data = self.__users_collection.find_one({
            '_id': session['user']['_id']
        })
        return jsonify({
            'api_key': api_data['api_key'],
            'api_secret': api_data['api_secret']
        })

    #############
    # DASHBOARD #
    #############

    @gui_add_rule_logged_in('dashboard/first_use', methods=['GET'], enforce_trial=False)
    def dashboard_first(self):
        """
        __is_first_time_use maintains whether any adapter was connected with a client.
        Otherwise, user should be offered to take a walkthrough of the system.

        :return: Whether this is the first use of the system
        """
        return jsonify(self.__is_system_first_use)

    def _fetch_historical_chart_intersect(self, card, from_given_date, to_given_date):
        if not card.get('config') or not card['config'].get('entity') or not card.get('view'):
            return []
        config = {**card['config'], 'entity': EntityType(card['config']['entity'])}
        latest_date = self._fetch_latest_date(config['entity'], from_given_date, to_given_date)
        if not latest_date:
            return []
        return self._fetch_chart_intersect(ChartViews[card['view']], **config, for_date=latest_date)

    def _fetch_historical_chart_compare(self, card, from_given_date, to_given_date):
        """
        Finds the latest saved result from the given view list (from card) that are in the given date range
        """
        if not card.get('view') or not card.get('config') or not card['config'].get('views'):
            return []
        historical_views = []
        for view in card['config']['views']:
            view_name = view.get('name')
            if not view.get('entity') or not view_name:
                continue
            try:
                latest_date = self._fetch_latest_date(EntityType(view['entity']), from_given_date, to_given_date)
                if not latest_date:
                    continue
                historical_views.append({'for_date': latest_date, **view})

            except Exception:
                logger.exception(f'When dealing with {view_name} and {view["entity"]}')
                continue
        if not historical_views:
            return []
        return self._fetch_chart_compare(ChartViews[card['view']], historical_views)

    def _fetch_historical_chart_segment(self, card, from_given_date, to_given_date):
        """
        Get historical data for card of metric 'segment'
        """
        if not card.get('view') or not card.get('config') or not card['config'].get('entity'):
            return []
        config = {**card['config'], 'entity': EntityType(card['config']['entity'])}
        latest_date = self._fetch_latest_date(config['entity'], from_given_date, to_given_date)
        if not latest_date:
            return []
        return self._fetch_chart_segment(ChartViews[card['view']], **config, for_date=latest_date)

    def _fetch_historical_chart_abstract(self, card, from_given_date, to_given_date):
        """
        Get historical data for card of metric 'abstract'
        """
        config = {**card['config'], 'entity': EntityType(card['config']['entity'])}
        latest_date = self._fetch_latest_date(config['entity'], from_given_date, to_given_date)
        if not latest_date:
            return []
        return self._fetch_chart_abstract(ChartViews[card['view']], **config, for_date=latest_date)

    def _fetch_latest_date(self, entity: EntityType, from_given_date: datetime, to_given_date: datetime):
        """
        For given entity and dates, check which is latest date with historical data, within the range
        """
        historical = self._historical_entity_views_db_map[entity]
        latest_date = historical.find_one({
            'accurate_for_datetime': {
                '$lt': to_given_date,
                '$gt': from_given_date,
            }
        }, sort=[('accurate_for_datetime', -1)], projection=['accurate_for_datetime'])
        if not latest_date:
            return None
        return latest_date['accurate_for_datetime']

    @gui_helpers.historical_range(force=True)
    @gui_add_rule_logged_in('saved_card_results/<card_uuid>', methods=['GET'],
                            required_permissions={Permission(PermissionType.Dashboard,
                                                             PermissionLevel.ReadOnly)})
    def saved_card_results(self, card_uuid: str, from_date: datetime, to_date: datetime):
        """
        Saved results for cards, i.e. the mechanism used to show the user the results
        of some "card" (collection of views) in the past
        """

        card = self._get_collection(DASHBOARD_COLLECTION).find_one({'_id': ObjectId(card_uuid)})
        if not card:
            return return_error('Card doesn\'t exist')

        res = None
        try:
            card_metric = ChartMetrics[card['metric']]
            handler_by_metric = {
                ChartMetrics.compare: self._fetch_historical_chart_compare,
                ChartMetrics.intersect: self._fetch_historical_chart_intersect,
                ChartMetrics.segment: self._fetch_historical_chart_segment,
                ChartMetrics.abstract: self._fetch_historical_chart_abstract
            }
            res = handler_by_metric[card_metric](card, from_date, to_date)
        except KeyError:
            logger.exception(f'Card {card["name"]} must have metric field in order to be fetched')

        if res is None:
            logger.error(f'Unexpected card found - {card["name"]} {card["metric"]}')
            return return_error('Unexpected error')

        return jsonify({x['name']: x for x in res})

    @gui_add_rule_logged_in('first_historical_date', methods=['GET'], required_permissions={
        Permission(PermissionType.Dashboard, PermissionLevel.ReadOnly)})
    def get_first_historical_date(self):
        return jsonify(first_historical_date())

    @gui_add_rule_logged_in('get_allowed_dates', required_permissions={
        Permission(PermissionType.Dashboard, PermissionLevel.ReadOnly)})
    def all_historical_dates(self):
        return jsonify(all_historical_dates())

    @gui_helpers.paginated()
    @gui_add_rule_logged_in('dashboard', methods=['POST', 'GET'],
                            required_permissions={Permission(PermissionType.Dashboard, ReadOnlyJustForGet)},
                            enforce_trial=False)
    def get_dashboard(self, skip, limit):
        if request.method == 'GET':
            return jsonify(self._get_dashboard(skip, limit))

        # Handle 'POST' request method - save dashboard configuration
        dashboard_data = self.get_request_data_as_object()
        if not dashboard_data.get('name'):
            return return_error('Name required in order to save Dashboard Chart', 400)
        if not dashboard_data.get('config'):
            return return_error('At least one query required in order to save Dashboard Chart', 400)
        update_result = self._get_collection(DASHBOARD_COLLECTION).replace_one(
            {'name': dashboard_data['name']}, dashboard_data, upsert=True)
        if not update_result.upserted_id and not update_result.modified_count:
            return return_error('Error saving dashboard chart', 400)
        return str(update_result.upserted_id)

    def __clear_dashboard_cache(self, clear_slow=False):
        """
        Clears the calculated dashboard cache, and async recalculates all dashboards
        :param clear_slow: Also clear the slow cache
        """
        if clear_slow:
            self.__generate_dashboard.update_cache()
        self.__generate_dashboard_fast.update_cache()
        adapter_data.update_cache()
        get_fielded_plugins.update_cache()
        first_historical_date.clean_cache()
        all_historical_dates.clean_cache()
        entity_fields.clean_cache()
        self.__lifecycle.clean_cache()
        self._adapters.clean_cache()

    def __generate_dashboard_uncached(self, dashboard):
        """
        See _get_dashboard
        """
        dashboard = dict(dashboard)

        dashboard_metric = ChartMetrics[dashboard['metric']]
        handler_by_metric = {
            ChartMetrics.compare: self._fetch_chart_compare,
            ChartMetrics.intersect: self._fetch_chart_intersect,
            ChartMetrics.segment: self._fetch_chart_segment,
            ChartMetrics.abstract: self._fetch_chart_abstract,
            ChartMetrics.timeline: self._fetch_chart_timeline
        }
        config = {**dashboard['config']}
        if config.get('entity'):
            # _fetch_chart_compare crashed in the wild because it got entity as a param.
            # We don't understand how such a dasbhoard chart was created. But at lease we won't crash now
            config['entity'] = EntityType(dashboard['config']['entity'])
            if self._fetch_chart_compare == handler_by_metric[dashboard_metric]:
                del config['entity']
        dashboard['data'] = handler_by_metric[dashboard_metric](ChartViews[dashboard['view']], **config)
        return gui_helpers.beautify_db_entry(dashboard)

    @rev_cached(ttl=3600 * 4, key_func=lambda self, dashboard: dashboard['_id'])
    def __generate_dashboard(self, dashboard):
        """
        See _get_dashboard
        """
        return self.__generate_dashboard_uncached(dashboard)

    @rev_cached(ttl=120, key_func=lambda self, dashboard: dashboard['_id'])
    def __generate_dashboard_fast(self, dashboard):
        """
        See _get_dashboard
        """
        return self.__generate_dashboard_uncached(dashboard)

    def _get_dashboard(self, skip=0, limit=0, uncached: bool = False):
        """
        GET Fetch current dashboard chart definitions. For each definition, fetch each of it's views and
        fetch devices_db with their view. Amount of results is mapped to each views' name, under 'data' key,
        to be returned with the dashboard definition.

        POST Save a new dashboard chart definition, given it has a name and at least one query attached

        If 'uncached' is True, then this will return a non cached version
        :return:
        """
        logger.info('Getting dashboard')
        for dashboard in self._get_collection(DASHBOARD_COLLECTION).find(filter=filter_archived(), skip=skip,
                                                                         limit=limit):
            if not dashboard.get('name'):
                logger.info(f'No name for dashboard {dashboard["_id"]}')
            elif not dashboard.get('config'):
                logger.info(f'No config found for dashboard {dashboard.get("name")}')
            else:
                # Let's fetch and execute them query filters, depending on the chart's type
                try:
                    dashboard_metric = ChartMetrics[dashboard['metric']]
                    if uncached:
                        yield self.__generate_dashboard_uncached(dashboard)
                    elif dashboard_metric == ChartMetrics.timeline:
                        # slow dashboard cache
                        yield self.__generate_dashboard(dashboard)
                    else:
                        yield self.__generate_dashboard_fast(dashboard)
                except Exception:
                    # Since there is no data, not adding this chart to the list
                    logger.exception(f'Error fetching data for chart {dashboard["name"]} ({dashboard["_id"]})')

    def _find_filter_by_name(self, entity_type: EntityType, name):
        """
        From collection of views for given entity_type, fetch that with given name.
        Return it's filter, or None if no filter.
        """
        if not name:
            return None
        view_doc = self.gui_dbs.entity_query_views_db_map[entity_type].find_one({'name': name})
        if not view_doc:
            logger.info(f'No record found for view {name}')
            return None
        return view_doc['view']

    def _fetch_chart_compare(self, chart_view: ChartViews, views):
        """
        Iterate given views, fetch each one's filter from the appropriate query collection, according to its module,
        and execute the filter on the appropriate entity collection.

        """
        if not views:
            raise Exception('No views for the chart')

        data = []
        total = 0
        for view in views:
            # Can be optimized by taking all names in advance and querying each module's collection once
            # But since list is very short the simpler and more readable implementation is fine
            entity_name = view.get('entity', EntityType.Devices.value)
            entity = EntityType(entity_name)
            view_dict = self._find_filter_by_name(entity, view['name'])
            if not view_dict:
                continue

            data_item = {
                'name': view['name'],
                'view': view_dict,
                'module': entity_name,
                'value': 0
            }
            if view.get('for_date'):
                data_item['value'] = self._historical_entity_views_db_map[entity].count_documents(
                    {
                        '$and': [
                            parse_filter(view_dict['query']['filter']), {
                                'accurate_for_datetime': view['for_date']
                            }
                        ]
                    })
                data_item['accurate_for_datetime'] = view['for_date']
            else:
                data_item['value'] = self._entity_db_map[entity].count_documents(
                    parse_filter(view_dict['query']['filter']))
            data.append(data_item)
            total += data_item['value']

        def val(element):
            return element.get('value', 0)

        data.sort(key=val, reverse=True)
        if chart_view == ChartViews.pie:
            return_data = [{'name': 'ALL', 'value': 0}]
            if total:
                return_data.extend(map(lambda x: {**x, 'value': x['value'] / total}, data))
            return return_data
        return data

    def _fetch_chart_intersect(self, _: ChartViews, entity: EntityType, base, intersecting, for_date=None):
        """
        This chart shows intersection of 1 or 2 'Child' views with a 'Parent' (expected not to be a subset of them).
        Module to be queried is defined by the parent query.

        :param _: Placeholder to create uniform interface for the chart fetching methods
        :param intersecting: List of 1 or 2 views
        :param for_date: Data will be fetched and calculated according to what is stored on this date
        :return: List of result portions for the query executions along with their names. First represents Parent query.
                 If 1 child, second represents Child intersecting with Parent.
                 If 2 children, intersection between all three is calculated, namely 'Intersection'.
                                Second and third represent each Child intersecting with Parent, excluding Intersection.
                                Fourth represents Intersection.
        """
        if not intersecting or len(intersecting) < 1:
            raise Exception('Pie chart requires at least one views')
        # Query and data collections according to given parent's module
        data_collection = self._entity_db_map[entity]

        base_view = {'query': {'filter': '', 'expressions': []}}
        base_queries = []
        if base:
            base_view = self._find_filter_by_name(entity, base)
            base_queries = [parse_filter(base_view['query']['filter'])]

        if for_date:
            # If history requested, fetch from appropriate historical db
            data_collection = self._historical_entity_views_db_map[entity]
            base_queries.append({
                'accurate_for_datetime': for_date
            })

        data = []
        total = data_collection.count_documents({'$and': base_queries} if base_queries else {})
        if not total:
            return [{'name': base or 'ALL', 'value': 0, 'remainder': True,
                     'view': {**base_view, 'query': {'filter': base_view['query']['filter']}}, 'module': entity.value}]

        child1_view = self._find_filter_by_name(entity, intersecting[0])
        child1_filter = child1_view['query']['filter']
        child1_query = parse_filter(child1_filter)
        base_filter = f'({base_view["query"]["filter"]}) and ' if base_view['query']['filter'] else ''
        child2_filter = ''
        if len(intersecting) == 1:
            # Fetch the only child, intersecting with parent
            child1_view['query']['filter'] = f'{base_filter}({child1_filter})'
            data.append({'name': intersecting[0], 'view': child1_view, 'module': entity.value,
                         'value': data_collection.count_documents({
                             '$and': base_queries + [child1_query]
                         }) / total})
        else:
            child2_view = self._find_filter_by_name(entity, intersecting[1])
            child2_filter = child2_view['query']['filter']
            child2_query = parse_filter(child2_filter)

            # Child1 + Parent - Intersection
            child1_view['query']['filter'] = f'{base_filter}({child1_filter}) and not ({child2_filter})'
            data.append({'name': intersecting[0], 'value': data_collection.count_documents({
                '$and': base_queries + [
                    child1_query,
                    {
                        '$nor': [child2_query]
                    }
                ]
            }) / total, 'module': entity.value, 'view': child1_view})

            # Intersection
            data.append(
                {'name': ' + '.join(intersecting),
                 'intersection': True,
                 'value': data_collection.count_documents({
                     '$and': base_queries + [
                         child1_query, child2_query
                     ]}) / total,
                 'view': {**base_view, 'query': {'filter': f'{base_filter}({child1_filter}) and ({child2_filter})'}},
                 'module': entity.value})

            # Child2 + Parent - Intersection
            child2_view['query']['filter'] = f'{base_filter}({child2_filter}) and not ({child1_filter})'
            data.append({'name': intersecting[1], 'value': data_collection.count_documents({
                '$and': base_queries + [
                    child2_query,
                    {
                        '$nor': [child1_query]
                    }
                ]
            }) / total, 'module': entity.value, 'view': child2_view})

        remainder = 1 - sum([x['value'] for x in data])
        child2_or = f' or ({child2_filter})' if child2_filter else ''
        return [{'name': base or 'ALL', 'value': remainder, 'remainder': True, 'view': {
            **base_view, 'query': {'filter': f'{base_filter}not (({child1_filter}){child2_or})'}
        }, 'module': entity.value}, *data]

    # pylint: disable=R0914,R0912
    def _fetch_chart_segment(self, chart_view: ChartViews, entity: EntityType, view, field, for_date=None):
        """
        Perform aggregation which matching given view's filter and grouping by give field, in order to get the
        number of results containing each available value of the field.
        For each such value, add filter combining the original filter with restriction of the field to this value.
        If the requested view is a pie, divide all found quantities by the total amount, to get proportions.

        :return: Data counting the amount / portion of occurrences for each value of given field, among the results
                of the given view's filter
        """
        # Query and data collections according to given module
        data_collection = self._entity_db_map[entity]
        base_view = {'query': {'filter': '', 'expressions': []}}
        base_queries = []
        if view:
            base_view = self._find_filter_by_name(entity, view)
            base_queries.append(parse_filter(base_view['query']['filter']))
        if for_date:
            # If history requested, fetch from appropriate historical db
            data_collection = self._historical_entity_views_db_map[entity]
            base_queries.append({
                'accurate_for_datetime': for_date
            })
        base_query = {
            '$and': base_queries
        } if base_queries else {}

        field_name = field['name']

        if field_name.startswith(SPECIFIC_DATA):
            empty_field_name = field_name[len(SPECIFIC_DATA) + 1:]
            adapter_field_name = 'adapters.' + empty_field_name
            tags_field_name = 'tags.' + empty_field_name

        elif field_name.startswith(ADAPTERS_DATA):
            splitted = field_name.split('.')
            empty_field_name = 'data.' + '.'.join(splitted[2:])
            adapter_field_name = 'adapters.' + empty_field_name
            tags_field_name = 'tags.' + empty_field_name

        aggregate_results = data_collection.aggregate([
            {
                '$match': base_query
            },
            {
                '$project': {
                    'tags': '$tags',
                    'adapters': {
                        '$filter': {
                            'input': '$adapters',
                            'as': 'i',
                            'cond': {
                                '$ne': ['$$i.data._old', True]
                            }
                        }
                    }
                }
            },
            {
                # TODO: We might need another $filter stage here for cases
                # where two adapters have the same field name and the user *really* want to
                # differentiate between the two cases.
                # It's a bit complicated to do so I'm postponing this for later.
                '$project': {
                    'field': {
                        '$filter': {
                            'input': {
                                '$setUnion': [
                                    '$' + adapter_field_name,
                                    '$' + tags_field_name
                                ]
                            },
                            'as': 'i',
                            'cond': {
                                '$ne': ['$$i', []]
                            }
                        }
                    }
                }
            },
            {
                '$group': {
                    '_id': '$field',
                    'value': {
                        '$sum': 1
                    }
                }
            },
            {
                '$project': {
                    'value': 1,
                    'name': {
                        '$cond': {
                            'if': {
                                '$eq': [
                                    '$_id', []
                                ]
                            },
                            'then': ['No Value'],
                            'else': '$_id'
                        }
                    }
                }
            },
            {
                '$sort': {
                    'value': -1
                }
            }
        ])
        base_filter = f'({base_view["query"]["filter"]}) and ' if base_view['query']['filter'] else ''
        data = []
        all_values = defaultdict(int)
        for item in aggregate_results:
            for value in item['name']:
                all_values[value] += item['value']

        for field_value, field_count in all_values.items():
            if field_value == 'No Value':
                value_filter = f'not ({field_name} == exists(true))'
            elif isinstance(field_value, str):
                value_filter = f'{field_name} == "{field_value}"'
            elif isinstance(field_value, bool):
                value_filter = f'{field_name} == {str(field_value).lower()}'
            elif isinstance(field_value, int):
                value_filter = f'{field_name} == {field_value}'
            elif isinstance(field_value, datetime):
                value_filter = f'{field_name} == date("{field_value}")'
            else:
                # you can't search by other types, currently unsupported
                value_filter = ''

            data.append({
                'name': field_value,
                'value': field_count,
                'module': entity.value,
                'view': {
                    **base_view,
                    'query': {
                        'filter': f'{base_filter}{value_filter}'
                    }
                }
            })

        if chart_view == ChartViews.pie:
            total = data_collection.count_documents(base_query)
            return [{'name': view or 'ALL', 'value': 0}, *[{**x, 'value': x['value'] / total} for x in data]]
        return data

    def _fetch_chart_abstract(self, _: ChartViews, entity: EntityType, view, field, func, for_date=None):
        """
        One piece of data that is the calculation of given func on the values of given field, returning from
                 given view's query
        """
        # Query and data collections according to given module
        data_collection = self._entity_db_map[entity]
        field_name = field['name']
        splitted = field_name.split('.')

        additional_elemmatch_data = {}

        if splitted[0] == SPECIFIC_DATA:
            processed_field_name = '.'.join(splitted[1:])
        elif splitted[0] == ADAPTERS_DATA:
            processed_field_name = 'data.' + '.'.join(splitted[2:])
            additional_elemmatch_data = {
                PLUGIN_NAME: splitted[1]
            }
        else:
            raise Exception(f'Can\'t handle this field {field_name}')

        adapter_field_name = 'adapters.' + processed_field_name
        tags_field_name = 'tags.' + processed_field_name

        base_view = {'query': {'filter': ''}}
        base_query = {
            '$or': [
                {
                    'adapters': {
                        '$elemMatch': {
                            processed_field_name: {
                                '$exists': True
                            },
                            **additional_elemmatch_data
                        }
                    }
                },
                {
                    'tags': {
                        '$elemMatch': {
                            processed_field_name: {
                                '$exists': True
                            },
                            **additional_elemmatch_data
                        }
                    }
                }
            ]
        }
        if view:
            base_view = self._find_filter_by_name(entity, view)
            base_query = {
                '$and': [
                    parse_filter(base_view['query']['filter']),
                    base_query
                ]
            }
            base_view['query']['filter'] = f'({base_view["query"]["filter"]}) and ' if view else ''

        field_compare = 'true' if field['type'] == 'bool' else 'exists(true)'
        base_view['query']['filter'] = f'{base_view["query"]["filter"]}{field["name"]} == {field_compare}'
        if for_date:
            # If history requested, fetch from appropriate historical db
            data_collection = self._historical_entity_views_db_map[entity]
            base_query = {
                '$and': [
                    base_query, {
                        'accurate_for_datetime': for_date
                    }
                ]
            }
        results = data_collection.find(base_query, projection={
            adapter_field_name: 1,
            tags_field_name: 1,
            f'adapters.{PLUGIN_NAME}': 1,
            f'tags.{PLUGIN_NAME}': 1
        })
        count = 0
        sigma = 0
        for item in results:
            field_values = gui_helpers.find_entity_field(convert_db_entity_to_view_entity(item, ignore_errors=True),
                                                         field_name)
            if not field_values:
                continue
            if ChartFuncs[func] == ChartFuncs.count:
                count += 1
                continue
            if isinstance(field_values, list):
                count += len(field_values)
                sigma += sum(field_values)
            else:
                count += 1
                sigma += field_values

        if not count:
            return [{'name': view, 'value': 0, 'view': base_view, 'module': entity.value}]
        name = f'{func} of {field["title"]} on {view or "ALL"} results'
        if ChartFuncs[func] == ChartFuncs.average:
            return [
                {'name': name, 'value': (sigma / count), 'schema': field, 'view': base_view, 'module': entity.value}]
        return [{'name': name, 'value': count, 'view': base_view, 'module': entity.value}]

    def _fetch_chart_timeline(self, _: ChartViews, views, timeframe, intersection=False):
        """
        Fetch and count results for each view from given views, per day in given timeframe.
        Timeframe can be either:
        - Absolute - defined by a start and end date to fetch between
        - Relative - defined by a unit (days, weeks, months, years) and an amount, to fetch back from now
        Create for each view a sequence of points that represent the count for each day in the range.

        :param views: List of view for which to fetch results over timeline
        :param dateFrom: Date to start fetching from
        :param dateTo: Date to fetch up to
        :return:
        """
        date_from, date_to = self._parse_range_timeline(timeframe)
        if not date_from or not date_to:
            return None

        scale = [(date_from + timedelta(i)) for i in range((date_to - date_from).days + 1)]
        date_ranges = list(_get_date_ranges(date_from, date_to))
        if intersection:
            lines = list(self._intersect_timeline_lines(views, date_ranges))
        else:
            lines = list(self._compare_timeline_lines(views, date_ranges))
        if not lines:
            return None

        return [
            ['Day'] + [{
                'label': line['title'],
                'type': 'number'
            } for line in lines],
            *[[day] + [line['points'].get(day.strftime('%m/%d/%Y')) for line in lines] for day in scale]
        ]

    def _parse_range_timeline(self, timeframe):
        """
        Timeframe dict includes choice of range for the timeline chart.
        It can be absolute and include a date to start and to end the series,
        or relative and include a unit and count to fetch back from moment of request.

        :param timeframe:
        :return:
        """
        try:
            range_type = ChartRangeTypes[timeframe['type']]
        except KeyError:
            logger.error(f'Unexpected timeframe type {timeframe["type"]}')
            return None, None
        if range_type == ChartRangeTypes.absolute:
            logger.info(f'Gathering data between {timeframe["from"]} and {timeframe["to"]}')
            try:
                date_to = parse_date(timeframe['to'])
                date_from = parse_date(timeframe['from'])
            except ValueError:
                logger.exception('Given date to or from is invalid')
                return None, None
        else:
            logger.info(f'Gathering data from {timeframe["count"]} {timeframe["unit"]} back')
            date_to = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            try:
                range_unit = ChartRangeUnits[timeframe['unit']]
            except KeyError:
                logger.error(f'Unexpected timeframe unit {timeframe["unit"]} for reltaive chart')
                return None, None
            date_from = date_to - timedelta(days=timeframe['count'] * RANGE_UNIT_DAYS[range_unit])
        return date_from, date_to

    def _compare_timeline_lines(self, views, date_ranges):
        for view in views:
            if not view.get('name'):
                continue
            entity = EntityType(view['entity'])
            base_view = self._find_filter_by_name(entity, view['name'])
            yield {
                'title': view['name'],
                'points': self._fetch_timeline_points(entity, parse_filter(base_view['query']['filter']), date_ranges)
            }

    def _intersect_timeline_lines(self, views, date_ranges):
        if len(views) != 2 or not views[0].get('name'):
            logger.error(f'Unexpected number of views for performing intersection {len(views)}')
            return None
        first_entity_type = EntityType(views[0]['entity'])
        second_entity_type = EntityType(views[1]['entity'])

        # first query handling
        base_query = {}
        if views[0].get('name'):
            base_query = parse_filter(self._find_filter_by_name(first_entity_type, views[0]['name'])['query']['filter'])
        yield {
            'title': views[0]['name'],
            'points': self._fetch_timeline_points(first_entity_type, base_query, date_ranges)
        }

        # second query handling
        intersecting_view = self._find_filter_by_name(second_entity_type, views[1]['name'])
        intersecting_query = parse_filter(intersecting_view['query']['filter'])
        if base_query:
            intersecting_query = {
                '$and': [
                    base_query, intersecting_query
                ]
            }
        yield {
            'title': f'{views[0]["name"]} and {views[1]["name"]}',
            'points': self._fetch_timeline_points(second_entity_type, intersecting_query, date_ranges)
        }

    def _fetch_timeline_points(self, entity_type: EntityType, match_query, date_ranges):
        def aggregate_for_date_range(args):
            range_from, range_to = args
            return self._historical_entity_views_db_map[entity_type].aggregate([
                {
                    '$match': {
                        '$and': [
                            match_query, {
                                'accurate_for_datetime': {
                                    '$lte': datetime.combine(range_to, datetime.min.time()),
                                    '$gte': datetime.combine(range_from, datetime.min.time())
                                }
                            }
                        ]
                    }
                }, {
                    '$group': {
                        '_id': '$accurate_for_datetime',
                        'count': {
                            '$sum': 1
                        }
                    }
                }
            ])

        points = {}
        for results in self.__aggregate_thread_pool.map_async(aggregate_for_date_range, date_ranges).get():
            for item in results:
                # _id here is the grouping id, so in fact it is accurate_for_datetime
                points[item['_id'].strftime('%m/%d/%Y')] = item.get('count', 0)
        return points

    @gui_add_rule_logged_in('dashboard/<dashboard_id>', methods=['DELETE'],
                            required_permissions={Permission(PermissionType.Dashboard,
                                                             PermissionLevel.ReadWrite)})
    def remove_dashboard(self, dashboard_id):
        """
        Fetches data, according to definition saved for the dashboard named by given name
        :return:
        """
        update_result = self._get_collection(DASHBOARD_COLLECTION).update_one(
            {'_id': ObjectId(dashboard_id)}, {'$set': {'archived': True}})
        if not update_result.modified_count:
            return return_error(f'No dashboard by the id {dashboard_id} found or updated', 400)
        return ''

    @rev_cached(ttl=3, key_func=lambda self: 1)
    def __lifecycle(self):
        is_running = self.request_remote_plugin('trigger_state/execute', SYSTEM_SCHEDULER_PLUGIN_NAME). \
            json()['state'] == TriggerStates.Triggered.name
        state_response = self.request_remote_plugin('state', SYSTEM_SCHEDULER_PLUGIN_NAME)
        if state_response.status_code != 200:
            raise RuntimeError(f'Error fetching status of system scheduler. Reason: {state_response.text}')

        state_response = state_response.json()
        state = SchedulerState(**state_response['state'])
        is_research = state.Phase == Phases.Research.name

        if state_response['stopping']:
            nice_state = ResearchStatus.stopping
        elif is_research:
            nice_state = ResearchStatus.running
        elif is_running:
            nice_state = ResearchStatus.starting
        else:
            nice_state = ResearchStatus.done

        # Map each sub-phase to a dict containing its name and status, which is determined by:
        # - Sub-phase prior to current sub-phase - 1
        # - Current sub-phase - complementary of retrieved status (indicating complete portion)
        # - Sub-phase subsequent to current sub-phase - 0
        sub_phases = []
        found_current = False
        for sub_phase in ResearchPhases:
            if is_research and sub_phase.name == state.SubPhase:
                # Reached current status - set complementary of SubPhaseStatus value
                found_current = True
                sub_phases.append({'name': sub_phase.name, 'status': 1 - (state.SubPhaseStatus or 1)})
            else:
                # Set 0 or 1, depending if reached current status yet
                sub_phases.append({'name': sub_phase.name, 'status': 0 if found_current else 1})

        return {
            'sub_phases': sub_phases,
            'next_run_time': state_response['next_run_time'],
            'status': nice_state.name
        }

    @gui_add_rule_logged_in('dashboard/lifecycle', methods=['GET'],
                            required_permissions={Permission(PermissionType.Dashboard, PermissionLevel.ReadOnly)},
                            enforce_trial=False)
    def get_system_lifecycle(self):
        """
        Fetches and build data needed for presenting current status of the system's lifecycle in a graph

        :return: Data containing:
         - All research phases names, for showing the whole picture
         - Current research sub-phase, which is empty if system is not stable
         - Portion of work remaining for the current sub-phase
         - The time next cycle is scheduled to run
        """
        return jsonify(self.__lifecycle())

    @gui_add_rule_logged_in('dashboard/adapter_data/<entity_name>', methods=['GET'],
                            required_permissions={Permission(PermissionType.Dashboard, PermissionLevel.ReadOnly)},
                            enforce_trial=False)
    def get_adapter_data(self, entity_name):
        try:
            return jsonify(adapter_data(EntityType(entity_name)))
        except KeyError:
            error = f'No such entity {entity_name}'
        except Exception:
            error = f'Could not get adapter data for entity {entity_name}'
            logger.exception(error)
        return return_error(error, 400)

    @gui_add_rule_logged_in('get_latest_report_date', methods=['GET'],
                            required_permissions={Permission(PermissionType.Reports,
                                                             PermissionLevel.ReadOnly)})
    def get_latest_report_date(self):
        recent_report = self._get_collection('reports').find_one({'filename': 'most_recent_report'})
        if recent_report is not None:
            return jsonify(recent_report['time'])
        return ''

    @gui_add_rule_logged_in('research_phase', methods=['POST'],
                            required_permissions={Permission(PermissionType.Dashboard,
                                                             PermissionLevel.ReadWrite)})
    def schedule_research_phase(self):
        """
        Schedules or initiates research phase.

        :return: Map between each adapter and the number of devices it has, unless no devices
        """
        self._trigger_remote_plugin(SYSTEM_SCHEDULER_PLUGIN_NAME, blocking=False)

        self.__lifecycle.clean_cache()
        return ''

    @gui_add_rule_logged_in('stop_research_phase', methods=['POST'],
                            required_permissions={Permission(PermissionType.Dashboard,
                                                             PermissionLevel.ReadWrite)})
    def stop_research_phase(self):
        """
        Stops currently running research phase.
        """
        logger.info('Stopping research phase')
        response = self.request_remote_plugin('stop_all', SYSTEM_SCHEDULER_PLUGIN_NAME, 'POST')

        if response.status_code != 200:
            logger.error(
                f'Could not stop research phase. returned code: {response.status_code}, '
                f'reason: {str(response.content)}')
            return return_error(f'Could not stop research phase {str(response.content)}', response.status_code)

        self.__lifecycle.clean_cache()
        return ''

    ####################
    # Executive Report #
    ####################

    def _get_adapter_data(self, adapters):
        """
        Get the definition of the adapters to include in the report. For each adapter, get the views defined for it
        and execute each one, according to its entity, to get the amount of results for it.

        :return:
        """

        def get_adapters_data():
            for adapter in adapters:
                if not adapter.get('name'):
                    continue

                views = []
                for query in adapter.get('views', []):
                    if not query.get('name') or not query.get('entity'):
                        continue
                    entity = EntityType(query['entity'])
                    view_filter = self._find_filter_by_name(entity, query['name'])
                    if view_filter:
                        query_filter = view_filter['query']['filter']
                        view_parsed = parse_filter(query_filter)
                        views.append({
                            **query,
                            'count': self._entity_db_map[entity].count_documents(view_parsed)
                        })
                adapter_clients_report = {}
                adapter_unique_name = ''
                try:
                    # Exception thrown if adapter is down or report missing, and section will appear with views only
                    adapter_unique_name = self.get_plugin_unique_name(adapter['name'])
                    adapter_reports_db = self._get_db_connection()[adapter_unique_name]
                    found_report = adapter_reports_db['report'].find_one({'name': 'report'}) or {}
                    adapter_clients_report = found_report.get('data', {})
                except Exception:
                    logger.exception(f'Error contacting the report db for adapter {adapter_unique_name} {adapter}')

                yield {'name': adapter['title'], 'queries': views, 'views': adapter_clients_report}

        return list(get_adapters_data())

    def _get_saved_views_data(self, include_all_saved_views=True, saved_queries=None):
        """
        *** Currently this function is unused ***
        For each entity in system, fetch all saved views.
        For each view, fetch first page of entities - filtered, projected, sorted_endpoint according to it's definition.

        :return: Lists of the view names along with the list of results and list of field headers, with pretty names.
        """

        def _get_field_titles(entity):
            current_entity_fields = gui_helpers.entity_fields(entity)
            name_to_title = {}
            for field in current_entity_fields['generic']:
                name_to_title[field['name']] = field['title']
            for type in current_entity_fields['specific']:
                for field in current_entity_fields['specific'][type]:
                    name_to_title[field['name']] = field['title']
            return name_to_title

        logger.info('Getting views data')
        views_data = []
        query_per_entity = {}
        for saved_query in saved_queries:
            entity = saved_query['entity']
            name = saved_query['name']
            if entity not in query_per_entity:
                query_per_entity[entity] = []
            query_per_entity[entity].append(name)
        saved_views_filter = None
        if include_all_saved_views:
            saved_views_filter = filter_archived({
                'query_type': 'saved',
                '$or': [
                    {
                        'predefined': False
                    },
                    {
                        'predefined': {
                            '$exists': False
                        }
                    }
                ]
            })
        for entity in EntityType:
            field_to_title = _get_field_titles(entity)
            # Fetch only saved views that were added by user, excluding out-of-the-box queries
            if query_per_entity.get(entity.name.lower()) and not include_all_saved_views:
                saved_views_filter = filter_by_name(query_per_entity[entity.name.lower()])

            if not saved_views_filter:
                continue

            saved_views = self.gui_dbs.entity_query_views_db_map[entity].find(saved_views_filter)
            for view_doc in saved_views:
                try:
                    view = view_doc.get('view')
                    if view:
                        filter_query = view.get('query', {}).get('filter', '')
                        log_metric(logger, 'query.report', filter_query)
                        field_list = view.get('fields', [])
                        views_data.append({
                            'name': view_doc.get('name'), 'entity': entity.value,
                            'fields': [{field_to_title.get(field, field): field} for field in field_list],
                            'data': list(gui_helpers.get_entities(limit=view.get('pageSize', 20),
                                                                  skip=0,
                                                                  view_filter=parse_filter(filter_query),
                                                                  sort=gui_helpers.get_sort(view),
                                                                  projection={field: 1 for field in field_list},
                                                                  entity_type=entity,
                                                                  default_sort=self._system_settings['defaultSort']))
                        })
                except Exception:
                    logger.exception('Problem with View {} ViewDoc {}'.format(view_doc.get('name'), str(view_doc)))
        return views_data

    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        if job_name == 'clear_dashboard_cache':
            self.__clear_dashboard_cache(clear_slow=post_json is not None and post_json.get('clear_slow') is True)

            # Don't clean too often!
            time.sleep(5)
            return ''

        elif job_name == 'execute':
            # GUI is a post correlation plugin, thus this is called near the end of the cycle
            self._trigger('clear_dashboard_cache', blocking=False)
            self.dump_metrics()
            return self.generate_new_reports_offline()
        raise RuntimeError(f'GUI was called with a wrong job name {job_name}')

    def generate_new_reports_offline(self):
        """
        Generates a new version of the report as a PDF file and saves it to the db
        (this method is NOT an endpoint)

        :return: "Success" if successful, error if there is an error
        """

        logger.info('Rendering Reports.')
        reports = self.reports_config_collection.find()
        for report in reports:
            try:
                self._generate_and_save_report(report)
            except Exception:
                logger.exception('error generating pdf for the report {}'.format(report['name']))
        return 'Success'

    def _generate_and_save_report(self, report):
        # generate_report() renders the report html
        report_html = self.generate_report(report)

        exec_report_generate_pdf_thread_id = EXEC_REPORT_GENERATE_PDF_THREAD_ID.format(report['name'])
        exec_report_generate_pdf_job = self._job_scheduler.get_job(exec_report_generate_pdf_thread_id)
        # If job doesn't exist generate it
        if exec_report_generate_pdf_job is None:
            self._job_scheduler.add_job(func=self._convert_to_pdf_and_save_report,
                                        kwargs={'report': report,
                                                'report_html': report_html},
                                        trigger='date',
                                        next_run_time=datetime.now(),
                                        name=exec_report_generate_pdf_thread_id,
                                        id=exec_report_generate_pdf_thread_id,
                                        max_instances=1)
            self._job_scheduler.start()
        else:
            exec_report_generate_pdf_job.modify(next_run_time=datetime.now())
            self._job_scheduler.reschedule_job(exec_report_generate_pdf_thread_id)
            self._job_scheduler.start()

    def _convert_to_pdf_and_save_report(self, report, report_html):
        # Writes the report pdf to a file-like object and use seek() to point to the beginning of the stream
        with io.BytesIO() as report_data:
            report_html.write_pdf(report_data)
            report_data.seek(0)
            # Uploads the report to the db and returns a uuid to retrieve it
            uuid = self._upload_report(report_data, report)
            logger.info(f'Report was saved to the db {uuid}')
            # Stores the uuid in the db in the "reports" collection
            filename = 'most_recent_{}'.format(report['name'])
            self._get_collection('reports').replace_one(
                {'filename': filename},
                {'uuid': uuid, 'filename': filename, 'time': datetime.now()}, True
            )
            report[report_consts.LAST_GENERATED_FIELD] = datetime.now()
            self._upsert_report_config(report['name'], report, False)

    def _upload_report(self, report, report_metadata):
        """
        Uploads the latest report PDF to the db
        :param report: report data
        :return:
        """
        if not report:
            return return_error('Report must exist', 401)
        report_name = 'most_recent_{}'.format(report_metadata['name'])

        # First, need to delete the old report
        self._delete_last_report(report_name)

        db_connection = self._get_db_connection()
        fs = gridfs.GridFS(db_connection[GUI_NAME])
        written_file_id = fs.put(report, filename=report_name)
        logger.info('Report successfully placed in the db')
        return str(written_file_id)

    def _delete_last_report(self, report_name):
        """
        Deletes the last version of the report pdf to avoid having too many saved versions
        :return:
        """
        report_collection = self._get_collection('reports')
        if report_collection != None:
            most_recent_report = report_collection.find_one({'filename': report_name})
            if most_recent_report != None:
                uuid = most_recent_report.get('uuid')
                if uuid != None:
                    logger.info(f'DELETE: {uuid}')
                    db_connection = self._get_db_connection()
                    fs = gridfs.GridFS(db_connection[GUI_NAME])
                    fs.delete(ObjectId(uuid))

    @gui_add_rule_logged_in('export_report/<report_name>', required_permissions={Permission(PermissionType.Dashboard,
                                                                                            PermissionLevel.ReadOnly)})
    def export_report(self, report_name):
        """
        Gets definition of report from DB for the dynamic content.
        Gets all the needed data for both pre-defined and dynamic content definitions.
        Sends the complete data to the report generator to be composed to one document and generated as a pdf file.

        If background report generation setting is turned off, the report will be generated here, as well.

        TBD Should receive ID of the report to export (once there will be an option to save many report definitions)
        :return:
        """
        report_path = self._get_existing_executive_report(report_name)
        return send_file(report_path, mimetype='application/pdf', as_attachment=True,
                         attachment_filename=report_path)

    def _get_existing_executive_report(self, name):
        report = self._get_collection('reports').find_one({'filename': 'most_recent_{}'.format(name)})
        if not report:
            self.generate_new_reports_offline()

        uuid = report['uuid']
        report_path = f'/tmp/axonius-{name}_{datetime.now()}.pdf'
        db_connection = self._get_db_connection()
        with gridfs.GridFS(db_connection[GUI_NAME]).get(ObjectId(uuid)) as report_content:
            open(report_path, 'wb').write(report_content.read())
            return report_path

    def generate_report(self, report=None):
        """
        Generates the report and returns html.
        :return: the generated report file path.
        """
        logger.info('Starting to generate report')
        saved_views = report['views'] if report else None
        include_dashboard = report.get('include_dashboard', False)
        include_all_saved_views = report.get('include_all_saved_views', False)
        include_saved_views = report.get('include_saved_views', False)
        report_data = {
            'include_dashboard': include_dashboard,
            'adapter_devices': adapter_data.call_uncached(EntityType.Devices) if include_dashboard else None,
            'adapter_users': adapter_data.call_uncached(EntityType.Users) if include_dashboard else None,
            'custom_charts': list(self._get_dashboard()) if include_dashboard else None,
            'views_data':
                self._get_saved_views_data(include_all_saved_views, saved_views) if include_saved_views else None
        }
        if not include_saved_views:
            log_metric(logger, 'query.report', None)
        if report.get('adapters'):
            report_data['adapter_data'] = self._get_adapter_data(report['adapters'])
        system_config = self.system_collection.find_one({'type': 'server'}) or {}
        server_name = system_config.get('server_name', 'localhost')
        logger.info(f'All data for report gathered - about to generate for server {server_name}')
        return ReportGenerator(report_data, 'gui/templates/report/', host=server_name).render_html(datetime.now())

    @gui_add_rule_logged_in('test_exec_report', methods=['POST'],
                            required_permissions={Permission(PermissionType.Reports,
                                                             PermissionLevel.ReadWrite)})
    def test_exec_report(self):
        try:
            report = self.get_request_data_as_object()
            self._send_report_thread(report=report)
            return ''
        except Exception as e:
            logger.exception('Failed sending test report by email.')
            return return_error(f'Problem testing report by email:\n{str(e.args[0]) if e.args else e}', 400)

    def _get_exec_report_settings(self, exec_reports_settings_collection):
        settings_objects = exec_reports_settings_collection.find(
            {'period': {'$exists': True}, 'mail_properties': {'$exists': True}})
        return settings_objects

    def _schedule_exec_report(self, exec_report_data):
        logger.info('rescheduling exec_reports')
        time_period = exec_report_data.get('period')
        current_date = datetime.now()
        next_run_time = None
        new_interval_triggger = None

        if time_period == 'weekly':
            # Next beginning of the work week (monday for most of the world).
            next_run_time = next_weekday(current_date, 0)
            next_run_time = next_run_time.replace(hour=8, minute=0)
            new_interval_triggger = CronTrigger(year='*', month='*', week='*', day_of_week=0, hour=8, minute=0)
        elif time_period == 'monthly':
            # Sets the beginning of next month (1st day no matter if it's saturday).
            next_run_time = current_date + relativedelta(months=+1)
            next_run_time = next_run_time.replace(day=1, hour=8, minute=0)
            new_interval_triggger = CronTrigger(month='1-12', week=1, day_of_week=0, hour=8, minute=0)
        elif time_period == 'daily':
            # sets it for tomorrow at 8 and reccuring every work day at 8.
            next_run_time = current_date + relativedelta(days=+1)
            next_run_time = next_run_time.replace(hour=8, minute=0)
            new_interval_triggger = CronTrigger(year='*', month='*', week='*', day_of_week='0-4', hour=8, minute=0)
        else:
            raise ValueError('period have to be in (\'daily\', \'monthly\', \'weekly\').')

        exec_report_thread_id = EXEC_REPORT_THREAD_ID.format(exec_report_data['name'])
        exec_report_job = self._job_scheduler.get_job(exec_report_thread_id)

        # If job doesn't exist generate it
        if exec_report_job is None:
            self._job_scheduler.add_job(func=self._send_report_thread,
                                        kwargs={'report': exec_report_data},
                                        trigger=new_interval_triggger,
                                        next_run_time=next_run_time,
                                        name=exec_report_thread_id,
                                        id=exec_report_thread_id,
                                        max_instances=1)
        else:
            exec_report_job.modify(next_run_time=next_run_time)
            self._job_scheduler.reschedule_job(exec_report_thread_id, trigger=new_interval_triggger)

        logger.info(f'Scheduling an exec_report sending for {next_run_time} and period of {time_period}.')
        return 'Scheduled next run.'

    @gui_add_rule_logged_in('exec_report', methods=['POST', 'GET'],
                            required_permissions={Permission(PermissionType.Reports,
                                                             ReadOnlyJustForGet)})
    def exec_report(self):
        """
        Makes the apscheduler schedule a research phase right now.
        :return:
        """
        if request.method == 'GET':
            return jsonify(self._get_exec_report_settings(self.exec_report_collection))

        elif request.method == 'POST':
            exec_report_data = self.get_request_data_as_object()
            return self._schedule_exec_report(exec_report_data)

    def _send_report_thread(self, report):
        if self.trial_expired():
            logger.error('Report email not sent - system trial has expired')
            return

        report_name = report['name']
        lock = self.exec_report_locks[report_name] if self.exec_report_locks.get(report_name) else threading.RLock()
        self.exec_report_locks[report_name] = lock
        with lock:
            report_path = self._get_existing_executive_report(report_name)
            if self.mail_sender:
                mail_properties = report['mail_properties']
                subject = mail_properties.get('mailSubject')
                logger.info(mail_properties)
                if mail_properties.get('emailList'):
                    email = self.mail_sender.new_email(subject,
                                                       mail_properties.get('emailList', []),
                                                       cc_recipients=mail_properties.get('emailListCC', []))
                    with open(report_path, 'rb') as report_file:
                        email.add_pdf(EXEC_REPORT_FILE_NAME.format(report_name), bytes(report_file.read()))
                    email.send(EXEC_REPORT_EMAIL_CONTENT)
                    report[report_consts.LAST_TRIGGERED_FIELD] = datetime.now()
                    self._upsert_report_config(report_name, report, False)
            else:
                logger.info('Email cannot be sent because no email server is configured')
                raise RuntimeWarning('No email server configured')

    def _stop_temp_maintenance(self):
        if self.trial_expired():
            logger.error('Support access not stopped - system trial has expired')
            return

        logger.info('Stopping Support Access')
        self._update_temp_maintenance(None)
        temp_maintenance_job = self._job_scheduler.get_job(TEMP_MAINTENANCE_THREAD_ID)
        if temp_maintenance_job:
            temp_maintenance_job.remove()

    def _update_temp_maintenance(self, timeout):
        self.system_collection.update_one({
            'type': 'maintenance'
        }, {
            '$set': {
                'timeout': timeout
            }
        })

    @gui_add_rule_logged_in('config/maintenance', methods=['GET', 'POST', 'PUT', 'DELETE'],
                            required_permissions={Permission(PermissionType.Settings,
                                                             ReadOnlyJustForGet)})
    def maintenance(self):
        """
        Manage the maintenance features which can be customly set by user or switched all on for a limited time.
        GET returns current config for the features
        POST updates current config for the features
        PUT start all features for given duration of time
        DELETE stop all features (should be available only if they are temporarily on)

        """
        match_maintenance = {
            'type': 'maintenance'
        }
        if request.method == 'GET':
            return jsonify(self.system_collection.find_one(match_maintenance))

        if request.method == 'POST':
            self.system_collection.update_one(match_maintenance, {
                '$set': self.get_request_data_as_object()
            })
            self._stop_temp_maintenance()

        if request.method == 'DELETE':
            self._stop_temp_maintenance()

        if request.method == 'PUT':
            temp_maintenance_job = self._job_scheduler.get_job(TEMP_MAINTENANCE_THREAD_ID)
            duration_param = self.get_request_data_as_object().get('duration', 24)
            try:
                next_run_time = time_from_now(float(duration_param))
            except ValueError:
                message = f'Value for "duration" parameter must be a number, instead got {duration_param}'
                logger.exception(message)
                return return_error(message, 400)

            logger.info('Starting Support Access')
            self._update_temp_maintenance(next_run_time)
            if temp_maintenance_job is not None:
                # Job exists, not creating another
                logger.info(f'Job already existing - updating its run time to {next_run_time}')
                temp_maintenance_job.modify(next_run_time=next_run_time)
                # self._job_scheduler.reschedule_job(SUPPORT_ACCESS_THREAD_ID, trigger='date')
            else:
                logger.info(f'Creating a job for stopping the maintenance access at {next_run_time}')
                self._job_scheduler.add_job(func=self._stop_temp_maintenance,
                                            trigger='date',
                                            next_run_time=next_run_time,
                                            name=TEMP_MAINTENANCE_THREAD_ID,
                                            id=TEMP_MAINTENANCE_THREAD_ID,
                                            max_instances=1)
            return jsonify({'timeout': next_run_time})

        return ''

    def dump_metrics(self):
        try:
            # Uncached because the values here are important for metrics
            adapter_devices = adapter_data.call_uncached(EntityType.Devices)
            adapter_users = adapter_data.call_uncached(EntityType.Users)

            log_metric(logger, SystemMetric.GUI_USERS, self.__users_collection.count_documents({}))
            log_metric(logger, SystemMetric.DEVICES_SEEN, adapter_devices['seen'])
            log_metric(logger, SystemMetric.DEVICES_UNIQUE, adapter_devices['unique'])

            log_metric(logger, SystemMetric.USERS_SEEN, adapter_users['seen'])
            log_metric(logger, SystemMetric.USERS_UNIQUE, adapter_users['unique'])

            enforcements = self.get_enforcements(limit=0,
                                                 mongo_filter={},
                                                 mongo_sort={},
                                                 skip=0)
            for enforcement in enforcements:
                log_metric(logger, SystemMetric.ENFORCEMENT_RAW, str(enforcement))

            plugins_by_plugin_name = {x[PLUGIN_NAME]
                                      for x
                                      in self.get_available_plugins_from_core().values()}

            def dump_per_adapter(mapping, subtype):
                counters = mapping['counters']
                plugins_left = set(plugins_by_plugin_name)
                for counter in counters:
                    log_metric(logger, f'adapter.{subtype}.{counter["name"]}.entities', counter['value'])
                    log_metric(logger, f'adapter.{subtype}.{counter["name"]}.entities.meta', counter['meta'])
                    plugins_left -= {counter['name']}
                for name in plugins_left:
                    log_metric(logger, f'adapter.{subtype}.{name}.entities', 0)
                    log_metric(logger, f'adapter.{subtype}.{name}.entities.meta', 0)

            dump_per_adapter(adapter_devices, 'devices')
            dump_per_adapter(adapter_users, 'users')
        except Exception:
            logger.exception('Failed to dump metrics')

    @gui_add_rule_logged_in('metadata', methods=['GET'], required_permissions={
        Permission(PermissionType.Settings, PermissionLevel.ReadOnly)})
    def get_metadata(self):
        """
        Gets the system metadata.
        :return:
        """
        return jsonify(self.metadata)

    @gui_add_rule_logged_in('historical_sizes', methods=['GET'],
                            required_permissions={Permission(PermissionType.Settings,
                                                             PermissionLevel.ReadOnly)})
    def get_historical_size_stats(self):
        sizes = {}
        for entity_type in EntityType:
            try:
                col = self._historical_entity_views_db_map[entity_type]

                # find the date of the last historical point
                last_date = col.find_one(projection={'accurate_for_datetime': 1},
                                         sort=[('accurate_for_datetime', -1)])['accurate_for_datetime']

                axonius_entities_in_last_historical_point = col.count_documents({
                    'accurate_for_datetime': last_date
                })

                stats = get_collection_stats(col)

                d = {
                    'size': stats['storageSize'],
                    'capped': get_collection_capped_size(col),
                    'avg_document_size': stats['avgObjSize'],
                    'entities_last_point': axonius_entities_in_last_historical_point
                }
                sizes[entity_type.name] = d
            except Exception:
                logger.exception(f'failed calculating stats for {entity_type}')

        disk_usage = shutil.disk_usage('/')
        return jsonify({
            'disk_free': disk_usage.free,
            'disk_used': disk_usage.used,
            'entity_sizes': sizes
        })

    ####################
    # User Notes #
    ####################

    def _entity_notes(self, entity_type: EntityType, entity_id):
        """
        Method for fetching, creating or deleting the notes for a specific entity, by the id given in the rule

        :param entity_type:  Type of entity in subject
        :param entity_id:    ID of the entity to handle notes of
        :return:             GET, list of notes for the entity
        """
        entity_doc = self._fetch_historical_entity(entity_type, entity_id, None)
        if not entity_doc:
            logger.error(f'No entity found with internal_axon_id = {entity_id}')
            return return_error(f'No entity found with internal_axon_id = {entity_id}', 400)

        entity_obj = AXONIUS_ENTITY_BY_CLASS[entity_type](self, entity_doc)
        notes_list = entity_obj.get_data_by_name(NOTES_DATA_TAG)
        if notes_list is None:
            notes_list = []

        current_user = session['user']
        if request.method == 'PUT':
            note_obj = self.get_request_data_as_object()
            note_obj['user_id'] = current_user['_id']
            note_obj['user_name'] = f'{current_user["source"]}/{current_user["user_name"]}'
            note_obj['accurate_for_datetime'] = datetime.now()
            note_obj['uuid'] = str(uuid4())
            notes_list.append(note_obj)
            entity_obj.add_data(NOTES_DATA_TAG, notes_list, action_if_exists='merge')
            note_obj['user_id'] = str(note_obj['user_id'])
            return jsonify(note_obj)

        if request.method == 'DELETE':
            note_ids_list = self.get_request_data_as_object()
            if not session['user'].get('admin') and session['user'].get('role_name') != PREDEFINED_ROLE_ADMIN:
                # Validate all notes requested to be removed belong to user
                for note in notes_list:
                    if note['uuid'] in note_ids_list and note['user_id'] != current_user['_id']:
                        logger.error('Only Administrator can remove another user\'s Note')
                        return return_error('Only Administrator can remove another user\'s Note', 400)
            remaining_notes_list = []
            for note in notes_list:
                if note['uuid'] not in note_ids_list:
                    remaining_notes_list.append(note)
            entity_obj.add_data(NOTES_DATA_TAG, remaining_notes_list, action_if_exists='merge')
            return ''

    def _entity_notes_update(self, entity_type: EntityType, entity_id, note_id):
        """
        Update the content of a specific note attached to a specific entity.
        This operation will update accurate_for_datetime.
        If this is called by an Administrator for a note of another user, the user_name will be changed too.

        :param entity_type:
        :param entity_id:
        :param note_id:
        :return:
        """
        entity_doc = self._fetch_historical_entity(entity_type, entity_id, None)
        if not entity_doc:
            logger.error(f'No entity found with internal_axon_id = {entity_id}')
            return return_error('No entity found for selected ID', 400)

        entity_obj = AXONIUS_ENTITY_BY_CLASS[entity_type](self, entity_doc)
        notes_list = entity_obj.get_data_by_name(NOTES_DATA_TAG)
        note_doc = next(x for x in notes_list if x['uuid'] == note_id)
        if not note_doc:
            logger.error(f'Entity with internal_axon_id = {entity_id} has no note at index = {note_id}')
            return return_error('Selected Note cannot be found for the Entity', 400)

        current_user = session['user']
        if current_user['_id'] != note_doc['user_id'] and not current_user.get('admin') and \
                current_user.get('role_name') != PREDEFINED_ROLE_ADMIN:
            return return_error('Only Administrator can edit another user\'s Note', 400)

        note_doc['note'] = self.get_request_data_as_object()['note']
        note_doc['user_id'] = current_user['_id']
        note_doc['user_name'] = f'{current_user["source"]}/{current_user["user_name"]}'
        note_doc['accurate_for_datetime'] = datetime.now()
        entity_obj.add_data(NOTES_DATA_TAG, notes_list, action_if_exists='merge')
        note_doc['user_id'] = str(note_doc['user_id'])
        return jsonify(note_doc)

    #############
    # Instances #
    #############

    @gui_add_rule_logged_in('instances', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Instances,
                                                             ReadOnlyJustForGet)})
    def instances(self):
        return self._instances()

    def _instances(self):
        if request.method == 'GET':
            db_connection = self._get_db_connection()
            nodes = []
            for current_node in db_connection['core']['configs'].distinct('node_id'):
                node_data = db_connection['core']['nodes_metadata'].find_one({'node_id': current_node})
                if node_data is not None:
                    nodes.append({'node_id': current_node, 'node_name': node_data.get('node_name', {}),
                                  'tags': node_data.get('tags', {}),
                                  'last_seen': self.request_remote_plugin(f'nodes/last_seen/{current_node}').json()[
                                      'last_seen'], NODE_USER_PASSWORD: node_data.get(NODE_USER_PASSWORD, '')})
                else:
                    nodes.append({'node_id': current_node, 'node_name': current_node, 'tags': {},
                                  'last_seen': self.request_remote_plugin(f'nodes/last_seen/{current_node}').json()[
                                      'last_seen'], NODE_USER_PASSWORD: ''})
            system_config = db_connection['gui']['system_collection'].find_one({'type': 'server'}) or {}
            return jsonify({'instances': nodes, 'connection_data': {'key': self.encryption_key,
                                                                    'host': system_config.get('server_name',
                                                                                              '<axonius-hostname>')}})
        elif request.method == 'POST':
            data = self.get_request_data_as_object()
            self.request_remote_plugin(f'node/{data["node_id"]}', method='POST', json={'node_name': data['node_name']})
            return ''
        elif request.method == 'DELETE':
            data = self.get_request_data_as_object()
            node_ids = data['nodeIds']
            if self.node_id in node_ids:
                raise RuntimeError('Can\'t Delete Master.')

            delete_entities = data['deleteEntities']

            plugins_available = requests.get(self.core_address + '/register').json()

            for current_node in node_ids:
                node_adapters = [x for x in plugins_available.values() if
                                 x['plugin_type'] == adapter_consts.ADAPTER_PLUGIN_TYPE and x[NODE_ID] == current_node]

                for adapter in node_adapters:
                    cursor = self._get_collection('clients', adapter[PLUGIN_UNIQUE_NAME]).find({},
                                                                                               projection={'_id': 1})
                    for current_client in cursor:
                        self.delete_client_data(adapter[PLUGIN_NAME], current_client['_id'],
                                                current_node, delete_entities)
                        self.request_remote_plugin(
                            'clients/' + str(current_client['_id']), adapter[PLUGIN_UNIQUE_NAME], method='delete')
            return ''

    @gui_add_rule_logged_in('instances/tags', methods=['DELETE', 'POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadOnly)})
    def instances_tags(self):
        if request.method == 'POST':
            data = self.get_request_data_as_object()
            self.request_remote_plugin(f'nodes/tags/{data["node_id"]}', method='POST', json={'tags': data['tags']})
            return ''
        elif request.method == 'DELETE':
            data = self.get_request_data_as_object()
            self.request_remote_plugin(f'nodes/tags/{data["node_id"]}', method='DELETE', json={'tags': data['tags']})
            return ''

    @gui_helpers.add_rule_unauth('google_analytics/collect', methods=['GET', 'POST'])
    def google_analytics_proxy(self):
        self.handle_ga_request('https://www.google-analytics.com/collect')
        return ''

    @gui_helpers.add_rule_unauth('google_analytics/r/collect', methods=['GET', 'POST'])
    def google_analytics_r_proxy(self):
        self.handle_ga_request('https://www.google-analytics.com/r/collect')
        return ''

    def handle_ga_request(self, path):
        values = dict(request.values)
        signup_collection = self._get_collection(Signup.SignupCollection)
        signup = signup_collection.find_one({})
        if signup:
            customer = signup.get(Signup.CompanyField, 'signup-not-set')
            if customer in [SIGNUP_TEST_CREDS[Signup.CompanyField], SIGNUP_TEST_COMPANY_NAME]:
                return
        else:
            customer = 'not-set'
        # referrer
        values['tid'] = 'UA-137924837-1'
        values['dr'] = f'https://{customer}'
        values['dh'] = customer
        if 'dl' in values:
            del values['dl']
        response = requests.request(request.method,
                                    path,
                                    params=values)
        if response.status_code != 200:
            logger.error('Failed to submit ga data {response}')

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.PostCorrelation

    @property
    def system_collection(self):
        return self._get_collection(GUI_SYSTEM_CONFIG_COLLECTION)

    @property
    def reports_config_collection(self):
        return self._get_collection('reports_config')

    @property
    def exec_report_collection(self):
        return self._get_collection('exec_reports_settings')

    def get_plugin_unique_name(self, plugin_name):
        return self.get_plugin_by_name(plugin_name)[PLUGIN_UNIQUE_NAME]

    def _on_config_update(self, config):
        logger.info(f'Loading GuiService config: {config}')
        self._okta = config['okta_login_settings']
        self.__saml_login = config['saml_login_settings']
        self.__ldap_login = config['ldap_login_settings']
        self._system_settings = config[SYSTEM_SETTINGS]

        metadata_url = self.__saml_login.get('metadata_url')
        if metadata_url:
            try:
                logger.info(f'Requesting metadata url for SAML Auth')
                self.__saml_login['idp_data_from_metadata'] = \
                    OneLogin_Saml2_IdPMetadataParser.parse_remote(metadata_url)
            except Exception:
                logger.exception(f'SAML Configuration change: Metadata parsing error')
                self.create_notification(
                    'SAML config change failed',
                    content='The metadata URL provided is invalid.',
                    severity_type='error'
                )

    @property
    def _maintenance_config(self):
        return self.system_collection.find_one({
            'type': 'maintenance'
        })

    @gui_helpers.add_rule_unauth(Signup.SignupEndpoint, methods=['POST', 'GET'])
    def process_signup(self):
        signup_collection = self._get_collection(Signup.SignupCollection)
        signup = signup_collection.find_one({})

        if request.method == 'GET':
            return jsonify({Signup.SignupField: signup or has_customer_login_happened()})

        # POST from here
        if signup:
            return return_error('Signup already completed', 400)

        signup_data = self.get_request_data_as_object() or {}

        new_password = signup_data[Signup.NewPassword] if \
            signup_data[Signup.ConfirmNewPassword] == signup_data[Signup.NewPassword] \
            else ''

        if not new_password:
            return return_error('Passwords do not match', 400)

        self.__users_collection.update_one({'user_name': 'admin'},
                                           {'$set': {'password': bcrypt.hash(new_password)}})

        # we don't want to store creds openly
        signup_data[Signup.NewPassword] = ''
        signup_data[Signup.ConfirmNewPassword] = ''

        signup_collection.insert_one(signup_data)
        self._get_collection(CONFIGURABLE_CONFIGS_COLLECTION).update_one({
            'config_name': FeatureFlags.__name__
        }, {
            '$set': {
                f'config.{FeatureFlagsNames.TrialEnd}':
                    (datetime.now() + timedelta(days=30)).isoformat()[:10].replace('-', '/')
            }
        })
        return jsonify({})

    @gui_helpers.add_rule_unauth('provision')
    def get_provision(self):
        if self.trial_expired():
            return jsonify(True)

        return jsonify(self._maintenance_config.get('provision', False) or
                       self._maintenance_config.get('timeout') is not None)

    @gui_helpers.add_rule_unauth('analytics')
    def get_analytics(self):
        if self.trial_expired():
            return jsonify(True)

        return jsonify(self._maintenance_config.get('analytics', False) or
                       self._maintenance_config.get('timeout') is not None)

    @gui_helpers.add_rule_unauth('troubleshooting')
    def get_troubleshooting(self):
        if self.trial_expired():
            return jsonify(True)

        return jsonify(self._maintenance_config.get('troubleshooting', False) or
                       self._maintenance_config.get('timeout') is not None)

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'items': [
                        {
                            'name': 'refreshRate',
                            'title': 'Auto-Refresh Rate (seconds)',
                            'type': 'number'
                        },
                        {
                            'name': 'singleAdapter',
                            'title': 'Use Single Adapter View',
                            'type': 'bool'
                        },
                        {
                            'name': 'multiLine',
                            'title': 'Use Table Multi Line View',
                            'type': 'bool'
                        },
                        {
                            'name': 'defaultSort',
                            'title': 'Sort by Number of Adapters in Default View',
                            'type': 'bool'
                        },
                        {
                            'name': 'percentageThresholds',
                            'title': 'Percentage Fields Severity Scopes',
                            'type': 'array',
                            'items': [
                                {
                                    'name': 'error',
                                    'title': 'Poor under:',
                                    'type': 'integer'
                                },
                                {
                                    'name': 'warning',
                                    'title': 'Average under:',
                                    'type': 'integer'
                                },
                                {
                                    'name': 'success',
                                    'title': 'Good under:',
                                    'type': 'integer'
                                }
                            ],
                            'required': ['error', 'warning', 'success']
                        },
                        {
                            'name': 'tableView',
                            'title': 'Present advanced General Data of entity in a table',
                            'type': 'bool'
                        }
                    ],
                    'required': ['refreshRate', 'singleAdapter', 'multiLine', 'defaultSort', 'tableView'],
                    'name': SYSTEM_SETTINGS,
                    'title': 'System Settings',
                    'type': 'array'
                },
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Allow Okta logins',
                            'type': 'bool'
                        },
                        {
                            'name': 'client_id',
                            'title': 'Okta application client id',
                            'type': 'string'
                        },
                        {
                            'name': 'client_secret',
                            'title': 'Okta application client secret',
                            'type': 'string',
                            'format': 'password'
                        },
                        {
                            'name': 'url',
                            'title': 'Okta application URL',
                            'type': 'string'
                        },
                        {
                            'name': 'gui2_url',
                            'title': 'The URL of Axonius GUI',
                            'type': 'string'
                        }
                    ],
                    'required': ['enabled', 'client_id', 'client_secret', 'url', 'gui2_url'],
                    'name': 'okta_login_settings',
                    'title': 'Okta Login Settings',
                    'type': 'array'
                },
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Allow LDAP logins',
                            'type': 'bool'
                        },
                        {
                            'name': 'dc_address',
                            'title': 'The host domain controller IP or DNS',
                            'type': 'string'
                        },
                        {
                            'name': 'group_cn',
                            'title': 'A group the user must be a part of',
                            'type': 'string'
                        },
                        {
                            'name': 'default_domain',
                            'title': 'Default domain to present to the user',
                            'type': 'string'
                        },
                        *COMMON_SSL_CONFIG_SCHEMA
                    ],
                    'required': ['enabled', 'dc_address'],
                    'name': 'ldap_login_settings',
                    'title': 'Ldap Login Settings',
                    'type': 'array'
                },
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Allow SAML-Based logins',
                            'type': 'bool'
                        },
                        {
                            'name': 'idp_name',
                            'title': 'The name of the Identity Provider',
                            'type': 'string'
                        },
                        {
                            'name': 'metadata_url',
                            'title': 'Metadata URL',
                            'type': 'string'
                        },
                        {
                            'name': 'axonius_external_url',
                            'title': 'Axonius External URL',
                            'type': 'string'
                        },
                        {
                            'name': 'sso_url',
                            'title': 'Single Sign-On Service URL',
                            'type': 'string'
                        },
                        {
                            'name': 'entity_id',
                            'title': 'Entity ID',
                            'type': 'string'
                        },
                        {
                            'name': 'certificate',
                            'title': 'Signing Certificate (Base64 Encoded)',
                            'type': 'file'
                        }
                    ],
                    'required': ['enabled', 'idp_name'],
                    'name': 'saml_login_settings',
                    'title': 'SAML-Based Login Settings',
                    'type': 'array'
                }
            ],
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'okta_login_settings': {
                'enabled': False,
                'client_id': '',
                'client_secret': '',
                'url': 'https://yourname.okta.com',
                'gui2_url': 'https://127.0.0.1'
            },
            'ldap_login_settings': {
                'enabled': False,
                'dc_address': '',
                'default_domain': '',
                'group_cn': '',
                **COMMON_SSL_CONFIG_SCHEMA_DEFAULTS
            },
            'saml_login_settings': {
                'enabled': False,
                'idp_name': None,
                'metadata_url': None,
                'axonius_external_url': None,
                'sso_url': None,
                'entity_id': None,
                'certificate': None
            },
            SYSTEM_SETTINGS: {
                'refreshRate': 60,
                'singleAdapter': False,
                'multiLine': False,
                'defaultSort': True,
                'percentageThresholds': {
                    'error': 40,
                    'warning': 60,
                    'success': 100,
                },
                'tableView': True
            }
        }
