import codecs
import csv
import configparser
import io
import json
import logging
import os
import secrets
import shutil
import subprocess
import tarfile
import threading
import time
import calendar
import urllib.parse
from collections import defaultdict
from datetime import date, datetime, timedelta
from multiprocessing.pool import ThreadPool
from typing import Dict, Iterable, Tuple, List

import gridfs
import ldap3
import pymongo
import requests
from apscheduler.executors.pool import \
    ThreadPoolExecutor as ThreadPoolExecutorApscheduler
from apscheduler.triggers.cron import CronTrigger
from bson import ObjectId
from dateutil import tz
from dateutil.relativedelta import relativedelta
from flask import (after_this_request, has_request_context, jsonify,
                   make_response, redirect, request, session)
from passlib.hash import bcrypt
from urllib3.util.url import parse_url
import OpenSSL
from werkzeug.wrappers import Response

# pylint: disable=import-error
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser

from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.clients.aws.utils import aws_list_s3_objects
from axonius.clients.ldap.exceptions import LdapException
from axonius.clients.ldap.ldap_connection import LdapConnection
from axonius.clients.rest.connection import RESTConnection
from axonius.compliance.compliance import get_compliance
from axonius.consts import adapter_consts, report_consts
from axonius.consts.core_consts import CORE_CONFIG_NAME, ACTIVATED_NODE_STATUS, DEACTIVATED_NODE_STATUS
from axonius.consts.gui_consts import (ENCRYPTION_KEY_PATH,
                                       EXEC_REPORT_EMAIL_CONTENT,
                                       EXEC_REPORT_FILE_NAME,
                                       EXEC_REPORT_GENERATE_PDF_THREAD_ID,
                                       EXEC_REPORT_THREAD_ID,
                                       LOGGED_IN_MARKER_PATH,
                                       PREDEFINED_ROLE_ADMIN,
                                       PREDEFINED_ROLE_READONLY,
                                       PREDEFINED_ROLE_RESTRICTED,
                                       PROXY_ERROR_MESSAGE,
                                       ROLES_COLLECTION,
                                       SIGNUP_TEST_COMPANY_NAME,
                                       SIGNUP_TEST_CREDS,
                                       TEMP_MAINTENANCE_THREAD_ID,
                                       USERS_COLLECTION,
                                       USERS_CONFIG_COLLECTION,
                                       ChartViews,
                                       FeatureFlagsNames, ResearchStatus,
                                       DASHBOARD_COLLECTION, DASHBOARD_SPACES_COLLECTION,
                                       DASHBOARD_SPACE_PERSONAL, DASHBOARD_SPACE_TYPE_CUSTOM,
                                       Signup, PROXY_DATA_PATH, DASHBOARD_LIFECYCLE_ENDPOINT,
                                       UNCHANGED_MAGIC_FOR_GUI, GETTING_STARTED_CHECKLIST_SETTING,
                                       LAST_UPDATED_FIELD, UPDATED_BY_FIELD,
                                       PREDEFINED_FIELD, CONFIG_CONFIG)
from axonius.consts.metric_consts import ApiMetric, Query, SystemMetric, GettingStartedMetric
from axonius.consts.plugin_consts import (AGGREGATOR_PLUGIN_NAME,
                                          AXONIUS_USER_NAME,
                                          CONFIGURABLE_CONFIGS_COLLECTION,
                                          CORE_UNIQUE_NAME,
                                          DEVICE_CONTROL_PLUGIN_NAME, GUI_PLUGIN_NAME,
                                          GUI_SYSTEM_CONFIG_COLLECTION,
                                          METADATA_PATH, NODE_ID, NODE_NAME, NODE_HOSTNAME,
                                          PLUGIN_NAME, PLUGIN_UNIQUE_NAME, PROXY_SETTINGS,
                                          STATIC_CORRELATOR_PLUGIN_NAME,
                                          STATIC_USERS_CORRELATOR_PLUGIN_NAME,
                                          SYSTEM_SCHEDULER_PLUGIN_NAME,
                                          SYSTEM_SETTINGS, REPORTS_PLUGIN_NAME, EXECUTION_PLUGIN_NAME, PROXY_VERIFY,
                                          NODE_DATA_INSTANCE_ID, NODE_STATUS)
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.consts.report_consts import (ACTIONS_FAILURE_FIELD, ACTIONS_FIELD,
                                          ACTIONS_MAIN_FIELD,
                                          ACTIONS_POST_FIELD,
                                          ACTIONS_SUCCESS_FIELD,
                                          LAST_TRIGGERED_FIELD,
                                          NOT_RAN_STATE,
                                          TIMES_TRIGGERED_FIELD,
                                          TRIGGERS_FIELD, ACTION_CONFIG_FIELD, ACTION_FIELD)
from axonius.consts.scheduler_consts import (Phases, ResearchPhases,
                                             SchedulerState)
from axonius.devices.device_adapter import DeviceAdapter
from axonius.email_server import EmailServer
from axonius.fields import Field
from axonius.logging.metric_helper import log_metric
from axonius.mixins.configurable import Configurable
from axonius.mixins.triggerable import (RunIdentifier,
                                        StoredJobStateCompletion, Triggerable,
                                        TriggerStates)
from axonius.plugin_base import EntityType, PluginBase, return_error, add_rule
from axonius.thread_pool_executor import LoggedThreadPoolExecutor
from axonius.types.correlation import (MAX_LINK_AMOUNT, CorrelationReason,
                                       CorrelationResult)
from axonius.types.enforcement_classes import TriggerPeriod
from axonius.types.ssl_state import (COMMON_SSL_CONFIG_SCHEMA,
                                     COMMON_SSL_CONFIG_SCHEMA_DEFAULTS,
                                     SSLState)
from axonius.users.user_adapter import UserAdapter
from axonius.utils import gui_helpers
from axonius.utils.backup import verify_preshared_key
from axonius.utils.db_querying_helper import get_entities
from axonius.utils.axonius_query_language import parse_filter
from axonius.utils.datetime import next_weekday, time_from_now
from axonius.utils.files import get_local_config_file
from axonius.utils.gui_helpers import (Permission, PermissionLevel,
                                       PermissionType, ReadOnlyJustForGet,
                                       add_labels_to_entities,
                                       check_permissions,
                                       deserialize_db_permissions,
                                       get_entity_labels, entity_fields, get_connected_user_id,
                                       find_filter_by_name,
                                       is_admin_user, get_user_permissions)
from axonius.utils.json_encoders import iterator_jsonify
from axonius.utils.metric import remove_ids
from axonius.utils.mongo_administration import (get_collection_capped_size,
                                                get_collection_stats)
from axonius.utils.mongo_chunked import get_chunks_length
from axonius.utils.mongo_escaping import escape_dict
from axonius.utils.mongo_retries import mongo_retry
from axonius.utils.parsing import bytes_image_to_base64
from axonius.utils.proxy_utils import to_proxy_string
from axonius.utils.revving_cache import rev_cached, WILDCARD_ARG
from axonius.utils.ssl import check_associate_cert_with_private_key, validate_cert_with_ca, MUTUAL_TLS_CA_PATH, \
    MUTUAL_TLS_CONFIG_FILE
from axonius.utils.threading import run_and_forget
from axonius.clients.ldap.ldap_group_cache import set_ldap_groups_cache, get_ldap_groups_cache_ttl
from gui.api import APIMixin
from gui.cached_session import CachedSessionInterface
from gui.feature_flags import FeatureFlags
from gui.gui_logic.entity_data import (get_entity_data, entity_data_field_csv,
                                       entity_notes, entity_notes_update, entity_tasks_actions,
                                       entity_tasks_actions_csv, get_task_full_name)
from gui.gui_logic.dashboard_data import (adapter_data, fetch_chart_segment, fetch_chart_segment_historical,
                                          generate_dashboard, generate_dashboard_uncached,
                                          generate_dashboard_historical)
from gui.gui_logic.db_helpers import beautify_db_entry, translate_user_id_to_details
from gui.gui_logic.ec_helpers import extract_actions_from_ec
from gui.gui_logic.fielded_plugins import get_fielded_plugins
from gui.gui_logic.filter_utils import filter_archived
from gui.gui_logic.generate_csv import get_csv_from_heavy_lifting_plugin
from gui.gui_logic.historical_dates import (all_historical_dates, first_historical_date)
from gui.gui_logic.views_data import get_views, get_views_count
from gui.gui_logic.users_helper import beautify_user_entry
from gui.okta_login import OidcData, try_connecting_using_okta
from gui.report_generator import ReportGenerator
# pylint: disable=line-too-long,superfluous-parens,too-many-statements,too-many-lines,too-many-locals,too-many-branches,keyword-arg-before-vararg,invalid-name,too-many-instance-attributes,inconsistent-return-statements,no-self-use,inconsistent-return-statements,no-else-return,no-self-use,unnecessary-pass,useless-return,cell-var-from-loop,logging-not-lazy,singleton-comparison,redefined-builtin,comparison-with-callable,too-many-return-statements,too-many-boolean-expressions,logging-format-interpolation,fixme,no-member

logger = logging.getLogger(f'axonius.{__name__}')

SAML_SETTINGS_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config', 'saml_settings.json'))


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

        now = time.time()
        try:
            return func(self, *args, **kwargs)
        finally:
            if has_request_context():
                # don't change these consts since we monitor this our alerts systems
                if request.args.get('is_refresh') != '1' and DASHBOARD_LIFECYCLE_ENDPOINT not in request.path:
                    cleanpath = remove_ids(request.path)
                    delay_seconds = time.time() - now
                    if delay_seconds > 1:
                        log_metric(logger, SystemMetric.TIMED_ENDPOINT,
                                   metric_value=delay_seconds,
                                   endpoint=cleanpath,
                                   method=request.method)

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

def clear_passwords_fields(data, schema):
    """
    Assumes "data" is organized according to schema and nullifies all password fields
    """
    if not data:
        return data
    if schema.get('format') == 'password' and not (isinstance(data, dict) and data.get('type') == 'cyberark_vault'):
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


def has_unchanged_password_value(value: object) -> bool:
    """
    Check if the current field value has an unchanged password or contains an inner unchanged password
    :param value: the value of the checked field or the dict to check inside of
    :return: True if the data contains an unchanged password
    """
    if value == UNCHANGED_MAGIC_FOR_GUI:
        return True
    if isinstance(value, dict):
        for key in value.keys():
            if has_unchanged_password_value(value[key]):
                return True
    return False


def filter_by_name(names, additional_filter=None):
    """
    Returns a filter that filters in objects by names
    :param additional_filter: optional - allows another filter to be made
    """
    base_names = {'name': {'$in': names}}
    if additional_filter:
        return {'$and': [base_names, additional_filter]}
    return base_names


if os.environ.get('HOT') == 'true':
    session = None


def _is_valid_node_hostname(hostname):
    """
    verify hostname is a valid lnx hostname pattern .
    """
    import re
    if len(hostname) > 255:
        return False
    if hostname[-1] == '.':
        hostname = hostname[:-1]
    # pylint: disable=C4001,W1401
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split('.'))


class GuiService(Triggerable, FeatureFlags, PluginBase, Configurable, APIMixin):
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

    def beautify_task_entry(self, task):
        """
        Extract needed fields to build task as represented in the Frontend
        """
        success_rate = '0 / 0'
        status = 'In Progress'
        result = task.get('result', {})
        if not isinstance(result, dict):
            result = {}
        try:
            if task.get('job_completed_state') == StoredJobStateCompletion.Successful.name:
                main_results = result.get(ACTIONS_MAIN_FIELD, {}).get('action', {}).get('results', {})

                main_successful_count = get_chunks_length(self.enforcement_tasks_action_results_id_lists,
                                                          main_results.get('successful_entities', 0))

                main_unsuccessful_count = get_chunks_length(self.enforcement_tasks_action_results_id_lists,
                                                            main_results.get('unsuccessful_entities', 0))
                success_rate = f'{main_successful_count} / {main_successful_count + main_unsuccessful_count}'
                status = 'Completed'

            return beautify_db_entry({
                '_id': task.get('_id'),
                'result.metadata.success_rate': success_rate,
                'post_json.report_name':
                    get_task_full_name(task.get('post_json', {}).get('report_name', ''),
                                       result.get('metadata', {}).get('pretty_id', '')),
                'status': status,
                f'result.{ACTIONS_MAIN_FIELD}.name': result.get('main', {}).get('name', ''),
                'result.metadata.trigger.view.name': result.get('metadata', {}).get('trigger', {}).get('view', {}).get(
                    'name', ''),
                'started_at': task.get('started_at', ''),
                'finished_at': task.get('finished_at', '')
            })
        except Exception as e:
            logger.exception(f'Invalid task {task.get("_id")}')
            return beautify_db_entry({
                '_id': task.get('_id', 'Invalid ID'),
                'status': 'Invalid'
            })

    def __add_defaults(self):
        self._add_default_roles()
        if self.__users_config_collection.find_one({}) is None:
            self.__users_config_collection.insert_one({
                'external_default_role': PREDEFINED_ROLE_RESTRICTED
            })

        current_user = self._users_collection.find_one({'user_name': 'admin'})
        if current_user is None:
            # User doesn't exist, this must be the installation process
            self._users_collection.update({'user_name': 'admin'}, self.DEFAULT_USER, upsert=True)

        alt_user = self._users_collection.find_one({'user_name': AXONIUS_USER_NAME})
        if alt_user is None:
            self._users_collection.update({'user_name': AXONIUS_USER_NAME}, self.ALTERNATIVE_USER, upsert=True)

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
        super().__init__(get_local_config_file(__file__), *args, requested_unique_plugin_name=GUI_PLUGIN_NAME, **kwargs)
        self.__all_sessions = {}
        self.wsgi_app.config['SESSION_COOKIE_SECURE'] = True
        self.wsgi_app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
        self.wsgi_app.session_interface = CachedSessionInterface(self.__all_sessions)

        self._users_collection = self._get_collection(USERS_COLLECTION)
        self.__roles_collection = self._get_collection(ROLES_COLLECTION)
        self.__users_config_collection = self._get_collection(USERS_CONFIG_COLLECTION)
        self.__dashboard_collection = self._get_collection(DASHBOARD_COLLECTION)
        self.__dashboard_spaces_collection = self._get_collection(DASHBOARD_SPACES_COLLECTION)

        self.reports_config_collection.create_index([('name', pymongo.HASHED)])

        try:
            self._users_collection.create_index([('user_name', pymongo.ASCENDING),
                                                 ('source', pymongo.ASCENDING)], unique=True)
        except pymongo.errors.DuplicateKeyError as e:
            logger.critical(f'Error creating user_name and source unique index: {e}')

        self.__add_defaults()

        # Start exec reports scheduler
        self.exec_report_locks = {}

        self._client_insertion_threadpool = LoggedThreadPoolExecutor(max_workers=10)  # Only for client insertion

        self._job_scheduler = LoggedBackgroundScheduler(executors={'default': ThreadPoolExecutorApscheduler(20)})
        current_exec_reports_setting = self._get_exec_report_settings(self.reports_config_collection)
        for current_exec_report_setting in current_exec_reports_setting:
            current_exec_report_setting['uuid'] = str(current_exec_report_setting['_id'])
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
        self._set_first_time_use()

        self._trigger('clear_dashboard_cache', blocking=False)

        if os.environ.get('HOT') == 'true':
            # pylint: disable=W0603
            global session
            user_db = self._users_collection.find_one({'user_name': 'admin'})
            user_db['permissions'] = deserialize_db_permissions(user_db['permissions'])
            session = {'user': user_db}

    @staticmethod
    def _is_hidden_user():
        return (session.get('user') or {}).get('user_name') == AXONIUS_USER_NAME

    def _delayed_initialization(self):
        self.__init_all_dashboards()

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
                    PREDEFINED_FIELD: True
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
            for name, data in config.items():
                if name == 'DEFAULT':
                    # ConfigParser always has a fake DEFAULT key, skip it
                    continue
                try:
                    self._insert_view(
                        self.gui_dbs.entity_query_views_db_map[entity_type],
                        name,
                        json.loads(data['view']),
                        data.get('description', ''),
                        json.loads(data.get('tags', '[]')))
                except Exception:
                    logger.exception(f'Error adding default view {name}')
        except Exception:
            logger.exception(f'Error adding default views')

    def add_default_dashboard_charts(self, default_dashboard_charts_ini_path):
        try:
            default_dashboards = []
            config = configparser.ConfigParser()
            config.read(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                     f'configs/{default_dashboard_charts_ini_path}')))
            default_space = self.__dashboard_spaces_collection.find_one({
                'type': 'default'
            })
            if not default_space:
                logger.error('This Axonius is missing the default Dashboard')
                return

            for name, data in config.items():
                if name == 'DEFAULT':
                    # ConfigParser always has a fake DEFAULT key, skip it
                    continue
                try:
                    if self.__dashboard_collection.find_one({'name': name}):
                        logger.info(f'dashboard with {name} already exists, not adding')
                        continue

                    dashboard_id = self._insert_dashboard_chart(dashboard_name=name,
                                                                dashboard_metric=data['metric'],
                                                                dashboard_view=data['view'],
                                                                dashboard_data=json.loads(data['config']),
                                                                hide_empty=bool(data.get('hide_empty', 0)),
                                                                space_id=default_space['_id'])
                    default_dashboards.append(str(dashboard_id))
                except Exception as e:
                    logger.exception(f'Error adding default dashboard chart {name}. Reason: {repr(e)}')
            if not default_space.get('panels_order'):
                # if panels_order attribute does not exist on space add it
                self.__dashboard_spaces_collection.update_one({
                    'type': 'default',
                    '_id': default_space['_id']
                }, {
                    '$set': {
                        'panels_order': default_dashboards
                    }
                })

        except Exception as e:
            logger.exception(f'Error adding default dashboard chart. Reason: {repr(e)}')

    def _insert_view(self, views_collection, name, mongo_view, description, tags):
        existed_view = views_collection.find_one({
            'name': {
                '$regex': name,
                '$options': 'i'
            },
            PREDEFINED_FIELD: True,
            UPDATED_BY_FIELD: '*'
        })
        find_query = {
            '_id': existed_view['_id']
        } if existed_view else {
            'name': name
        }
        current_time = datetime.now()
        views_collection.replace_one(find_query, {
            'name': name,
            'description': description,
            'tags': tags,
            'view': mongo_view,
            'query_type': 'saved',
            'timestamp': current_time,
            'user_id': '*',
            UPDATED_BY_FIELD: '*',
            LAST_UPDATED_FIELD: current_time,
            PREDEFINED_FIELD: True
        }, upsert=True)

    def _upsert_report_config(self, name, report_data, clear_generated_report) -> ObjectId:
        if clear_generated_report:
            report_data[report_consts.LAST_GENERATED_FIELD] = None

        result = self.reports_config_collection.find_one_and_update({
            'name': name,
            'archived': {
                '$ne': True
            }
        }, {
            '$set': report_data
        }, projection={
            '_id': True
        }, upsert=True, return_document=pymongo.ReturnDocument.AFTER)
        return result['_id']

    def _delete_report_configs(self, reports):
        reports_collection = self.reports_config_collection
        reports['ids'] = [ObjectId(id) for id in reports['ids']]
        ids = self.get_selected_ids(reports_collection, reports, {})
        for report_id in ids:
            existed_report = reports_collection.find_one_and_delete({
                'archived': {
                    '$ne': True
                },
                '_id': ObjectId(report_id)
            }, projection={
                'name': 1
            })

            if existed_report is None:
                logger.info(f'Report with id {report_id} does not exists')
                return return_error('Report does not exist')
            name = existed_report['name']
            exec_report_thread_id = EXEC_REPORT_THREAD_ID.format(name)
            exec_report_job = self._job_scheduler.get_job(exec_report_thread_id)
            if exec_report_job:
                exec_report_job.remove()
            logger.info(f'Deleted report {name} id: {report_id}')
        return ''

    def _insert_dashboard_chart(self, dashboard_name, dashboard_metric, dashboard_view, dashboard_data,
                                hide_empty=False, space_id=None):
        existed_dashboard_chart = self.__dashboard_collection.find_one({'name': dashboard_name})
        if existed_dashboard_chart is not None and existed_dashboard_chart.get('archived'):
            logger.info(f'Report {dashboard_name} was removed')
            return

        result = self.__dashboard_collection.replace_one({
            'name': dashboard_name
        }, {
            'name': dashboard_name,
            'metric': dashboard_metric,
            'view': dashboard_view,
            'config': dashboard_data,
            'hide_empty': hide_empty,
            'user_id': '*',
            'space': space_id
        }, upsert=True)
        return result.upserted_id

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
                'name': PREDEFINED_ROLE_ADMIN, PREDEFINED_FIELD: True, 'permissions': {
                    p.name: PermissionLevel.ReadWrite.name for p in PermissionType
                }
            })
        if self.__roles_collection.find_one({'name': PREDEFINED_ROLE_READONLY}) is None:
            # Read-only role doesn't exists - let's create it
            self.__roles_collection.insert_one({
                'name': PREDEFINED_ROLE_READONLY, PREDEFINED_FIELD: True, 'permissions': {
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
                'name': PREDEFINED_ROLE_RESTRICTED, PREDEFINED_FIELD: True, 'permissions': permissions
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
        self._trigger_remote_plugin(REPORTS_PLUGIN_NAME, 'run', blocking=False, data={
            'report_name': post_data['enforcement'],
            'input': {
                'entity': entity_type.name,
                'filter': escape_dict(mongo_filter),
                'selection': post_data['entities']
            }
        })
        return '', 200

    def _entity_views(self, method, entity_type: EntityType, limit, skip, mongo_filter, mongo_sort, query_type='saved'):
        """
        Save or fetch views over the entities db
        :return:
        """
        entity_views_collection = self.gui_dbs.entity_query_views_db_map[entity_type]
        if method == 'GET':
            mongo_filter['query_type'] = query_type
            return [beautify_db_entry(entry)
                    for entry
                    in get_views(entity_type, limit, skip, mongo_filter, mongo_sort)]

        if method == 'POST':
            view_data = self.get_request_data_as_object()
            if not view_data.get('name'):
                return return_error(f'Name is required in order to save a view', 400)
            if not view_data.get('view'):
                return return_error(f'View data is required in order to save one', 400)
            view_to_update = {
                'name': view_data['name'],
                'view': view_data['view'],
                'query_type': query_type,
            }
            if view_data.get(PREDEFINED_FIELD):
                view_to_update[PREDEFINED_FIELD] = view_data[PREDEFINED_FIELD]
            if not self._is_hidden_user():
                view_to_update[LAST_UPDATED_FIELD] = datetime.now()
                view_to_update[UPDATED_BY_FIELD] = get_connected_user_id()
                view_to_update['user_id'] = get_connected_user_id()
            update_result = entity_views_collection.find_one_and_update({
                'name': view_data['name']
            }, {
                '$set': view_to_update
            }, upsert=True, return_document=pymongo.ReturnDocument.AFTER)

            return str(update_result['_id'])

        if method == 'DELETE':
            selection = self.get_request_data_as_object()
            selection['ids'] = [ObjectId(i) for i in selection['ids']]
            query_ids = self.get_selected_ids(entity_views_collection, selection, mongo_filter)
            entity_views_collection.update_many({
                '_id': {
                    '$in': query_ids
                }
            }, {
                '$set': {
                    'archived': True
                }
            })
            return ''

    def _entity_views_update(self, entity_type: EntityType, query_id):
        view_data = self.get_request_data_as_object()
        if not view_data.get('name'):
            return return_error(f'Name is required in order to save a view', 400)
        view_set_data = {
            'name': view_data['name'],
            'view': view_data['view'],
        }
        if not self._is_hidden_user():
            view_set_data[LAST_UPDATED_FIELD] = datetime.now()
            view_set_data[UPDATED_BY_FIELD] = get_connected_user_id()
        self.gui_dbs.entity_query_views_db_map[entity_type].update_one({
            '_id': ObjectId(query_id)
        }, {
            '$set': view_set_data
        })

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
            add_labels_to_entities(namespace,
                                   internal_axon_ids,
                                   entities_and_labels['labels'],
                                   request.method == 'DELETE')
        except Exception as e:
            logger.exception(f'Tagging did not complete')
            return return_error(f'Tagging did not complete. First error: {e}', 400)

        return str(len(internal_axon_ids)), 200

    def __delete_entities_by_internal_axon_id(self, entity_type: EntityType, entities_selection, mongo_filter):
        entities = self._entity_db_map[entity_type].find({
            'internal_axon_id': {
                '$in': self.get_selected_entities(entity_type, entities_selection, mongo_filter)
            }
        }, projection={
            f'adapters.{PLUGIN_UNIQUE_NAME}': 1,
            f'adapters.data.id': 1
        })
        raw_col = self._raw_adapter_entity_db_map[entity_type]
        with ThreadPool(15) as pool:
            def delete_raw(axonius_entity):
                for adapter in axonius_entity['adapters']:
                    raw_col.delete_one({
                        PLUGIN_UNIQUE_NAME: adapter[PLUGIN_UNIQUE_NAME],
                        'id': adapter['data']['id']
                    })
            pool.map(delete_raw, entities)
        self._entity_db_map[entity_type].delete_many({
            'internal_axon_id': {
                '$in': self.get_selected_entities(entity_type, entities_selection, mongo_filter)
            }
        })
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
        if self._is_hidden_user():
            return

        view_filter = request.args.get('filter')
        if request.args.get('is_refresh') != '1':
            log_metric(logger, Query.QUERY_GUI, view_filter)
            history = request.args.get('history')
            if history:
                log_metric(logger, Query.QUERY_HISTORY, str(history))

        if view_filter and not skip:
            # getting the original filter text on purpose - we want to pass it
            mongo_sort = {'desc': -1, 'field': ''}
            if sort:
                field, desc = next(iter(sort.items()))
                mongo_sort = {'desc': int(desc), 'field': field}
            self.gui_dbs.entity_query_views_db_map[entity_type].replace_one(
                {'name': {'$exists': False}, 'view.query.filter': view_filter},
                {
                    'view': {
                        'page': 0,
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

    def _entity_custom_data(self, entity_type: EntityType, mongo_filter=None):
        """
        Adds misc adapter data to the data as given in the request
        POST data:
        {
            'selection': {
                'ids': list of ids, 'include': true / false
            },
            'data': {...}
        }
        For each field to set, search for as a title of an existing field.
        If found, set matching value to that field.
        Otherwise, create a new field with the name as a title and 'custom_<name>' as the field name.

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
            if not isinstance(v, (str, int, bool, float)):
                errors[k] = f'{k} is of type {type(v)} which is not allowed'
            try:
                if k.startswith('custom_'):
                    entity_to_add.set_static_field(k, Field(type(v), k))
                elif not entity_to_add.set_field_by_title(k, v):
                    # Canonize field name with title as received
                    field_name = f'custom_{"_".join(k.split(" ")).lower()}'
                    entity_to_add.declare_new_field(field_name, Field(type(v), k))
                    setattr(entity_to_add, field_name, v)
            except Exception:
                errors[k] = f'Value {v} not compatible with field {k}'
                logger.exception(errors[k])

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
        return '', 200

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
            'user_id': get_connected_user_id()
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

    ##############################
    # Getting Started Checklist #
    ##############################

    @gui_add_rule_logged_in('getting_started', methods=['GET'],
                            required_permissions={Permission(PermissionType.Settings,
                                                             PermissionLevel.ReadWrite)})
    def get_getting_started_data(self):
        """
        Fetch the Getting Started checklist state from db
        """
        data = self._get_collection('getting_started').find_one({})
        return jsonify(data)

    @gui_add_rule_logged_in('getting_started/completion', methods=['POST'])
    def getting_started_set_milestone_completion(self):
        """
        Check an item in the Getting Started checklist as done.
        """
        milestone_name = self.get_request_data_as_object().get('milestoneName', '')

        result = self._get_collection('getting_started').find_one_and_update({}, {
            '$set': {
                'milestones.$[element].completed': True,
                'milestones.$[element].user_id': gui_helpers.get_connected_user_id(),
                'milestones.$[element].completionDate': datetime.now()
            }
        }, array_filters=[{'element.name': milestone_name}], return_document=pymongo.ReturnDocument.AFTER)

        milestones_len = len(result['milestones'])
        progress = len([item for item in result['milestones'] if item['completed']])
        progress_formatted_str = f'{progress} of {milestones_len}'

        details = [{'name': item.get('name', 'name not found'), 'completed': item.get('completed', False)} for item
                   in result.get('milestones', []) if item]

        log_metric(logger, GettingStartedMetric.COMPLETION_STATE,
                   metric_value=milestone_name,
                   details=details,
                   progress=progress_formatted_str)
        return ''

    @gui_add_rule_logged_in('getting_started/settings', methods=['POST'],
                            required_permissions={Permission(PermissionType.Settings,
                                                             PermissionLevel.ReadWrite)})
    def getting_started_update_settings(self):
        """
        Update the value of the checklist autoOpen setting.
        """
        settings = self.get_request_data_as_object().get('settings', {})
        auto_open = settings.get('autoOpen', False)

        self._get_collection('getting_started').update_one({}, {
            '$set': {
                'settings.autoOpen': auto_open
            }
        })

        log_metric(logger, GettingStartedMetric.AUTO_OPEN_SETTING, metric_value=auto_open)

        return ''

    ##########
    # DEVICE #
    ##########
    @gui_helpers.historical()
    @gui_helpers.paginated()
    @gui_helpers.filtered_entities()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_add_rule_logged_in('devices', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             ReadOnlyJustForGet)})
    def get_devices(self, limit, skip, mongo_filter, mongo_sort, mongo_projection, history: datetime):
        if request.method == 'DELETE':
            return self.__delete_entities_by_internal_axon_id(
                EntityType.Devices, self.get_request_data_as_object(), mongo_filter)
        self._save_query_to_history(EntityType.Devices, mongo_filter, skip, limit, mongo_sort, mongo_projection)
        iterable = get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection,
                                EntityType.Devices,
                                default_sort=self._system_settings.get('defaultSort'),
                                history_date=history,
                                include_details=True)
        return iterator_jsonify(iterable)

    @gui_helpers.historical()
    @gui_helpers.filtered_entities()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_helpers.filtered_fields()
    @gui_add_rule_logged_in('devices/csv', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadOnly)})
    def get_devices_csv(self, mongo_filter, mongo_sort, mongo_projection, history: datetime, field_filters):
        return get_csv_from_heavy_lifting_plugin(mongo_filter,
                                                 mongo_sort,
                                                 mongo_projection,
                                                 history,
                                                 EntityType.Devices,
                                                 self._system_settings.get('defaultSort'),
                                                 field_filters)

    @gui_helpers.filtered_entities()
    @gui_helpers.historical()
    @gui_add_rule_logged_in('devices/count', methods=['GET', 'POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadOnly)})
    def get_devices_count(self, mongo_filter, history: datetime):
        content = self.get_request_data_as_object()
        quick = content.get('quick') or request.args.get('quick')
        quick = quick == 'True'
        return str(self._get_entity_count(EntityType.Devices, mongo_filter, history, quick))

    @gui_add_rule_logged_in('devices/fields',
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadOnly)})
    def device_fields(self):
        return jsonify(gui_helpers.entity_fields(EntityType.Devices))

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_add_rule_logged_in('devices/views/<query_type>', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Devices, ReadOnlyJustForGet)})
    def device_views(self, limit, skip, mongo_filter, mongo_sort, query_type):
        """
        Save or fetch views over the devices db
        :return:
        """
        return jsonify(
            self._entity_views(request.method, EntityType.Devices, limit, skip, mongo_filter, mongo_sort, query_type))

    @gui_add_rule_logged_in('devices/views/saved/<query_id>', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadWrite)})
    def device_views_update(self, query_id):
        """
        Update name of an existing view
        :return:
        """
        self._entity_views_update(EntityType.Devices, query_id)
        return ''

    @gui_helpers.filtered()
    @gui_add_rule_logged_in('devices/views/<query_type>/count', methods=['GET'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadOnly)})
    def get_devices_views_count(self, mongo_filter, query_type):
        content = self.get_request_data_as_object()
        quick = content.get('quick') or request.args.get('quick')
        quick = quick == 'True'
        mongo_filter['query_type'] = query_type
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

    @gui_helpers.historical()
    @gui_add_rule_logged_in('devices/<device_id>', methods=['GET'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadOnly)})
    def device_generic(self, device_id, history: datetime):
        res = get_entity_data(EntityType.Devices, device_id, history)
        if isinstance(res, dict):
            return jsonify(res)
        return res

    @gui_helpers.historical()
    @gui_helpers.sorted_endpoint()
    @gui_add_rule_logged_in('devices/<device_id>/<field_name>/csv', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadOnly)})
    def device_generic_field_csv(self, device_id, field_name, mongo_sort, history: datetime):
        """
        Create a csv file for a specific field of a specific device

        :param device_id:   internal_axon_id of the Device to create csv for
        :param field_name:  Field of the Device, containing table data
        :param mongo_sort:  How to sort the table data of the field
        :param history:     Fetch the Device according to this past date
        :return:            Response containing csv data, that can be downloaded into a csv file
        """
        csv_string = entity_data_field_csv(EntityType.Devices, device_id, field_name, mongo_sort, history)
        output = make_response((codecs.BOM_UTF8 * 2) + csv_string.getvalue().encode('utf-8'))
        timestamp = datetime.now().strftime('%d%m%Y-%H%M%S')
        field_name = field_name.split('.')[-1]
        output.headers['Content-Disposition'] = f'attachment; filename=axonius-data_{field_name}_{timestamp}.csv'
        output.headers['Content-type'] = 'text/csv'
        return output

    @gui_add_rule_logged_in('devices/<device_id>/tasks', methods=['GET'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadOnly)})
    def device_tasks(self, device_id):
        return jsonify(entity_tasks_actions(device_id))

    @gui_add_rule_logged_in('devices/<device_id>/notes', methods=['PUT', 'DELETE'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadWrite)})
    def device_notes(self, device_id):
        return entity_notes(EntityType.Devices, device_id, self.get_request_data_as_object())

    @gui_helpers.schema_fields()
    @gui_helpers.sorted_endpoint()
    @gui_add_rule_logged_in('devices/<device_id>/tasks/csv', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadOnly)})
    def device_tasks_csv(self, device_id, mongo_sort, schema_fields):
        """
        Create a csv file for a enforcement tasks of a specific device

        :param device_id:   internal_axon_id of the Device tasks to create csv for
        :param mongo_sort:  the sort of the csv
        :param schema_fields:   the fields to show
        :return:            Response containing csv data, that can be downloaded into a csv file
        """
        csv_string = entity_tasks_actions_csv(device_id, schema_fields, mongo_sort)
        output = make_response(csv_string.getvalue().encode('utf-8'))
        timestamp = datetime.now().strftime('%d%m%Y-%H%M%S')
        output.headers['Content-Disposition'] = f'attachment; filename=axonius-data_enforcement_tasks_{timestamp}.csv'
        output.headers['Content-type'] = 'text/csv'
        return output

    @gui_add_rule_logged_in('devices/<device_id>/notes/<note_id>', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadWrite)})
    def device_notes_update(self, device_id, note_id):
        return entity_notes_update(EntityType.Devices, device_id, note_id, self.get_request_data_as_object()['note'])

    @gui_helpers.filtered_entities()
    @gui_add_rule_logged_in('devices/custom', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadWrite)})
    def devices_custom_data(self, mongo_filter):
        """
        See self._entity_custom_data
        """
        return self._entity_custom_data(EntityType.Devices, mongo_filter)

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

    @gui_helpers.historical()
    @gui_helpers.paginated()
    @gui_helpers.filtered_entities()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_add_rule_logged_in('users', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Users,
                                                             ReadOnlyJustForGet)})
    def get_users(self, limit, skip, mongo_filter, mongo_sort, mongo_projection, history: datetime):
        if request.method == 'DELETE':
            return self.__delete_entities_by_internal_axon_id(
                EntityType.Users, self.get_request_data_as_object(), mongo_filter)
        self._save_query_to_history(EntityType.Users, mongo_filter, skip, limit, mongo_sort, mongo_projection)
        iterable = get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection,
                                EntityType.Users,
                                default_sort=self._system_settings['defaultSort'],
                                history_date=history,
                                include_details=True)
        return iterator_jsonify(iterable)

    @gui_helpers.historical()
    @gui_helpers.filtered_entities()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_helpers.filtered_fields()
    @gui_add_rule_logged_in('users/csv', methods=['POST'],
                            required_permissions={Permission(PermissionType.Users,
                                                             PermissionLevel.ReadOnly)})
    def get_users_csv(self, mongo_filter, mongo_sort, mongo_projection, history: datetime, field_filters):
        # Deleting image from the CSV (we dont need this base64 blob in the csv)
        if 'specific_data.data.image' in mongo_projection:
            del mongo_projection['specific_data.data.image']

        return get_csv_from_heavy_lifting_plugin(mongo_filter,
                                                 mongo_sort,
                                                 mongo_projection,
                                                 history,
                                                 EntityType.Users,
                                                 self._system_settings.get('defaultSort'),
                                                 field_filters)

    @gui_helpers.historical()
    @gui_helpers.filtered_entities()
    @gui_add_rule_logged_in('users/count', methods=['GET', 'POST'],
                            required_permissions={Permission(PermissionType.Users,
                                                             PermissionLevel.ReadOnly)})
    def get_users_count(self, mongo_filter, history: datetime):
        content = self.get_request_data_as_object()
        quick = content.get('quick') or request.args.get('quick')
        quick = quick == 'True'
        return self._get_entity_count(EntityType.Users, mongo_filter, history, quick)

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
    @gui_helpers.sorted_endpoint()
    @gui_add_rule_logged_in('users/views/<query_type>', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Users, ReadOnlyJustForGet)})
    def user_views(self, limit, skip, mongo_filter, mongo_sort, query_type):
        return jsonify(
            self._entity_views(request.method, EntityType.Users, limit, skip, mongo_filter, mongo_sort, query_type))

    @gui_add_rule_logged_in('users/views/saved/<query_id>', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadWrite)})
    def users_views_update(self, query_id):
        """
        Update name of an existing view
        :return:
        """
        self._entity_views_update(EntityType.Users, query_id)
        return ''

    @gui_helpers.filtered()
    @gui_add_rule_logged_in('users/views/<query_type>/count', methods=['GET'],
                            required_permissions={Permission(PermissionType.Users, PermissionLevel.ReadOnly)})
    def get_users_views_count(self, mongo_filter, query_type):
        content = self.get_request_data_as_object()
        quick = content.get('quick') or request.args.get('quick')
        quick = quick == 'True'
        mongo_filter['query_type'] = query_type
        return str(get_views_count(EntityType.Users, mongo_filter, quick=quick))

    @gui_helpers.filtered_entities()
    @gui_add_rule_logged_in('users/labels', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Users,
                                                             ReadOnlyJustForGet)})
    def user_labels(self, mongo_filter):
        return self._entity_labels(self.users_db, self.users, mongo_filter)

    @gui_helpers.historical()
    @gui_add_rule_logged_in('users/<user_id>', methods=['GET'],
                            required_permissions={Permission(PermissionType.Users, PermissionLevel.ReadOnly)})
    def user_generic(self, user_id, history: datetime):
        res = jsonify(get_entity_data(EntityType.Users, user_id, history))
        if isinstance(res, dict):
            return jsonify(res)
        return res

    @gui_helpers.historical()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.filtered_fields()
    @gui_add_rule_logged_in('users/<user_id>/<field_name>/csv', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadOnly)})
    def user_generic_field_csv(self, user_id, field_name, mongo_sort, history: datetime, field_filters):
        """
        Create a csv file for a specific field of a specific entity

        :param user_id:     internal_axon_id of User to create csv for
        :param field_name:  Field of the User, containing table data
        :param mongo_sort:  How to sort the table data of the field
        :param history:     Fetch the User according to this past date
        :return:            Response containing csv data, that can be downloaded into a csv file
        """
        csv_string = entity_data_field_csv(EntityType.Users, user_id, field_name, mongo_sort, history, field_filters)
        output = make_response(csv_string.getvalue().encode('utf-8'))
        timestamp = datetime.now().strftime('%d%m%Y-%H%M%S')
        field_name = field_name.split('.')[-1]
        output.headers['Content-Disposition'] = f'attachment; filename=axonius-data_{field_name}_{timestamp}.csv'
        output.headers['Content-type'] = 'text/csv'
        return output

    @gui_add_rule_logged_in('users/<user_id>/tasks', methods=['GET'],
                            required_permissions={Permission(PermissionType.Users, PermissionLevel.ReadOnly)})
    def user_tasks(self, user_id):
        return jsonify(entity_tasks_actions(user_id))

    @gui_helpers.schema_fields()
    @gui_helpers.sorted_endpoint()
    @gui_add_rule_logged_in('users/<user_id>/tasks/csv', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadOnly)})
    def user_tasks_csv(self, user_id, mongo_sort, schema_fields):
        """
        Create a csv file for a enforcement tasks of a specific device

        :param user_id:   internal_axon_id of the User tasks to create csv for
        :param mongo_sort:  the sort of the csv
        :param schema_fields:   the fields to show
        :return:            Response containing csv data, that can be downloaded into a csv file
        """
        csv_string = entity_tasks_actions_csv(user_id, schema_fields, mongo_sort)
        output = make_response(csv_string.getvalue().encode('utf-8'))
        timestamp = datetime.now().strftime('%d%m%Y-%H%M%S')
        output.headers['Content-Disposition'] = f'attachment; filename=axonius-data_enforcement_tasks_{timestamp}.csv'
        output.headers['Content-type'] = 'text/csv'
        return output

    @gui_add_rule_logged_in('users/<user_id>/notes', methods=['PUT', 'DELETE'],
                            required_permissions={Permission(PermissionType.Users, PermissionLevel.ReadWrite)})
    def user_notes(self, user_id):
        return entity_notes(EntityType.Users, user_id, self.get_request_data_as_object())

    @gui_add_rule_logged_in('users/<user_id>/notes/<note_id>', methods=['POST'],
                            required_permissions={Permission(PermissionType.Users, PermissionLevel.ReadWrite)})
    def user_notes_update(self, user_id, note_id):
        return entity_notes_update(EntityType.Users, user_id, note_id, self.get_request_data_as_object()['note'])

    @gui_helpers.filtered_entities()
    @gui_add_rule_logged_in('users/custom', methods=['POST'],
                            required_permissions={Permission(PermissionType.Users,
                                                             PermissionLevel.ReadWrite)})
    def users_custom_data(self, mongo_filter):
        """
        See self._entity_custom_data
        """
        return self._entity_custom_data(EntityType.Users, mongo_filter)

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

    @gui_add_rule_logged_in('adapters/hint_raise/<plugin_name>',
                            required_permissions={Permission(PermissionType.Adapters,
                                                             PermissionLevel.ReadOnly)},
                            methods=['POST'])
    def hint_raise_adapter(self, plugin_name: str):
        """
        Raises all instances of the given plugin name
        """
        plugins_to_raise = self.core_configs_collection.find({
            PLUGIN_NAME: plugin_name,
            'plugin_type': adapter_consts.ADAPTER_PLUGIN_TYPE,
            'status': {
                '$ne': 'up'
            }
        }, projection={
            PLUGIN_UNIQUE_NAME: True
        })
        for plugin in plugins_to_raise:
            unique_name = plugin[PLUGIN_UNIQUE_NAME]
            # 'lives_left' is a variable that accounts for the amount of minutes of grace
            # for the adapter until it shuts down again
            self._get_collection('lives_left', db_name=unique_name).update_one(
                {
                    'lives_left': {
                        '$exists': True
                    }
                },
                {
                    '$set': {
                        'lives_left': 5
                    }
                }, upsert=True)
            run_and_forget(lambda: self.request_remote_plugin('version', plugin_unique_name=unique_name))
        return ''

    @rev_cached(ttl=10, remove_from_cache_ttl=60)
    def _adapters(self):
        """
        Get all adapters from the core
        :return:
        """
        db_connection = self._get_db_connection()
        adapters_from_db = db_connection[CORE_UNIQUE_NAME]['configs'].find({
            'plugin_type': adapter_consts.ADAPTER_PLUGIN_TYPE,
            'hidden': {
                '$ne': True
            }
        }).sort([(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
        adapters_to_return = []
        for adapter in adapters_from_db:
            adapter_name = adapter[PLUGIN_UNIQUE_NAME]

            schema = self._get_plugin_schemas(db_connection, adapter_name).get('clients')
            nodes_metadata_collection = db_connection['core']['nodes_metadata']

            node_name = nodes_metadata_collection.find_one({
                NODE_ID: adapter[NODE_ID]
            })

            # Skip Deactivated nodes.
            if node_name and node_name.get('status', ACTIVATED_NODE_STATUS) == DEACTIVATED_NODE_STATUS:
                continue

            if not schema:
                # there might be a race - in the split second that the adapter is up
                # but it still hasn't written it's schema
                continue

            clients = [beautify_db_entry(client)
                       for client
                       in db_connection[adapter_name]['clients'].find()
                       .sort([('_id', pymongo.DESCENDING)])]
            for client in clients:
                self._decrypt_client_config(client['client_config'])
                client['client_config'] = clear_passwords_fields(client['client_config'], schema)
                client[NODE_ID] = adapter[NODE_ID]
                client['adapter'] = adapter[PLUGIN_NAME]
            status = ''
            if len(clients):
                status = 'success' if all(client.get('status') == 'success' for client in clients) \
                    else 'warning'

            node_name = '' if node_name is None else node_name.get(NODE_NAME)

            adapters_to_return.append({
                'plugin_name': adapter['plugin_name'],
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
        response = self.request_remote_plugin('client_test', adapter_unique_name, method='post',
                                              json=client_to_test)
        if response.status_code != 200:
            logger.error(f'Error in client adding: {response.status_code}, {response.text}')
        return response.text, response.status_code

    def _query_client_for_devices(self, adapter_unique_name, clients):
        if clients is None:
            return return_error('Invalid client', 400)
        # adding client to specific adapter
        response = self.request_remote_plugin('clients', adapter_unique_name, 'put', json=clients,
                                              raise_on_network_error=True)
        self._adapters.clean_cache()
        if response.status_code == 200:
            self._client_insertion_threadpool.submit(self._fetch_after_clients_thread, adapter_unique_name,
                                                     response.json()['client_id'], clients)
        else:
            logger.error(f'Error in client adding: {response.status_code}, {response.text}')
        return response.text, response.status_code

    def validate_and_fill_unchanged_passwords_fields(self,
                                                     adapter_unique_name: str,
                                                     client_id: str,
                                                     data: object,
                                                     data_for_unchanged_passwords: dict) -> bool:
        """
        Check if there is an unchanged password with a changed client_id
        :param adapter_unique_name: the adapter name
        :param client_id: the old client_id (from the db)
        :param data: the data to change
        :param data_for_unchanged_passwords: the data from the db for filling the unchanged passwords
        :return: True if the data is valid False if not
        """
        if not has_unchanged_password_value(data):
            return True
        if data_for_unchanged_passwords:
            refill_passwords_fields(data, data_for_unchanged_passwords)
        get_client_id_response = self.request_remote_plugin('get_client_id', adapter_unique_name, 'post', json=data,
                                                            raise_on_network_error=True)
        if not get_client_id_response or not get_client_id_response.text:
            return False
        # return True if the new client id equals to client_id in the db
        return get_client_id_response.text == client_id

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
        :param adapter_name: the adapter to refer to
        :return:
        """
        clients = request.get_json(silent=True)
        node_id = clients.pop('instanceName', self.node_id)

        adapter_unique_name = self.request_remote_plugin(
            f'find_plugin_unique_name/nodes/{node_id}/plugins/{adapter_name}').json().get('plugin_unique_name')
        logger.info(f'Got adapter unique name {adapter_unique_name}')
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
        :param adapter_name: the adapter to refer to
        :param client_id: UUID of client to delete if DELETE is used
        :return:
        """
        data = self.get_request_data_as_object()
        node_id = data.pop('instanceName', self.node_id)
        old_node_id = data.pop('oldInstanceName', None)
        adapter_unique_name = self.request_remote_plugin(f'find_plugin_unique_name/nodes/{old_node_id or node_id}/'
                                                         f'plugins/{adapter_name}').json().get(PLUGIN_UNIQUE_NAME)
        if request.method == 'DELETE':
            if request.args.get('deleteEntities', False):
                self.delete_client_data(adapter_name, adapter_unique_name, client_id)

        client_from_db = self._get_collection('clients', adapter_unique_name).find_one({'_id': ObjectId(client_id)})
        if not client_from_db:
            return return_error('Server is already gone, please try again after refreshing the page')
        self._decrypt_client_config(client_from_db['client_config'])
        if request.method == 'PUT' and \
                not self.validate_and_fill_unchanged_passwords_fields(adapter_unique_name,
                                                                      client_from_db['client_id'],
                                                                      data,
                                                                      client_from_db['client_config']):
            return return_error('Failed to save connection details. '
                                'Changing connection details requires re-entering credentials', 400)
        self.request_remote_plugin('clients/' + client_id, adapter_unique_name, method='delete')
        if request.method == 'PUT':
            if old_node_id != node_id:
                url = f'find_plugin_unique_name/nodes/{node_id}/plugins/{adapter_name}'
                adapter_unique_name = self.request_remote_plugin(url).json().get('plugin_unique_name')

            self._adapters.clean_cache()
            return self._query_client_for_devices(adapter_unique_name, data)

        self._adapters.clean_cache()
        return '', 200

    def delete_client_data(self, plugin_name, plugin_unique_name, client_id):
        client_from_db = self._get_collection('clients', plugin_unique_name).find_one({'_id': ObjectId(client_id)})
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
            sort.append((LAST_UPDATED_FIELD, pymongo.DESCENDING))

        def beautify_report(report):
            beautify_object = {
                '_id': report['_id'],
                'name': report['name'],
                LAST_UPDATED_FIELD: report.get(LAST_UPDATED_FIELD),
                UPDATED_BY_FIELD: report.get(UPDATED_BY_FIELD),
                report_consts.LAST_GENERATED_FIELD: report.get(report_consts.LAST_GENERATED_FIELD)
            }
            if report.get('add_scheduling'):
                beautify_object['period'] = report.get('period').capitalize()
                if report.get('mail_properties'):
                    beautify_object['mailSubject'] = report.get('mail_properties').get('mailSubject')
            return beautify_db_entry(beautify_object)

        reports_collection = self.reports_config_collection
        result = [beautify_report(enforcement) for enforcement in reports_collection.find(
            mongo_filter).sort(sort).skip(skip).limit(limit)]
        return result

    def _generate_and_schedule_report(self, report):
        run_and_forget(lambda: self._generate_and_save_report(report))
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
            report_name = report_to_add['name'] = report_to_add['name'].strip()
            report = reports_collection.find_one({
                'name': report_name
            })
            if report:
                return 'Report name already taken by another report', 400

            if not self._is_hidden_user():
                report_to_add['user_id'] = get_connected_user_id()
                report_to_add[LAST_UPDATED_FIELD] = datetime.now()
                report_to_add[UPDATED_BY_FIELD] = get_connected_user_id()
            upsert_result = self._upsert_report_config(report_to_add['name'], report_to_add, False)
            report_to_add['uuid'] = str(upsert_result)
            self._generate_and_schedule_report(report_to_add)
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
            }, {
                LAST_UPDATED_FIELD: 0,
                UPDATED_BY_FIELD: 0,
                'user_id': 0
            })
            if not report:
                return return_error(f'Report with id {report_id} was not found', 400)

            return jsonify(beautify_db_entry(report))

        # Handle remaining request - POST
        report_to_update = request.get_json(silent=True)
        if not self._is_hidden_user():
            report_to_update[LAST_UPDATED_FIELD] = datetime.now()
            report_to_update[UPDATED_BY_FIELD] = get_connected_user_id()

        self._upsert_report_config(report_to_update['name'], report_to_update, True)
        self._generate_and_schedule_report(report_to_update)

        return jsonify(report_to_update), 200

    ################
    # ENFORCEMENTS #
    ################

    def get_enforcements(self, limit, mongo_filter, mongo_sort, skip):
        sort = [(LAST_UPDATED_FIELD, pymongo.DESCENDING)] if not mongo_sort else list(mongo_sort.items())

        def beautify_enforcement(enforcement):
            actions = enforcement[ACTIONS_FIELD]
            trigger = enforcement[TRIGGERS_FIELD][0] if enforcement[TRIGGERS_FIELD] else None
            return beautify_db_entry({
                '_id': enforcement['_id'], 'name': enforcement['name'],
                f'{ACTIONS_FIELD}.{ACTIONS_MAIN_FIELD}': actions[ACTIONS_MAIN_FIELD],
                f'{TRIGGERS_FIELD}.view.name': trigger['view']['name'] if trigger else '',
                f'{TRIGGERS_FIELD}.{LAST_TRIGGERED_FIELD}': trigger.get(LAST_TRIGGERED_FIELD, '') if trigger else '',
                f'{TRIGGERS_FIELD}.{TIMES_TRIGGERED_FIELD}': trigger.get(TIMES_TRIGGERED_FIELD) if trigger else None,
                LAST_UPDATED_FIELD: enforcement.get(LAST_UPDATED_FIELD),
                UPDATED_BY_FIELD: enforcement.get(UPDATED_BY_FIELD)
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
            self._encrypt_client_config(action.get(ACTION_FIELD, {}).get(ACTION_CONFIG_FIELD, {}))
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
        if not self._is_hidden_user():
            enforcement_to_add['user_id'] = str(get_connected_user_id())
            enforcement_to_add[LAST_UPDATED_FIELD] = datetime.now()
            enforcement_to_add[UPDATED_BY_FIELD] = get_connected_user_id()

        if enforcement_to_add[TRIGGERS_FIELD] and not enforcement_to_add[TRIGGERS_FIELD][0].get('name'):
            enforcement_to_add[TRIGGERS_FIELD][0]['name'] = enforcement_to_add['name']
        response = self.request_remote_plugin('reports', REPORTS_PLUGIN_NAME, method='put', json=enforcement_to_add,
                                              raise_on_network_error=True)
        return response.text, response.status_code

    def delete_enforcement(self, enforcement_selection):
        # Since other method types cause the function to return - here we have DELETE request
        if enforcement_selection is None or (not enforcement_selection.get('ids')
                                             and enforcement_selection.get('include')):
            logger.error('No enforcement provided to be deleted')
            return ''

        response = self.request_remote_plugin('reports', REPORTS_PLUGIN_NAME, method='DELETE',
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
            return self.put_enforcement({
                'name': enforcement_to_add['name'],
                ACTIONS_FIELD: enforcement_to_add[ACTIONS_FIELD],
                TRIGGERS_FIELD: enforcement_to_add[TRIGGERS_FIELD]
            })

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
                self._decrypt_client_config(saved_action.get(ACTION_FIELD, {}).get(ACTION_CONFIG_FIELD, {}))
                # fixing password to be 'unchanged'
                action_type = saved_action['action']['action_name']
                schema = self._get_actions_from_reports_plugin()[action_type]['schema']
                saved_action['action']['config'] = clear_passwords_fields(saved_action['action']['config'], schema)
                return beautify_db_entry(saved_action)

            enforcement = self.enforcements_collection.find_one({
                '_id': ObjectId(enforcement_id)
            }, {
                'name': 1,
                ACTIONS_FIELD: 1,
                TRIGGERS_FIELD: 1
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
            return jsonify(beautify_db_entry(enforcement))

        # Handle remaining request - POST
        enforcement_data = request.get_json(silent=True)
        enforcement_to_update = {
            'name': enforcement_data['name'],
            ACTIONS_FIELD: enforcement_data[ACTIONS_FIELD],
            TRIGGERS_FIELD: enforcement_data[TRIGGERS_FIELD]
        }
        if not self._is_hidden_user():
            enforcement_to_update[LAST_UPDATED_FIELD] = datetime.now()
            enforcement_to_update[UPDATED_BY_FIELD] = get_connected_user_id()

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
            self._decrypt_client_config(action_from_db.get(ACTION_FIELD, {}).get(ACTION_CONFIG_FIELD, {}))
            logger.debug(action_from_db)
            logger.debug(corresponding_user_action)
            if not corresponding_user_action:
                continue
            corresponding_user_action['action']['config'] = refill_passwords_fields(
                corresponding_user_action['action']['config'],
                action_from_db['action']['config'])

        self.enforcements_saved_actions_collection.delete_many(all_actions_query)

        self.__process_enforcement_actions(enforcement_to_update[ACTIONS_FIELD])
        response = self.request_remote_plugin(f'reports/{enforcement_id}', REPORTS_PLUGIN_NAME, method='post',
                                              json=enforcement_to_update)
        if response is None:
            return return_error('No response whether enforcement was updated')

        for trigger in enforcement_to_update['triggers']:
            trigger_res = self.request_remote_plugin(f'reports/{enforcement_id}/{trigger.get("id", trigger["name"])}',
                                                     REPORTS_PLUGIN_NAME, method='post', json=trigger)
            if trigger_res is None or trigger_res.status_code == 500:
                logger.error(f'Failed to save trigger {trigger["name"]}')

        return response.text, response.status_code

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_add_rule_logged_in('enforcements/<enforcement_id>/tasks', methods=['GET'],
                            required_permissions={Permission(PermissionType.Enforcements, PermissionLevel.ReadOnly)})
    def tasks_by_enforcement_id(self, enforcement_id, limit, skip, mongo_filter, mongo_sort):
        enforcement = self.enforcements_collection.find_one({
            '_id': ObjectId(enforcement_id)
        })
        if not enforcement:
            return return_error(f'Enforcement with id {enforcement_id} was not found', 400)

        if mongo_sort.get('status'):
            mongo_sort['job_completed_state'] = -1 * mongo_sort['status']
            del mongo_sort['status']
        sort = [('finished_at', pymongo.DESCENDING)] if not mongo_sort else list(mongo_sort.items())
        return jsonify([self.beautify_task_entry(x) for x in self.enforcement_tasks_runs_collection.find(
            self.__tasks_query(mongo_filter, enforcement['name'])).sort(sort).skip(skip).limit(limit)])

    @gui_helpers.filtered()
    @gui_add_rule_logged_in('enforcements/<enforcement_id>/tasks/count', methods=['GET'],
                            required_permissions={Permission(PermissionType.Enforcements, PermissionLevel.ReadOnly)})
    def tasks_by_enforcement_id_count(self, enforcement_id, mongo_filter):
        enforcement = self.enforcements_collection.find_one({
            '_id': ObjectId(enforcement_id)
        })
        if not enforcement:
            return return_error(f'Enforcement with id {enforcement_id} was not found', 400)

        return jsonify(self.enforcement_tasks_runs_collection.count_documents(
            self.__tasks_query(mongo_filter, enforcement['name'])
        ))

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
        response = self._trigger_remote_plugin(REPORTS_PLUGIN_NAME, 'run', data={
            'report_name': enforcement['name'],
            'configuration_name': enforcement[TRIGGERS_FIELD][0]['name'],
            'manual': True
        }, priority=True)
        return response.text, response.status_code

    @add_rule('enforcements/<entity_type>/custom', methods=['POST'])
    def enforce_entity_custom_data(self, entity_type):
        """
        See self._entity_custom_data
        """
        return self._entity_custom_data(EntityType(entity_type))

    @rev_cached(ttl=3600)
    def _get_actions_from_reports_plugin(self) -> dict:
        response = self.request_remote_plugin('reports/actions', REPORTS_PLUGIN_NAME,
                                              method='get', raise_on_network_error=True)
        response.raise_for_status()
        return response.json()

    @gui_add_rule_logged_in('cache/<cache_name>/delete')
    def _clean_cache(self, cache_name):
        if cache_name == 'reports_actions':
            logger.info('Cleaning _get_actions_from_reports_plugin cache async...')
            try:
                self._get_actions_from_reports_plugin.update_cache()
            except Exception as e:
                logger.exception(f'Exception while cleaning cache for {cache_name}')
                return jsonify({'status': False, 'exception': str(e)})
            return jsonify({'status': True})

        return jsonify({'status': False})

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
    def __tasks_query(mongo_filter, enforcement_name=None):
        """
        General query for all Complete / In progress task that also answer given mongo_filter
        """
        query_segments = [{
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

        if enforcement_name:
            query_segments.append({
                'post_json.report_name': enforcement_name
            })

        return {
            '$and': query_segments
        }

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_add_rule_logged_in('tasks', required_permissions={Permission(PermissionType.Enforcements,
                                                                      PermissionLevel.ReadOnly)})
    def enforcement_tasks(self, limit, skip, mongo_filter, mongo_sort):

        if mongo_sort.get('status'):
            mongo_sort['job_completed_state'] = -1 * mongo_sort['status']
            del mongo_sort['status']
        sort = [('finished_at', pymongo.DESCENDING)] if not mongo_sort else list(mongo_sort.items())
        return jsonify([self.beautify_task_entry(x) for x in self.enforcement_tasks_runs_collection.find(
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
                action_configs = self._get_actions_from_reports_plugin()
                if not action_configs:
                    return
                clear_passwords_fields(action['config'], action_configs[action['action_name']]['schema'])

            normalize_saved_action_results(task['result']['main']['action']['results'])
            clear_saved_action_passwords(task['result']['main']['action'])
            for key in [ACTIONS_SUCCESS_FIELD, ACTIONS_FAILURE_FIELD, ACTIONS_POST_FIELD]:
                arr = task['result'][key]
                for x in arr:
                    normalize_saved_action_results(x['action']['results'])
                    clear_saved_action_passwords(x['action'])

            task_metadata = task.get('result', {}).get('metadata', {})
            return beautify_db_entry({
                '_id': task['_id'],
                'enforcement': task['post_json']['report_name'],
                'view': task_metadata['trigger']['view']['name'],
                'period': task_metadata['trigger']['period'],
                'condition': task_metadata['triggered_reason'],
                'started': task['started_at'],
                'finished': task['finished_at'],
                'result': task['result'],
                'task_name': get_task_full_name(task.get('post_json', {}).get('report_name', ''),
                                                task_metadata.get('pretty_id', ''))
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
                                                                              GUI_PLUGIN_NAME,
                                                                              'watch_service',
                                                                              EXECUTION_PLUGIN_NAME,
                                                                              SYSTEM_SCHEDULER_PLUGIN_NAME]:
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
                    # pylint: disable=invalid-sequence-index
                    if processed_plugin['state']['state'] != 'Disabled':
                        # pylint: enable=invalid-sequence-index
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
    # pylint: disable=too-many-branches,too-many-locals
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
                                                                                 stored_locally=False))
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
                config_private = self._grab_file_contents(global_ssl.get('private_key'), stored_locally=False)
                try:
                    parsed_cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, config_cert)
                except Exception:
                    logger.exception(f'Error loading certificate')
                    return return_error(
                        f'Error loading certificate file. Please upload a pem-type certificate file.', 400)
                cn = dict(parsed_cert.get_subject().get_components())[b'CN'].decode('utf8')
                if cn != global_ssl['hostname']:
                    return return_error(f'Hostname does not match the hostname in the certificate file, '
                                        f'hostname in given cert is {cn}', 400)

                ssl_check_result = False
                try:
                    ssl_check_result = check_associate_cert_with_private_key(
                        config_cert, config_private, global_ssl.get('passphrase')
                    )
                except Exception as e:
                    return return_error(f'Error - can not load ssl settings: {str(e)}', 400)

                if not ssl_check_result:
                    return return_error(f'Private key and public certificate do not match each other', 400)

            aws_s3_settings = config_to_set.get('aws_s3_settings')
            if aws_s3_settings and aws_s3_settings.get('enabled') is True:
                enable_backups = aws_s3_settings.get('enable_backups')
                preshared_key = aws_s3_settings.get('preshared_key') or ''
                if enable_backups is True:
                    try:
                        verify_preshared_key(preshared_key)
                    except Exception as e:
                        return return_error(f'Error: {str(e)}', 400)
                bucket_name = aws_s3_settings.get('bucket_name')
                aws_access_key_id = aws_s3_settings.get('aws_access_key_id')
                aws_secret_access_key = aws_s3_settings.get('aws_secret_access_key')
                if (aws_access_key_id and not aws_secret_access_key) \
                        or (aws_secret_access_key and not aws_access_key_id):
                    return return_error(f'Error: Please specify both AWS Access Key ID and AWS Secret Access Key', 400)
                try:
                    for _ in aws_list_s3_objects(
                            bucket_name=bucket_name,
                            access_key_id=aws_access_key_id,
                            secret_access_key=aws_secret_access_key,
                            just_one=True
                    ):
                        break
                except Exception as e:
                    logger.exception(f'Error listing AWS s3 objects')
                    return return_error(f'Error listing AWS S3 Objects: {str(e)}', 400)
            getting_started_conf = config_to_set.get(GETTING_STARTED_CHECKLIST_SETTING)
            getting_started_feature_enabled = getting_started_conf.get('enabled')

            log_metric(logger, GettingStartedMetric.FEATURE_ENABLED_SETTING,
                       metric_value=getting_started_feature_enabled)

        elif plugin_name == 'gui' and config_name == CONFIG_CONFIG:
            mutual_tls_settings = config_to_set.get('mutual_tls_settings')
            if mutual_tls_settings.get('enabled'):
                is_mandatory = mutual_tls_settings.get('mandatory')
                client_ssl_cert = request.environ.get('HTTP_X_CLIENT_ESCAPED_CERT')

                if is_mandatory and not client_ssl_cert:
                    logger.error(f'Client certificate not found in request.')
                    return return_error(f'Client certificate not found in request. Please make sure your client '
                                        f'uses a certificate to access Axonius', 400)

                try:
                    ca_certificate = self._grab_file_contents(mutual_tls_settings.get('ca_certificate'))
                except Exception:
                    logger.exception(f'Error getting ca certificate from db')
                    return return_error(f'can not find uploaded certificate', 400)

                try:
                    OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, ca_certificate)
                except Exception:
                    logger.error(f'Can not load ca certificate', exc_info=True)
                    return return_error(f'The uploaded file is not a pem-format certificate', 400)
                try:
                    if is_mandatory and \
                            not validate_cert_with_ca(urllib.parse.unquote(client_ssl_cert), ca_certificate):
                        logger.error(f'Current client certificate is not trusted by the uploaded CA')
                        return return_error(f'Current client certificate is not trusted by the uploaded CA', 400)
                except Exception:
                    logger.error(f'Can not validate current client certificate with the uploaded CA', exc_info=True)
                    return return_error(f'Current client certificate can not be validated by the uploaded CA', 400)

        self._update_plugin_config(plugin_name, config_name, config_to_set)
        self._adapters.clean_cache()
        return ''

    def store_proxy_data(self, proxy_settings):
        try:

            # This string is used by chef!
            proxy_string = to_proxy_string(proxy_settings)
            verify = proxy_settings[PROXY_VERIFY]

            proxy_json = {
                'creds': proxy_string,
                'verify': verify
            }

            proxy_data = json.dumps(proxy_json)
            PROXY_DATA_PATH.write_text(proxy_data)  # saving proxy data to a folder readable from outside
            logger.info(f'updating proxy settings: {proxy_settings}')

        except Exception:
            logger.exception(f'Failed to set proxy settings from gui {proxy_settings}')

    @gui_add_rule_logged_in('plugins/configs/gui/FeatureFlags', methods=['POST', 'GET'], enforce_trial=False)
    def plugins_configs_feature_flags(self):
        plugin_name = GUI_PLUGIN_NAME
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
        if not self._is_hidden_user():
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
                'syslog': self._syslog_settings['enabled'] if self._syslog_settings else False,
                'httpsLog': self._https_logs_settings['enabled'] if self._https_logs_settings else False,
                'jira': self._jira_settings['enabled'] if self._jira_settings else False,
                'gettingStartedEnabled': self._getting_started_settings['enabled'],
                'cyberark_vault': self._vault_settings['enabled']
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

    @gui_add_rule_logged_in('plugins/gui/upload_file', methods=['POST'],
                            required_permissions={Permission(PermissionType.Settings,
                                                             PermissionLevel.ReadWrite)})
    def gui_upload_file(self):
        return self._upload_file(GUI_PLUGIN_NAME)

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
                    notifications.append(beautify_db_entry(n))
            else:
                sort = []
                for field, direction in mongo_sort.items():
                    sort.append(('_id' if field == 'date_fetched' else field, direction))
                if not sort:
                    sort.append(('_id', pymongo.DESCENDING))
                notifications = [beautify_db_entry(n) for n in notification_collection.find(
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
            beautify_db_entry(notification_collection.find_one({'_id': ObjectId(notification_id)})))

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
            if self._system_settings.get('timeout_settings') and self._system_settings.get('timeout_settings').get(
                    'enabled'):
                user['timeout'] = self._system_settings.get('timeout_settings').get('timeout') \
                    if not (os.environ.get('HOT') == 'true' or session.permanent) else 0
            return jsonify(beautify_user_entry(user)), 200

        log_in_data = self.get_request_data_as_object()
        if log_in_data is None:
            return return_error('No login data provided', 400)
        user_name = log_in_data.get('user_name')
        password = log_in_data.get('password')
        remember_me = log_in_data.get('remember_me', False)
        if not isinstance(remember_me, bool):
            return return_error('remember_me isn\'t boolean', 401)
        user_from_db = self._users_collection.find_one(filter_archived({
            'user_name': user_name,
            'source': 'internal'  # this means that the user must be a local user and not one from an external service
        }))
        if user_from_db is None:
            logger.info(f'Unknown user {user_name} tried logging in')
            self.send_external_info_log(f'Unknown user {user_name} tried logging in')
            return return_error('Wrong user name or password', 401)

        if not bcrypt.verify(password, user_from_db['password']):
            self.send_external_info_log(f'User {user_name} tried logging in with wrong password')
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
        user = self._users_collection.find_one(filter_archived(match_user))
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
            try:
                self._users_collection.replace_one(match_user, user, upsert=True)
            except pymongo.errors.DuplicateKeyError:
                logger.warning(f'Duplicate key error on {username}:{source}', exc_info=True)
            user = self._users_collection.find_one(filter_archived(match_user))
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
                                      ca_file_data=self._grab_file_contents(
                                          ldap_login['private_key']) if ldap_login['private_key'] else None,
                                      cert_file=self._grab_file_contents(
                                          ldap_login['cert_file']) if ldap_login['cert_file'] else None,
                                      private_key=self._grab_file_contents(
                                          ldap_login['ca_file']) if ldap_login['ca_file'] else None)
            except LdapException:
                logger.exception('Failed login')
                return return_error('Failed logging into AD')
            except Exception:
                logger.exception('Unexpected exception')
                return return_error('Failed logging into AD')

            result = conn.get_user(user_name)
            if not result:
                return return_error('Failed login')
            user, groups, groups_dn = result

            needed_group = ldap_login['group_cn']
            use_group_dn = ldap_login.get('use_group_dn') or False
            groups_prefix = [group.split('.')[0] for group in groups]
            if needed_group:
                if not use_group_dn:
                    if needed_group.split('.')[0] not in groups_prefix:
                        return return_error(f'The provided user is not in the group {needed_group}')
                else:
                    if needed_group not in groups_dn:
                        return return_error(f'The provided user is not in the group {needed_group}')
            image = None
            try:
                thumbnail_photo = user.get('thumbnailPhoto') or \
                    user.get('exchangePhoto') or \
                    user.get('jpegPhoto') or \
                    user.get('photo') or \
                    user.get('thumbnailLogo')
                if thumbnail_photo is not None:
                    if isinstance(thumbnail_photo, list):
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
        user = session['user']
        username = user.get('user_name')
        source = user.get('source')
        first_name = user.get('first_name')
        logger.info(f'User {username}, {source}, {first_name} has logged out')
        session['user'] = None
        return redirect('/', code=302)

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
                           self._users_collection.find(filter_archived(
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
        if self._users_collection.find_one(filter_archived(
                {
                    'user_name': post_data['user_name'],
                    'source': 'internal'
                })):
            return return_error('User already exists', 400)
        self.__create_user_if_doesnt_exist(post_data['user_name'], post_data['first_name'], post_data['last_name'],
                                           picname=None, source='internal', password=post_data['password'],
                                           role_name=post_data.get('role_name'))
        return ''

    @gui_add_rule_logged_in('system/users/<user_id>', methods=['POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Settings, PermissionLevel.ReadWrite)})
    def update_user(self, user_id):
        """
            Updates the userinfo for the current user or deleting a user
        """
        if request.method == 'POST':
            update_white_list_fields = ['first_name', 'last_name', 'password']
            post_data = self.get_request_data_as_object()
            user_data = {}
            for key, value in post_data.items():
                if key not in update_white_list_fields:
                    continue
                if key == 'password':
                    if value != UNCHANGED_MAGIC_FOR_GUI:
                        user_data[key] = bcrypt.hash(value)
                else:
                    user_data[key] = value

            res = self._users_collection.update_one({
                '_id': ObjectId(user_id)
            }, {
                '$set': user_data
            })
            if not res.matched_count:
                return '', 400
        if request.method == 'DELETE':
            self._users_collection.update_one({'_id': ObjectId(user_id)},
                                              {'$set': {'archived': True}})
            self.__invalidate_sessions(user_id)

        translate_user_id_to_details.clean_cache()
        return '', 200

    @gui_add_rule_logged_in('system/users/self/additional_userinfo', methods=['POST'])
    def system_users_additional_userinfo(self):
        """
        Updates the userinfo for the current user
        :return:
        """
        post_data = self.get_request_data_as_object()

        self._users_collection.update_one({
            '_id': get_connected_user_id()
        }, {
            '$set': {
                'additional_userinfo': post_data
            }
        })
        return '', 200

    @gui_add_rule_logged_in('system/users/self/password', methods=['POST'])
    def system_users_password(self):
        """
        Change a password for a specific user. It must be the same user as currently logged in to the system.
        Post data is expected to have the old password, matching the one in the DB

        :param user_id:
        :return:
        """
        post_data = self.get_request_data_as_object()
        user = session['user']
        if not bcrypt.verify(post_data['old'], user['password']):
            return return_error('Given password is wrong')

        self._users_collection.update_one({'_id': user['_id']},
                                          {'$set': {'password': bcrypt.hash(post_data['new'])}})
        self.__invalidate_sessions(user['_id'])
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
        self._users_collection.update_one({'_id': ObjectId(user_id)},
                                          {'$set': post_data})
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
                [beautify_db_entry(entry) for entry in self.__roles_collection.find(filter_archived())])

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
            self._users_collection.update_many(match_user_role, {
                '$set': {
                    'role_name': ''
                }
            })
        else:
            # Handling 'PUT' and 'POST' similarly - new role may replace an existing, archived one
            self.__roles_collection.replace_one(match_role, role_data, upsert=True)
            self._users_collection.update_many(match_user_role, {
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
            # Pylint is angry because it thinks session is a dict, which is true for HOT=True
            # pylint: disable=no-member
            if k == session.sid:
                continue
            # pylint: enable=no-member
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
            self._users_collection.update_one(
                {
                    '_id': get_connected_user_id(),
                },
                {
                    '$set': {
                        'api_key': new_api_key,
                        'api_secret': new_token
                    }
                }
            )
        api_data = self._users_collection.find_one({
            '_id': get_connected_user_id()
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

    @gui_add_rule_logged_in('first_historical_date', methods=['GET'], required_permissions={
        Permission(PermissionType.Dashboard, PermissionLevel.ReadOnly)})
    def get_first_historical_date(self):
        return jsonify(first_historical_date())

    @gui_add_rule_logged_in('get_allowed_dates', required_permissions={
        Permission(PermissionType.Dashboard, PermissionLevel.ReadOnly)})
    def all_historical_dates(self):
        return jsonify(all_historical_dates())

    @gui_add_rule_logged_in('dashboards', methods=['POST', 'GET'],
                            required_permissions={Permission(PermissionType.Dashboard, ReadOnlyJustForGet)},
                            enforce_trial=False)
    def get_dashboards(self):
        """
        GET all the saved spaces.

        POST a new space that will have the type 'custom'

        :return:
        """
        if request.method == 'GET':
            spaces = [{
                'uuid': str(space['_id']),
                'name': space['name'],
                'panels_order': space.get('panels_order'),
                'type': space['type']
            } for space in self.__dashboard_spaces_collection.find(filter_archived())]

            panels = self._get_dashboard(generate_data=False)
            return jsonify({
                'spaces': spaces,
                'panels': panels
            })

        # Handle 'POST' request method - save new custom dashboard space
        space_data = dict(self.get_request_data_as_object())
        space_data['type'] = DASHBOARD_SPACE_TYPE_CUSTOM
        insert_result = self.__dashboard_spaces_collection.insert_one(space_data)
        if not insert_result or not insert_result.inserted_id:
            return return_error(f'Could not create a new space named {space_data["name"]}')
        return str(insert_result.inserted_id)

    @gui_add_rule_logged_in('dashboards/<space_id>', methods=['PUT', 'DELETE'],
                            required_permissions={Permission(PermissionType.Dashboard, PermissionLevel.ReadWrite)},
                            enforce_trial=False)
    def update_dashboard_space(self, space_id):
        """
        PUT an updated name for an existing Dashboard Space
        DELETE an existing Dashboard Space

        :param space_id: The ObjectId of the existing space
        :return:         An error with 400 status code if failed, or empty response with 200 status code, otherwise
        """
        if request.method == 'PUT':
            space_data = dict(self.get_request_data_as_object())
            self.__dashboard_spaces_collection.update_one({
                '_id': ObjectId(space_id)
            }, {
                '$set': space_data
            })
            return ''

        if request.method == 'DELETE':
            delete_result = self.__dashboard_spaces_collection.delete_one({
                '_id': ObjectId(space_id)
            })
            if not delete_result or delete_result.deleted_count == 0:
                return return_error('Could not remove the requested Dashboard Space', 400)
            return ''

    @gui_add_rule_logged_in('dashboards/<space_id>/panels', methods=['POST'],
                            required_permissions={Permission(PermissionType.Dashboard, PermissionLevel.ReadWrite)},
                            enforce_trial=False)
    def add_dashboard_space_panel(self, space_id):
        """
        POST a new Dashboard Panel configuration, attached to requested space

        :param space_id: The ObjectId of the space for adding the panel to
        :return:         An error with 400 status code if failed, or empty response with 200 status code, otherwise
        """
        dashboard_data = dict(self.get_request_data_as_object())
        if not dashboard_data.get('name'):
            return return_error('Name required in order to save Dashboard Chart', 400)
        if not dashboard_data.get('config'):
            return return_error('At least one query required in order to save Dashboard Chart', 400)
        dashboard_data['space'] = ObjectId(space_id)
        dashboard_data['user_id'] = get_connected_user_id()
        dashboard_data[LAST_UPDATED_FIELD] = datetime.now()
        insert_result = self.__dashboard_collection.insert_one(dashboard_data)
        if not insert_result or not insert_result.inserted_id:
            return return_error('Error saving dashboard chart', 400)
        # Adding to the 'panels_order' attribute the newly panelId created through the wizard
        self.__dashboard_spaces_collection.update_one({
            '_id': ObjectId(space_id)
        }, {
            '$push': {
                'panels_order': str(insert_result.inserted_id)
            }
        })
        return str(insert_result.inserted_id)

    @gui_add_rule_logged_in('dashboards/<space_id>/panels/reorder', methods=['POST', 'GET'],
                            required_permissions={Permission(PermissionType.Dashboard, PermissionLevel.ReadWrite)},
                            enforce_trial=False)
    def reorder_dashboard_space_panels(self, space_id):
        if request.method == 'POST':
            panels_order = self.get_request_data_as_object().get('panels_order')
            self.__dashboard_spaces_collection.update_one({
                '_id': ObjectId(space_id)
            }, {
                '$set': {
                    'panels_order': panels_order
                }
            })
            return ''
        return jsonify(self.__dashboard_spaces_collection.find_one({
            '_id': ObjectId(space_id)
        }))

    @gui_helpers.paginated()
    @gui_add_rule_logged_in('dashboards/panels', methods=['GET'],
                            required_permissions={Permission(PermissionType.Dashboard, PermissionLevel.ReadOnly)},
                            enforce_trial=False)
    def get_dashboard_data(self, skip, limit):
        """
        Return charts data for the requested page.
        Charts attached to the Personal dashboard and a different user the connected one, are excluded

        """
        return jsonify(self._get_dashboard(skip, limit))

    def _process_initial_dashboard_data(self, dashboard_data: list) -> Dict[str, object]:
        """
        Truncates the given data to allow viewing the beginning and end of the values, if more than 100

        :param dashboard_data: List of values to be shown in the form of some dashboard chart
        :return: Tail and head of the list (50) or entire list, if up to 100 values and the total count
        """
        data_length = len(dashboard_data)
        data_limit, data_tail_limit = 50, -50
        if data_length <= 100:
            data_limit, data_tail_limit = 100, data_length
        return {
            'data': dashboard_data[:data_limit],
            'data_tail': dashboard_data[data_tail_limit:],
            'count': data_length
        }

    @gui_helpers.paginated()
    @gui_helpers.historical_range()
    @gui_add_rule_logged_in('dashboards/<space_id>/panels/<panel_id>', methods=['GET', 'DELETE', 'POST'],
                            required_permissions={Permission(PermissionType.Dashboard, ReadOnlyJustForGet)})
    def update_dashboard_panel(self, space_id, panel_id, skip, limit, from_date: datetime, to_date: datetime):
        """
        DELETE an existing Dashboard Panel and DELETE its panelId from the
        "panels_order" in the "dashboard_space" collection
        GET partial data of the Dashboard Panel
        POST an update of the configuration for an existing Dashboard Panel

        :param panel_id: The mongo id of the panel to handle
        :param space_id: The mongo id of the space where the panel should be removed
        :param skip: For GET, requested offset of panel's data
        :param limit: For GET, requested limit of panel's data
        :return: ObjectId of the Panel to delete
        """
        panel_id = ObjectId(panel_id)
        if request.method == 'GET':
            if from_date and to_date:
                generated_dashboard = generate_dashboard_historical(panel_id, from_date, to_date)
            else:
                generated_dashboard = generate_dashboard(panel_id)
            dashboard_data = generated_dashboard.get('data', [])
            if not skip:
                return jsonify(self._process_initial_dashboard_data(dashboard_data))
            return jsonify({
                'data': dashboard_data[skip: skip + limit]
            })

        if request.method == 'DELETE':
            self.__dashboard_spaces_collection.update_one({
                '_id': ObjectId(space_id)
            }, {
                '$pull': {
                    'panels_order': str(panel_id)
                }
            })
            update_data = {
                'archived': True
            }
        else:
            update_data = {
                **self.get_request_data_as_object(),
                'user_id': get_connected_user_id(),
                'last_updated': datetime.now()
            }
        update_result = self.__dashboard_collection.update_one(
            {'_id': panel_id}, {'$set': update_data})
        if not update_result.modified_count:
            return return_error(f'No dashboard by the id {str(panel_id)} found or updated', 400)
        if request.method == 'DELETE':
            generate_dashboard.remove_from_cache([panel_id])
            generate_dashboard_historical.remove_from_cache([panel_id, WILDCARD_ARG, WILDCARD_ARG])
        else:
            generate_dashboard.clean_cache([panel_id])
            generate_dashboard_historical.clean_cache([panel_id, WILDCARD_ARG, WILDCARD_ARG])
        return ''

    @gui_helpers.historical_range()
    @gui_add_rule_logged_in('dashboards/panels/<panel_id>/csv', methods=['GET'],
                            required_permissions={Permission(PermissionType.Dashboard, PermissionLevel.ReadOnly)})
    def chart_segment_csv(self, panel_id, from_date: datetime, to_date: datetime):
        card = self.__dashboard_collection.find_one({
            '_id': ObjectId(panel_id)
        })
        if (not card.get('view') or not card.get('config') or not card['config'].get('entity')
                or not card['config'].get('field')):
            return return_error('Error: no such data available ', 400)
        card['config']['entity'] = EntityType(card['config']['entity'])
        if from_date and to_date:
            data = fetch_chart_segment_historical(card, from_date, to_date)
        else:
            data = fetch_chart_segment(ChartViews[card['view']], **card['config'])
        name = card['config']['field']['title']
        string_output = io.StringIO()
        dw = csv.DictWriter(string_output, [name, 'count'])
        dw.writeheader()
        dw.writerows([{name: x['name'], 'count': x['value']} for x in data])
        outputFile = make_response(string_output.getvalue().encode('utf-8'))
        timestamp = datetime.now().strftime('%d%m%Y-%H%M%S')
        outputFile.headers['Content-Disposition'] = f'attachment; filename=axonius-chart_{card["name"]}_{timestamp}.csv'
        outputFile.headers['Content-type'] = 'text/csv'
        return outputFile

    def __clear_dashboard_cache(self, clear_slow=False):
        """
        Clears the calculated dashboard cache, and async recalculates all dashboards
        :param clear_slow: Also clear the slow cache
        """
        if clear_slow:
            generate_dashboard.update_cache()
        adapter_data.update_cache()
        get_fielded_plugins.update_cache()
        first_historical_date.clean_cache()
        all_historical_dates.clean_cache()
        entity_fields.clean_cache()
        self.__lifecycle.clean_cache()
        self._adapters.clean_cache()

    def __init_all_dashboards(self):
        """
        Warms up the cache for all dashboards for all users
        """
        for dashboard in self.__dashboard_collection.find(
                filter=filter_archived(),
                projection={
                    '_id': True
                }):
            try:
                generate_dashboard(dashboard['_id'])
            except Exception:
                logger.warning(f'Failed generating dashboard for {dashboard}', exc_info=True)

    def _get_dashboard(self, skip=0, limit=0, uncached: bool = False,
                       space_ids: list = None, exclude_personal=False, generate_data=True):
        """
        GET Fetch current dashboard chart definitions. For each definition, fetch each of it's views and
        fetch devices_db with their view. Amount of results is mapped to each views' name, under 'data' key,
        to be returned with the dashboard definition.

        POST Save a new dashboard chart definition, given it has a name and at least one query attached

        If 'uncached' is True, then this will return a non cached version
        If 'space_ids' is List[str] and has more then 0 space ids then fetch only these dashboard spaces

        :return:
        """
        logger.debug('Getting dashboard')
        personal_id = self.__dashboard_spaces_collection.find_one({'name': DASHBOARD_SPACE_PERSONAL}, {'_id': 1})['_id']
        filter_spaces = {
            'space': {
                '$in': [ObjectId(space_id) for space_id in space_ids]
            } if space_ids else {
                '$ne': personal_id
            },
            'name': {
                '$ne': None
            },
            'config': {
                '$ne': None
            }
        }
        if not exclude_personal:
            filter_spaces = {
                '$or': [{
                    'space': personal_id,
                    'user_id': {
                        '$in': ['*', get_connected_user_id()]
                    }
                }, filter_spaces]
            }
        for dashboard in self.__dashboard_collection.find(
                filter=filter_archived(filter_spaces),
                skip=skip,
                limit=limit,
                projection={
                    '_id': True,
                    'space': True,
                    'name': True
                }):
            # Let's fetch and execute them query filters
            try:
                if generate_data:
                    if uncached:
                        generated_dashboard = generate_dashboard_uncached(dashboard['_id'])
                    else:
                        generated_dashboard = generate_dashboard(dashboard['_id'])
                    yield {
                        **generated_dashboard,
                        **self._process_initial_dashboard_data(generated_dashboard.get('data', []))
                    }
                else:
                    yield {
                        'uuid': str(dashboard['_id']),
                        'name': dashboard['name'],
                        'space': str(dashboard['space']),
                        'data': [],
                        'loading': True
                    }
            except Exception:
                # Since there is no data, not adding this chart to the list
                logger.exception(f'Error fetching data for chart ({dashboard["_id"]})')

    def _get_lifecycle_phase_info(self, doc_id: ObjectId) -> dict:
        """
        :param  doc_id: the id of the triggerable_history job to get the result from
        :return: the result field in the triggerable_history collection
        """
        if not doc_id:
            return {}
        result = self.aggregator_db_connection['triggerable_history'].find_one(
            {
                '_id': doc_id
            },
            sort=[('started_at', pymongo.DESCENDING)]
        )
        if not result or not result['result']:
            return {}
        return result['result']

    @rev_cached(ttl=3, key_func=lambda self: 1)
    def __lifecycle(self):
        res = self.request_remote_plugin('trigger_state/execute', SYSTEM_SCHEDULER_PLUGIN_NAME)
        execution_state = res.json()
        if 'state' not in execution_state:
            logger.critical(f'Something is deeply wrong with scheduler, result is {execution_state} '
                            f'on {res}')
        is_running = execution_state['state'] == TriggerStates.Triggered.name
        del res, execution_state

        state_response = self.request_remote_plugin('state', SYSTEM_SCHEDULER_PLUGIN_NAME)
        if state_response.status_code != 200:
            raise RuntimeError(f'Error fetching status of system scheduler. Reason: {state_response.text}')

        state_response = state_response.json()
        # pylint: disable=no-member
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
            additional_data = {}
            if is_research and sub_phase.name == state.SubPhase:
                # Reached current status - set complementary of SubPhaseStatus value
                found_current = True
                if sub_phase.name in (ResearchPhases.Fetch_Devices.name, ResearchPhases.Fetch_Scanners.name):
                    doc_id = state_response.get('state').get('AssociatePluginId')
                    additional_data = self._get_lifecycle_phase_info(doc_id=ObjectId(doc_id))

                sub_phases.append({
                    'name': sub_phase.name,
                    'status': 0,
                    'additional_data': additional_data
                })
            else:
                # Set 0 or 1, depending if reached current status yet
                sub_phases.append({
                    'name': sub_phase.name,
                    'status': 0 if found_current else 1,
                    'additional_data': additional_data
                })

        # pylint: enable=no-member

        return {
            'sub_phases': sub_phases,
            'next_run_time': state_response['next_run_time'],
            'last_start_time': state_response['last_start_time'],
            'last_finished_time': state_response['last_finished_time'],
            'status': nice_state.name
        }

    @gui_add_rule_logged_in(DASHBOARD_LIFECYCLE_ENDPOINT, methods=['GET'],
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
        self._trigger_remote_plugin(SYSTEM_SCHEDULER_PLUGIN_NAME, blocking=False, external_thread=False)

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
                    view_filter = find_filter_by_name(entity, query['name'])
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
        generated_date = datetime.now(tz.tzlocal())
        report_html, attachments = self.generate_report(generated_date, report)

        exec_report_generate_pdf_thread_id = EXEC_REPORT_GENERATE_PDF_THREAD_ID.format(report['name'])
        exec_report_generate_pdf_job = self._job_scheduler.get_job(exec_report_generate_pdf_thread_id)
        # If job doesn't exist generate it
        if exec_report_generate_pdf_job is None:
            self._job_scheduler.add_job(func=self._convert_to_pdf_and_save_report,
                                        kwargs={'report': report,
                                                'report_html': report_html,
                                                'generated_date': generated_date,
                                                'attachments': attachments},
                                        trigger='date',
                                        next_run_time=datetime.now(),
                                        name=exec_report_generate_pdf_thread_id,
                                        id=exec_report_generate_pdf_thread_id,
                                        max_instances=1,
                                        coalesce=True)
        else:
            self._job_scheduler.reschedule_job(exec_report_generate_pdf_thread_id, next_run_time=datetime.now())

    def _convert_to_pdf_and_save_report(self, report, report_html, generated_date, attachments):
        # Writes the report pdf to a file-like object and use seek() to point to the beginning of the stream
        name = report['name']
        try:
            with io.BytesIO() as report_data:
                report_html.write_pdf(report_data)
                report_data.seek(0)
                # Uploads the report to the db and returns a uuid to retrieve it
                uuid = self._upload_report(report_data, report)
                logger.info(f'Report was saved to the grif fs db uuid: {uuid}')
                # Stores the uuid in the db in the "reports" collection

                attachment_uuids = []
                for attachment in attachments:
                    with io.BytesIO() as attachment_data:
                        attachment_data.write(attachment['stream'].getvalue().encode('utf-8'))
                        attachment_data.seek(0)
                        attachment_uuid = self._upload_attachment(attachment['name'], attachment_data)
                        attachment_uuids.append(attachment_uuid)

                filename = 'most_recent_{}'.format(name)
                self._get_collection('reports').replace_one(
                    {
                        'filename': filename
                    },
                    {
                        'uuid': uuid,
                        'filename': filename,
                        'time': datetime.now(),
                        'attachments': attachment_uuids
                    },
                    upsert=True
                )
                logger.info(f'Report was saved to the mongo db to "reports" collection filename: {filename}')

                report[report_consts.LAST_GENERATED_FIELD] = generated_date
                self._upsert_report_config(name, report, False)
                logger.info(f'Report was saved to the mongo db to "report_configs" collection name: {name}')
        except Exception:
            logger.exception(f'Exception with report {name}')

    def _upload_report(self, report, report_metadata) -> str:
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
        fs = gridfs.GridFS(db_connection[GUI_PLUGIN_NAME])
        written_file_id = fs.put(report, filename=report_name)
        logger.info('Report successfully placed in the db')
        return str(written_file_id)

    def _upload_attachment(self, attachment_name: str, attachment_stream: object) -> str:
        """
        Uploads an attachment for a report to the db
        :param attachment_name: attachment name
        :param attachment_stream: attachment stream
        :return: the attachment object id
        """
        if not attachment_name:
            return return_error('Attachment must exist', 401)

        db_connection = self._get_db_connection()
        fs = gridfs.GridFS(db_connection[GUI_PLUGIN_NAME])
        written_file_id = fs.put(attachment_stream,
                                 filename=attachment_name)
        logger.info('Attachment successfully placed in the db')
        return str(written_file_id)

    def _delete_last_report(self, report_name):
        """
        Deletes the last version of the report pdf to avoid having too many saved versions
        :return:
        """
        report_collection = self._get_collection('reports')
        most_recent_report = report_collection.find_one({'filename': report_name})
        if most_recent_report is not None:
            fs = gridfs.GridFS(self._get_db_connection()[GUI_PLUGIN_NAME])
            attachments = most_recent_report.get('attachments')
            if attachments is not None:
                for attachment_uuid in attachments:
                    logger.info(f'DELETE attachment: {attachment_uuid}')
                    fs.delete(ObjectId(attachment_uuid))
            uuid = most_recent_report.get('uuid')
            if uuid is not None:
                logger.info(f'DELETE: {uuid}')
                fs.delete(ObjectId(uuid))

    @gui_add_rule_logged_in('export_report/<report_id>', required_permissions={Permission(PermissionType.Dashboard,
                                                                                          PermissionLevel.ReadOnly)})
    def export_report(self, report_id):
        """
        Gets definition of report from DB for the dynamic content.
        Gets all the needed data for both pre-defined and dynamic content definitions.
        Sends the complete data to the report generator to be composed to one document and generated as a pdf file.

        If background report generation setting is turned off, the report will be generated here, as well.

        TBD Should receive ID of the report to export (once there will be an option to save many report definitions)
        :return:
        """
        report_name, report_data, attachments_data = self._get_existing_executive_report_and_attachments(report_id)
        response = Response(report_data, mimetype='application/pdf', direct_passthrough=True)
        return response

    def _get_existing_executive_report_and_attachments(self, report_id) -> Tuple[str, object, List[object]]:
        """
        Opens the report pdf and attachment csv's from the db,
        save them in a temp files and return their path
        :param name: a report name string
        :return: A tuple of the report pdf path and a list of attachments paths
         """
        report_config = self.reports_config_collection.find_one({'_id': ObjectId(report_id)})
        name = report_config.get('name', '')
        report = self._get_collection('reports').find_one({'filename': f'most_recent_{name}'})
        logger.info(f'exporting report "{name}"')
        if not report:
            logger.info(f'exporting report "{name}" failed - most recent report was not found')
            raise Exception('The report is being generated or '
                            'there was a problem with generating the report')

        logger.info(f'exporting report "{name}" succeeded. most recent report found')
        uuid = report['uuid']
        report_path = f'axonius-{name}_{datetime.now()}.pdf'
        logger.info(f'report_path: {report_path}')
        db_connection = self._get_db_connection()

        attachments_data = []
        gridfs_connection = gridfs.GridFS(db_connection[GUI_PLUGIN_NAME])
        attachments = report.get('attachments')
        if attachments:
            for attachment_uuid in attachments:
                try:
                    attachment = gridfs_connection.get(ObjectId(attachment_uuid))
                    attachments_data.append({
                        'name': attachment.name,
                        'content': attachment
                    })
                except Exception:
                    logger.error(f'failed to retrieve attachment {attachment_uuid}')
        report_data = gridfs_connection.get(ObjectId(uuid))
        return report_path, report_data, attachments_data

    def generate_report(self, generated_date, report):
        """
        Generates the report and returns html.
        :return: the generated report file path.
        """
        logger.info('Starting to generate report')
        generator_params = {}
        space_ids = report.get('spaces') or []
        generator_params['dashboard'] = self._get_dashboard(space_ids=space_ids, exclude_personal=True)
        generator_params['adapters'] = self._get_adapter_data(report['adapters']) if report.get('adapters') else None
        generator_params['default_sort'] = self._system_settings['defaultSort']
        generator_params['saved_view_count_func'] = self._get_entity_count
        generator_params['spaces'] = self.__dashboard_spaces_collection.find(filter_archived())
        system_config = self.system_collection.find_one({'type': 'server'}) or {}
        server_name = system_config.get('server_name', 'localhost')
        logger.info(f'All data for report gathered - about to generate for server {server_name}')
        return ReportGenerator(report,
                               generator_params,
                               'gui/templates/report/',
                               host=server_name).render_html(generated_date)

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
            return return_error(f'Problem testing report by email: {repr(e)}', 400)

    def _get_exec_report_settings(self, exec_reports_settings_collection):
        settings_objects = exec_reports_settings_collection.find(
            {'period': {'$exists': True}, 'mail_properties': {'$exists': True}})
        return settings_objects

    def _schedule_exec_report(self, exec_report_data):
        logger.info('rescheduling exec_reports')
        time_period = exec_report_data.get('period')
        time_period_config = exec_report_data.get('period_config')
        current_date = datetime.now()
        next_run_time = current_date

        next_run_hour = 8
        next_run_minute = 0
        week_day = 0
        monthly_day = 1

        if time_period_config:
            send_time = time_period_config.get('send_time')
            send_time_parts = send_time.split(':')
            next_run_hour = int(send_time_parts[0])
            next_run_minute = int(send_time_parts[1])
            week_day = int(time_period_config.get('week_day'))
            monthly_day = int(time_period_config.get('monthly_day'))

            utc_time_diff = int((datetime.now() - datetime.utcnow()).total_seconds() / 3600)
            next_run_hour += utc_time_diff
            if next_run_hour > 23:
                next_run_hour -= 24
            elif next_run_hour < 0:
                next_run_hour += 24

        next_run_time = next_run_time.utcnow()

        if time_period == 'weekly':
            if week_day < next_run_time.weekday() or (week_day == next_run_time.weekday() and
                                                      next_run_time.replace(hour=next_run_hour, minute=next_run_minute,
                                                                            second=0) < next_run_time):
                # Get next week's selected week day if it has passed this week
                next_run_time = next_weekday(current_date, week_day)
            else:
                # Get next day of the the current week
                day_of_month_diff = week_day - current_date.weekday()
                next_run_time += timedelta(days=day_of_month_diff)
            next_run_time = next_run_time.replace(hour=next_run_hour, minute=next_run_minute, second=0)
            new_interval_triggger = CronTrigger(year='*', month='*', week='*',
                                                day_of_week=week_day, hour=next_run_hour,
                                                minute=next_run_minute, second=0)
        elif time_period == 'monthly':
            if monthly_day < current_date.day or (monthly_day == current_date.day and
                                                  next_run_time.replace(hour=next_run_hour,
                                                                        minute=next_run_minute,
                                                                        second=0) < next_run_time):
                # ￿Go to next month if the selected day of the month has passed
                next_run_time = current_date + relativedelta(months=+1)
            next_run_time = next_run_time.replace(day=monthly_day, hour=next_run_hour,
                                                  minute=next_run_minute, second=0)
            # 29 means the end of the month
            if monthly_day == 29:
                last_month_day = calendar.monthrange(current_date.year, current_date.month)[1]
                next_run_time.replace(day=last_month_day)
                monthly_day = 'last'
            new_interval_triggger = CronTrigger(year='*', month='1-12',
                                                day=monthly_day, hour=next_run_hour,
                                                minute=next_run_minute, second=0)
        elif time_period == 'daily':
            if next_run_time.replace(hour=next_run_hour, minute=next_run_minute, second=0) < next_run_time:
                # sets it for tomorrow if the selected time has passed
                next_run_time = current_date + relativedelta(days=+1)
            next_run_time = next_run_time.replace(hour=next_run_hour, minute=next_run_minute, second=0)
            new_interval_triggger = CronTrigger(year='*', month='*', week='*',
                                                day_of_week='0-4', hour=next_run_hour,
                                                minute=next_run_minute, second=0)
        else:
            raise ValueError('period have to be in (\'daily\', \'monthly\', \'weekly\').')

        exec_report_thread_id = EXEC_REPORT_THREAD_ID.format(exec_report_data['name'])
        exec_report_job = self._job_scheduler.get_job(exec_report_thread_id)

        logger.info(f'Next report send time: {next_run_time}')

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
            exec_report_job.modify(func=self._send_report_thread,
                                   kwargs={'report': exec_report_data},
                                   next_run_time=next_run_time)
            self._job_scheduler.reschedule_job(exec_report_thread_id, trigger=new_interval_triggger)

        logger.info(f'Scheduling an exec_report sending for {next_run_time} and period of {time_period}.')
        return 'Scheduled next run.'

    def _send_report_thread(self, report):
        if self.trial_expired():
            logger.error('Report email not sent - system trial has expired')
            return
        report_name = report['name']
        logger.info(f'_send_report_thread for the "{report_name}" report started')
        lock = self.exec_report_locks[report_name] if self.exec_report_locks.get(report_name) else threading.RLock()
        self.exec_report_locks[report_name] = lock
        with lock:
            report_path, report_data, attachments_data = self._get_existing_executive_report_and_attachments(
                report['uuid'])
            if self.mail_sender:
                try:
                    mail_properties = report['mail_properties']
                    subject = mail_properties.get('mailSubject')
                    logger.info(mail_properties)
                    if mail_properties.get('emailList'):
                        email = self.mail_sender.new_email(subject,
                                                           mail_properties.get('emailList', []),
                                                           cc_recipients=mail_properties.get('emailListCC', []))
                        email.add_pdf(EXEC_REPORT_FILE_NAME.format(report_name), report_data.read())

                        for attachment_data in attachments_data:
                            email.add_attachment(attachment_data['name'], attachment_data['content'].read(),
                                                 'text/csv')
                        email.send(mail_properties.get('mailMessage', EXEC_REPORT_EMAIL_CONTENT))
                        self.reports_config_collection.update_one({
                            'name': report_name,
                            'archived': {
                                '$ne': True
                            }
                        }, {
                            '$set': {
                                report_consts.LAST_TRIGGERED_FIELD: datetime.now()
                            }
                        })
                        logger.info(f'The "{report_name}" report was sent')
                except Exception:
                    logger.info(f'Failed to send an Email for the "{report_name}" report')
                    raise
            else:
                logger.info('Email cannot be sent because no email server is configured')
                raise RuntimeWarning('No email server configured')
        logger.info(f'_send_report_thread for the "{report_name}" report ended')

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

            log_metric(logger, SystemMetric.GUI_USERS, self._users_collection.count_documents({}))
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

    #############
    # Instances #
    #############

    @gui_add_rule_logged_in('instances', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Instances,
                                                             ReadOnlyJustForGet)})
    def instances(self):
        return self._instances()

    def _is_node_activated(self, target_node_id=None) -> bool:

        if target_node_id == self.node_id:
            logger.debug(f'node id {target_node_id} is The MASTER ')
            return True

        node = self._get_db_connection()['core']['nodes_metadata'].find_one({NODE_ID: target_node_id})

        if node is None or not node.get(NODE_STATUS, ACTIVATED_NODE_STATUS) == ACTIVATED_NODE_STATUS:
            logger.error(f'node id {target_node_id} is not Activated ')
            return False
        logger.debug(f'node id {target_node_id} is online  ')
        return True

    def _update_hostname_on_node(self, instance_data=None):
        node_id = instance_data.get(NODE_DATA_INSTANCE_ID, None)
        logger.info(f'Starting to update hostname for target node id {node_id}')
        new_hostname = str(instance_data.get(NODE_HOSTNAME))

        url = f'find_plugin_unique_name/nodes/{node_id}/plugins/instance_control'
        node_unique_name = self.request_remote_plugin(url).json().get('plugin_unique_name')

        if node_unique_name is None:
            logger.error(f'unable to allocate target instance control plugin_unique_name with id  {node_id}')
            return False

        if self._is_node_activated(node_id) and node_unique_name:
            resp = self.request_remote_plugin(f'instances/host/{new_hostname}',
                                              node_unique_name,
                                              method='put',
                                              raise_on_network_error=True)
            if resp.status_code != 200:
                logger.error(f'failure to update node hostname response '
                             f'back from instance control {str(resp.content)} ')
            else:
                return True
        else:
            logger.error('node is offline aborting hostname update')
        return False

    def _instances(self):
        if request.method == 'GET':
            db_connection = self._get_db_connection()
            nodes = self._get_nodes_table()
            system_config = db_connection['gui']['system_collection'].find_one({'type': 'server'}) or {}
            connection_key = None
            if get_user_permissions().get(PermissionType.Instances) == PermissionLevel.ReadWrite or is_admin_user():
                connection_key = self.encryption_key
            return jsonify({
                'instances': nodes,
                'connection_data': {
                    'key': connection_key,
                    'host': system_config.get('server_name', '<axonius-hostname>')
                }
            })
        elif request.method == 'POST':

            data = self.get_request_data_as_object()

            def update_instance(instance_data=None, attribute=None):
                if instance_data.get(attribute, None):
                    node_id = instance_data.get(NODE_DATA_INSTANCE_ID)
                    self.request_remote_plugin(f'node/{node_id}', method='POST',
                                               json={'key': attribute, 'value': instance_data.get(attribute)})
                else:
                    logger.debug(f'{attribute} is null skip update. ')

            # REACTIVATE NODE
            if NODE_DATA_INSTANCE_ID in data and NODE_STATUS in data:
                update_instance(instance_data=data, attribute=NODE_STATUS)
            # UPDATE NODE NAME AND HOSTNAME
            elif NODE_DATA_INSTANCE_ID in data:
                update_instance(instance_data=data, attribute=NODE_NAME)
                if _is_valid_node_hostname(data[NODE_HOSTNAME]):
                    if self._update_hostname_on_node(instance_data=data):
                        update_instance(instance_data=data, attribute=NODE_HOSTNAME)
                    else:
                        return return_error(f'Failed to change hostname', 500)
                else:
                    return return_error(f'Illegal hostname value entered', 500)
            return ''

        elif request.method == 'DELETE':
            data = self.get_request_data_as_object()
            node_ids = data[NODE_DATA_INSTANCE_ID]
            if self.node_id in node_ids:
                return return_error('Can\'t Deactivate Master.', 400)

            for current_node in node_ids:
                # List because it might take a while for the process to finish
                # and cursors have a TTL
                node_adapters = list(self.core_configs_collection.find({
                    'plugin_type': adapter_consts.ADAPTER_PLUGIN_TYPE,
                    NODE_ID: current_node
                }, projection={
                    PLUGIN_UNIQUE_NAME: True,
                    PLUGIN_NAME: True
                }))

                for adapter in node_adapters:
                    plugin_unique_name = adapter[PLUGIN_UNIQUE_NAME]
                    plugin_name = adapter[PLUGIN_NAME]
                    cursor = self._get_collection('clients', plugin_unique_name).find({},
                                                                                      projection={'_id': 1})
                    for current_client in cursor:
                        self.request_remote_plugin(
                            'clients/' + str(current_client['_id']), plugin_unique_name, method='delete')

                # Deactivate node
                self.request_remote_plugin(f'node/{current_node}', method='POST',
                                           json={'key': 'status', 'value': DEACTIVATED_NODE_STATUS})
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
            customer = signup.get(Signup.CompanyField, 'company-not-set')
            if not customer or customer in [SIGNUP_TEST_CREDS[Signup.CompanyField], SIGNUP_TEST_COMPANY_NAME]:
                return

            if has_request_context():
                user = session.get('user')
                if user is None:
                    return
                user = dict(user)
                user_name = user.get('user_name')
                source = user.get('source')

                if user_name == AXONIUS_USER_NAME and source == 'internal':
                    return

            # referrer
            values['tid'] = 'UA-137924837-1'
            values['dr'] = f'https://{customer}'
            values['dh'] = customer
            if 'dl' in values:
                del values['dl']
            response = requests.request(request.method,
                                        path,
                                        params=values,
                                        timeout=(10, 30)
                                        )
            if response.status_code != 200:
                logger.error('Failed to submit ga data {response}')

    #################
    # Vault Service #
    #################

    @gui_add_rule_logged_in('password_vault', methods=['POST'],
                            required_permissions={Permission(PermissionType.Adapters, PermissionLevel.ReadWrite)})
    def check_password_vault_query(self):
        """
        Checks if the query successfully fetches data from requested vault (for use before saving the client credentials).
        :return: True if successfully retrieves data from requested vault.
        """
        vault_fetch_data = self.get_request_data_as_object()
        try:
            if self.check_password_fetch(vault_fetch_data['field'], vault_fetch_data['query']):
                return ''
        except Exception as exc:
            return return_error(str(exc))

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
        self._okta = config['okta_login_settings']
        self.__saml_login = config['saml_login_settings']
        self.__ldap_login = config['ldap_login_settings']
        self._system_settings = config[SYSTEM_SETTINGS]
        self._mutual_tls_settings = config['mutual_tls_settings']
        mutual_tls_is_mandatory = self._mutual_tls_settings.get('mandatory')

        if self._mutual_tls_settings.get('enabled') and mutual_tls_is_mandatory:
            # Enable Mutual TLS.
            # Note that we have checked before (plugins_configs_set) that the issuer is indeed part of this cert
            # as input validation. So input validation is not needed here.
            try:
                ca_certificate = self._grab_file_contents(self._mutual_tls_settings.get('ca_certificate'))

                current_ca_cert = None
                if os.path.exists(MUTUAL_TLS_CA_PATH):
                    with open(MUTUAL_TLS_CA_PATH, 'rb') as mtls_file:
                        current_ca_cert = mtls_file.read()

                if not current_ca_cert or current_ca_cert != ca_certificate:
                    logger.info(f'Writing mutual tls settings')
                    with open(MUTUAL_TLS_CA_PATH, 'wb') as mtls_file:
                        mtls_file.write(ca_certificate)

                    with open(MUTUAL_TLS_CONFIG_FILE, 'wt') as mtls_config_file:
                        mtls_config_file.write(
                            f'ssl_verify_client on;\r\n'
                            f'ssl_verify_depth 10;\r\n'
                            f'ssl_client_certificate {MUTUAL_TLS_CA_PATH};\r\n'
                        )
                    # Restart Openresty (NGINX)
                    subprocess.check_call(['openresty', '-s', 'reload'])
                    logger.info(f'Successfuly loaded new mutual TLS settings')
            except Exception:
                logger.critical(f'Can not get mutual tls ca certificate, system is not protected', exc_info=True)
        else:
            # Disable mandatory Mutual TLS
            mutual_tls_state = f'optional_no_ca' if self._mutual_tls_settings.get('enabled') else 'off'
            try:
                if os.path.exists(MUTUAL_TLS_CA_PATH):
                    logger.info(f'Deleting mutual tls settings')
                    with open(MUTUAL_TLS_CONFIG_FILE, 'wt') as mtls_config_file:
                        mtls_config_file.write(f'ssl_verify_client {mutual_tls_state};')
                    # Restart Openresty (NGINX)
                    subprocess.check_call(['openresty', '-s', 'reload'])
                    os.unlink(MUTUAL_TLS_CA_PATH)
                    logger.info(f'Successfuly loaded new mutual TLS settings: {mutual_tls_state}')
            except Exception:
                logger.exception(f'Can not delete mutual tls settings')

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

        try:
            new_ttl = self.__ldap_login.get('cache_time_in_hours')
            new_ttl = new_ttl if new_ttl is not None else 1

            if (get_ldap_groups_cache_ttl() / 3600) != new_ttl:
                logger.info(f'Setting a new cache with ttl of {new_ttl} hours')
                set_ldap_groups_cache(new_ttl * 3600)
        except Exception:
            logger.exception(f'Failed - could not add LDAP groups cached')

    def _global_config_updated(self):
        self.store_proxy_data(self._proxy_settings)

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
            return jsonify({Signup.SignupField: bool(signup) or has_customer_login_happened()})

        # POST from here
        if signup or has_customer_login_happened():
            return return_error('Signup already completed', 400)

        signup_data = self.get_request_data_as_object() or {}

        new_password = signup_data[Signup.NewPassword] if \
            signup_data[Signup.ConfirmNewPassword] == signup_data[Signup.NewPassword] \
            else ''

        if not new_password:
            return return_error('Passwords do not match', 400)

        self._users_collection.update_one({'user_name': 'admin'},
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

        # Reset this setting for new (version > 2.11) customers upon signup (Getting Started With Axonius Checklist)
        self._get_collection(CONFIGURABLE_CONFIGS_COLLECTION, CORE_UNIQUE_NAME).update_one({
            'config_name': CORE_CONFIG_NAME
        }, {
            '$set': {
                f'config.{GETTING_STARTED_CHECKLIST_SETTING}.enabled': True
            }
        })

        # Update Getting Started Checklist to interactive mode (version > 2.10)
        self._get_collection('getting_started', GUI_PLUGIN_NAME).update_one({}, {
            '$set': {
                'settings.interactive': True
            }
        })
        self._getting_started_settings['enabled'] = True
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
                            'name': 'defaultNumOfEntitiesPerPage',
                            'title': 'Default Number of Query Results Displayed Per Page',
                            'type': 'string',
                            'enum': [20, 50, 100]
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
                            'name': 'autoQuery',
                            'title': 'Perform a Query Every Keypress',
                            'type': 'bool'
                        },
                        {
                            'name': 'defaultColumnLimit',
                            'title': 'Number of Values Displayed in each Column',
                            'type': 'string',
                            'enum': [1, 2]
                        },
                        {
                            'name': 'timeout_settings',
                            'title': 'Timeout Settings',
                            'items': [
                                {
                                    'name': 'enabled',
                                    'title': 'Enable Session Timeout',
                                    'type': 'bool'
                                },
                                {
                                    'name': 'timeout',
                                    'title': 'Session Idle Timeout (Minutes)',
                                    'type': 'number',
                                    'default': 120
                                }
                            ],
                            'required': ['enabled', 'timeout'],
                            'type': 'array'
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
                        }
                    ],
                    'required': ['refreshRate', 'defaultNumOfEntitiesPerPage', 'singleAdapter', 'multiLine',
                                 'defaultSort', 'autoQuery', 'defaultColumnLimit'],
                    'name': SYSTEM_SETTINGS,
                    'title': 'System Settings',
                    'type': 'array'
                },
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Allow Okta Logins',
                            'type': 'bool'
                        },
                        {
                            'name': 'client_id',
                            'title': 'Okta Application Client Id',
                            'type': 'string'
                        },
                        {
                            'name': 'client_secret',
                            'title': 'Okta Application Client Secret',
                            'type': 'string',
                            'format': 'password'
                        },
                        {
                            'name': 'url',
                            'title': 'Okta Application URL',
                            'type': 'string'
                        },
                        {
                            'name': 'gui2_url',
                            'title': 'Axonius GUI URL',
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
                            'title': 'Allow LDAP Logins',
                            'type': 'bool'
                        },
                        {
                            'name': 'dc_address',
                            'title': 'The Host Domain Controller IP or DNS',
                            'type': 'string'
                        },
                        {
                            'name': 'group_cn',
                            'title': 'A Group the User Must be Part of',
                            'type': 'string'
                        },
                        {
                            'name': 'use_group_dn',
                            'title': 'Match Group Name by DN',
                            'type': 'bool'
                        },
                        {
                            'name': 'default_domain',
                            'title': 'Default Domain to Present to the User',
                            'type': 'string'
                        },
                        {
                            'name': 'cache_time_in_hours',
                            'title': 'Cache Time (Hours)',
                            'type': 'integer'
                        },
                        *COMMON_SSL_CONFIG_SCHEMA
                    ],
                    'required': ['enabled', 'dc_address', 'use_group_dn', 'cache_time_in_hours'],
                    'name': 'ldap_login_settings',
                    'title': 'Ldap Login Settings',
                    'type': 'array'
                },
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Allow SAML-Based Logins',
                            'type': 'bool'
                        },
                        {
                            'name': 'idp_name',
                            'title': 'Name of the Identity Provider',
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
                },
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Enable Mutual TLS',
                            'type': 'bool'
                        },
                        {
                            'name': 'mandatory',
                            'title': 'Enforce Client Certificate Validation',
                            'type': 'bool'
                        },
                        {
                            'name': 'ca_certificate',
                            'title': 'CA Certificate',
                            'description': 'A pem encoded certificate to authenticate users',
                            'type': 'file'
                        }
                    ],
                    'required': ['enabled', 'ca_certificate', 'mandatory'],
                    'name': 'mutual_tls_settings',
                    'title': 'Mutual TLS Settings',
                    'type': 'array'
                },
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
                'use_group_dn': False,
                'cache_time_in_hours': 1,
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
                'defaultNumOfEntitiesPerPage': 20,
                'timeout_settings': {
                    'enabled': True,
                    'timeout': 120
                },
                'singleAdapter': False,
                'multiLine': False,
                'defaultSort': True,
                'autoQuery': True,
                ''
                'defaultColumnLimit': 2,
                'percentageThresholds': {
                    'error': 40,
                    'warning': 60,
                    'success': 100,
                }
            },
            'mutual_tls_settings': {
                'enabled': False,
                'mandatory': False,
                'ca_certificate': None
            }
        }

    def _get_entity_count(self, entity, mongo_filter, history, quick):
        return str(gui_helpers.get_entities_count(mongo_filter, self.get_appropriate_view(history, entity),
                                                  history_date=history, quick=quick))

    # TODO: permissions requirements
    @gui_add_rule_logged_in('compliance/<compliance_name>/<method>')
    def compliance(self, compliance_name: str, method: str):
        try:
            return jsonify(get_compliance(compliance_name, method))
        except Exception as e:
            logger.exception(f'Error in get_compliance')
            return return_error(f'Error: {str(e)}')
