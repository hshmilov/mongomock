import configparser
import io
import json
import logging
import os
import re
import secrets
import shutil
import tarfile
import threading
from collections import defaultdict
from datetime import date, datetime, timedelta
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool
from typing import Iterable, Tuple
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
from elasticsearch import Elasticsearch
from flask import (after_this_request, jsonify, make_response, redirect,
                   request, send_file, session)
from passlib.hash import bcrypt
from urllib3.util.url import parse_url

from axonius.adapter_base import AdapterProperty
from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.clients.ldap.exceptions import LdapException
from axonius.clients.ldap.ldap_connection import LdapConnection
from axonius.clients.rest.connection import RESTConnection
from axonius.consts import adapter_consts
from axonius.consts.core_consts import CORE_CONFIG_NAME
from axonius.consts.gui_consts import (ENCRYPTION_KEY_PATH,
                                       EXEC_REPORT_EMAIL_CONTENT,
                                       EXEC_REPORT_FILE_NAME,
                                       EXEC_REPORT_THREAD_ID,
                                       EXEC_REPORT_TITLE, GOOGLE_KEYPAIR_FILE,
                                       LOGGED_IN_MARKER_PATH,
                                       PREDEFINED_ROLE_ADMIN,
                                       PREDEFINED_ROLE_READONLY,
                                       PREDEFINED_ROLE_RESTRICTED,
                                       RANGE_UNIT_DAYS, ROLES_COLLECTION,
                                       TEMP_MAINTENANCE_THREAD_ID,
                                       USERS_COLLECTION, ChartFuncs,
                                       ChartMetrics, ChartRangeTypes,
                                       ChartRangeUnits, ChartViews,
                                       ResearchStatus)
from axonius.consts.plugin_consts import (AGGREGATOR_PLUGIN_NAME,
                                          AXONIUS_USER_NAME,
                                          CONFIGURABLE_CONFIGS_COLLECTION,
                                          CORE_UNIQUE_NAME,
                                          DEVICE_CONTROL_PLUGIN_NAME, GUI_NAME,
                                          GUI_SYSTEM_CONFIG_COLLECTION,
                                          METADATA_PATH, NODE_ID, NODE_NAME,
                                          NODE_USER_PASSWORD, NOTES_DATA_TAG,
                                          PLUGIN_NAME, PLUGIN_UNIQUE_NAME,
                                          SYSTEM_SCHEDULER_PLUGIN_NAME,
                                          SYSTEM_SETTINGS)
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.consts.scheduler_consts import (Phases, ResearchPhases,
                                             SchedulerState)
from axonius.devices.device_adapter import DeviceAdapter
from axonius.email_server import EmailServer
from axonius.entities import AXONIUS_ENTITY_BY_CLASS
from axonius.fields import Field
from axonius.logging.metric_helper import log_metric
from axonius.mixins.configurable import Configurable
from axonius.mixins.triggerable import Triggerable
from axonius.plugin_base import EntityType, PluginBase, return_error
from axonius.thread_pool_executor import LoggedThreadPoolExecutor
from axonius.types.ssl_state import (COMMON_SSL_CONFIG_SCHEMA,
                                     COMMON_SSL_CONFIG_SCHEMA_DEFAULTS,
                                     SSLState)
from axonius.users.user_adapter import UserAdapter
from axonius.utils import gui_helpers
from axonius.utils.datetime import next_weekday, time_from_now
from axonius.utils.files import create_temp_file, get_local_config_file
from axonius.utils.gui_helpers import (Permission, PermissionLevel,
                                       PermissionType, ReadOnlyJustForGet,
                                       add_labels_to_entities,
                                       beautify_user_entry, check_permissions,
                                       deserialize_db_permissions,
                                       get_entity_labels,
                                       get_historized_filter)
from axonius.utils.mongo_administration import (get_collection_capped_size,
                                                get_collection_stats)
from axonius.utils.parsing import bytes_image_to_base64, parse_filter
from axonius.utils.threading import run_and_forget
from gui.api import API
from gui.cached_session import CachedSessionInterface
from gui.okta_login import try_connecting_using_okta
from gui.report_generator import ReportGenerator
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser

# pylint: disable=line-too-long,superfluous-parens,too-many-lines,keyword-arg-before-vararg,invalid-name,too-many-instance-attributes,inconsistent-return-statements,no-self-use,dangerous-default-value,unidiomatic-typecheck,inconsistent-return-statements,no-else-return,no-self-use,unnecessary-pass,useless-return,cell-var-from-loop,logging-not-lazy,singleton-comparison,redefined-builtin,comparison-with-callable,too-many-return-statements,too-many-boolean-expressions,logging-format-interpolation,fixme

# TODO: the following ones are real errors, we should fix them first
# pylint: disable=invalid-sequence-index,method-hidden

logger = logging.getLogger(f'axonius.{__name__}')

SAML_SETTINGS_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config', 'saml_settings.json'))

DEVICE_ADVANCED_FILEDS = ['installed_software', 'software_cves',
                          'security_patches', 'available_security_patches', 'network_interfaces',
                          'users', 'connected_hardware', 'local_admins', 'hard_drives', 'connected_devices']

USER_ADVANCED_FILEDS = ['associated_devices']


def session_connection(func, required_permissions: Iterable[Permission]):
    """
    Decorator stating that the view requires the user to be connected
    :param required_permissions: The set (or list...) of Permission required for this api call or none
    """

    def wrapper(self, *args, **kwargs):
        user = session.get('user')
        if user is None:
            return return_error('You are not connected', 401)
        permissions = user.get('permissions')
        if not check_permissions(permissions, required_permissions, request.method) and not user.get('admin'):
            return return_error('You are lacking some permissions for this request', 401)

        return func(self, *args, **kwargs)

    return wrapper


# Caution! These decorators must come BEFORE @add_rule
def gui_add_rule_logged_in(rule, required_permissions: Iterable[Permission] = None, *args, **kwargs):
    """
    A URL mapping for GUI endpoints that use the browser session for authentication,
    see add_rule_custom_authentication for more information.
    :param required_permissions: see session_connection for docs
    """
    required_permissions = set(required_permissions or [])

    def session_connection_permissions(*args, **kwargs):
        return session_connection(*args, **kwargs, required_permissions=required_permissions)

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
        for item in schema['items']:
            if item['name'] in data:
                data[item['name']] = clear_passwords_fields(data[item['name']], item)
        return data
    return data


def refill_passwords_fields(data, data_from_db):
    """
    Uses `data_from_db` to fill out "incomplete" (i.e. "unchanged") data in `data`
    """
    if data == UNCHANGED_MAGIC_FOR_GUI:
        return data_from_db
    if isinstance(data, dict):
        for key in data.keys():
            if key in data_from_db:
                data[key] = refill_passwords_fields(data[key], data_from_db[key])
        return data
    if isinstance(data, list):
        raise RuntimeError('We shouldn\'t have lists in schemas')

    return data


def filter_archived(additional_filter=None):
    """
    Returns a filter that filters out archived values
    :param additional_filter: optional - allows another filter to be made
    """
    base_non_archived = {'$or': [{'archived': {'$exists': False}}, {'archived': False}]}
    if additional_filter and additional_filter != {}:
        return {'$and': [base_non_archived, additional_filter]}
    return base_non_archived


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


class GuiService(PluginBase, Triggerable, Configurable, API):
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

    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__),
                         requested_unique_plugin_name=GUI_NAME, *args, **kwargs)
        self.__all_sessions = {}
        self.wsgi_app.session_interface = CachedSessionInterface(self.__all_sessions)

        self.wsgi_app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
        self.wsgi_app.config['SECRET_KEY'] = self.api_key  # a secret key which is used in sessions created by flask

        self._elk_addr = self.config['gui_specific']['elk_addr']
        self._elk_auth = self.config['gui_specific']['elk_auth']
        self.__users_collection = self._get_collection(USERS_COLLECTION)
        self.__roles_collection = self._get_collection(ROLES_COLLECTION)
        self._add_default_roles()
        if self._get_collection('users_config').find_one({}) is None:
            self._get_collection('users_config').insert_one({
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
        self.add_default_reports('default_reports.ini')
        self.add_default_dashboard_charts('default_dashboard_charts.ini')
        if not self.system_collection.count_documents({'type': 'server'}):
            self.system_collection.insert_one({'type': 'server', 'server_name': 'localhost'})
        if not self.system_collection.count_documents({'type': 'maintenance'}):
            self.system_collection.insert_one({
                'type': 'maintenance', 'provision': True, 'analytics': True, 'troubleshooting': True
            })

        # Start exec report scheduler
        self.exec_report_lock = threading.RLock()

        self._client_insertion_threadpool = LoggedThreadPoolExecutor(max_workers=20)  # Only for client insertion

        self._job_scheduler = LoggedBackgroundScheduler(executors={'default': ThreadPoolExecutorApscheduler(1)})
        current_exec_report_setting = self._get_exec_report_settings(self.exec_report_collection)
        if current_exec_report_setting != {}:
            self._schedule_exec_report(self.exec_report_collection, current_exec_report_setting)
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
        self.never_logged_in = True
        self.encryption_key = self.load_encryption_key()
        self.__aggregate_thread_pool = ThreadPool(processes=cpu_count())
        self._set_first_time_use()

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
                    metadata_bytes = metadata_file.read()[:-1].replace('\\', '\\\\')
                    return json.loads(metadata_bytes)
        except Exception:
            logger.exception(f'Bad __build_metadata file {metadata_bytes}')
            return ''

    def load_encryption_key(self):
        try:
            if os.path.exists(ENCRYPTION_KEY_PATH):
                with open(ENCRYPTION_KEY_PATH, 'r') as encryption_key_file:
                    encryption_key_bytes = encryption_key_file.read()[:-1].replace('\\', '\\\\')
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

    def add_default_reports(self, default_reports_ini_path):
        try:
            config = configparser.ConfigParser()
            config.read(os.path.abspath(os.path.join(os.path.dirname(__file__), f'configs/{default_reports_ini_path}')))

            for name, report in config.items():
                if name == 'DEFAULT':
                    # ConfigParser always has a fake DEFAULT key, skip it
                    continue
                try:
                    self._insert_report_config(name, report)
                except Exception as e:
                    logger.exception(f'Error adding default report {name}. Reason: {repr(e)}')
        except Exception as e:
            logger.exception(f'Error adding default reports. Reason: {repr(e)}')

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
                    self._insert_dashboard_chart(name, data['metric'], data['view'], json.loads(data['config']))
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

    def _insert_report_config(self, name, report):
        reports_collection = self._get_collection('reports_config')
        existed_report = reports_collection.find_one({'name': name})
        if existed_report is not None and not existed_report.get('archived'):
            logger.info(f'Report {name} already exists under id: {existed_report["_id"]}')
            return

        result = reports_collection.replace_one({'name': name},
                                                {'name': name, 'adapters': json.loads(report['adapters'])}, upsert=True)
        logger.info(f'Added report {name} id: {result.upserted_id}')

    def _insert_dashboard_chart(self, dashboard_name, dashboard_metric, dashboard_view, dashboard_data):
        dashboard_collection = self._get_collection('dashboard')
        existed_dashboard_chart = dashboard_collection.find_one({'name': dashboard_name})
        if existed_dashboard_chart is not None and not existed_dashboard_chart.get('archived'):
            logger.info(f'Report {dashboard_name} already exists under id: {existed_dashboard_chart["_id"]}')
            return

        result = dashboard_collection.replace_one({'name': dashboard_name},
                                                  {'name': dashboard_name,
                                                   'metric': dashboard_metric,
                                                   'view': dashboard_view,
                                                   'config': dashboard_data}, upsert=True)
        logger.info(f'Added report {dashboard_name} id: {result.upserted_id}')

    def _set_first_time_use(self):
        """
        Check the clients db of each registered adapter to determine if there is any connected adapter.
        We regard no connected adapters as a fresh system, that should offer user a tutorial.
        Answer is saved in a private member that is read by the frontend via a designated endpoint.

        """
        plugins_available = self.get_available_plugins_from_core()
        self.__is_system_first_use = True
        with self._get_db_connection() as db_connection:
            adapters_from_db = db_connection['core']['configs'].find({
                'plugin_type': {
                    '$in': [
                        'Adapter', 'ScannerAdapter'
                    ]
                }
            }).sort([(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
            for adapter in adapters_from_db:
                if adapter[PLUGIN_UNIQUE_NAME] in plugins_available and db_connection[adapter[PLUGIN_UNIQUE_NAME]][
                        'clients'].count_documents({}):
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
        return self._get_appropriate_view(history_date, entity_type). \
            find_one(get_historized_filter(
                {
                    'internal_axon_id': entity_id
                },
                history_date), projection=projection)

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

        def _basic_generic_field_names():
            return filter(lambda field: field != 'adapters' and field != 'labels' and
                          not any([category in field.split('.') for category in advanced_fields]),
                          list(map(lambda field: field.get('name'), gui_helpers.entity_fields(entity_type)['generic'])))

        entity = self._fetch_historical_entity(entity_type, entity_id, history_date, projection={
            'adapters_data': 0
        })
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

        # Specific is returned as is, to show all adapter datas.
        # Generic fields are divided to basic which are all merged through all adapter datas
        # and advanced, of which the main field is merged and data is given in original structure.
        return jsonify({
            'specific': entity['specific_data'],
            'generic': {
                'basic': gui_helpers.parse_entity_fields(entity, _basic_generic_field_names()),
                'advanced': [{
                    'name': category, 'data': gui_helpers.find_entity_field(entity, f'specific_data.data.{category}')
                } for category in advanced_fields],
                'data': entity['generic_data']
            },
            'labels': entity['labels'],
            'internal_axon_id': entity['internal_axon_id'],
            'accurate_for_datetime': entity.get('accurate_for_datetime', None)
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

    def _find_entities_by_uuid_for_adapter_with_feature(self, entities_selection, feature, entity_type: EntityType, mongo_filter):
        """
        Find all entity from adapters that have a given feature, from a given set of entities
        :return: plugin_unique_names of entity with given features, dict of plugin_unique_name -> id of adapter entity
        """
        with self._get_db_connection() as db_connection:
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

    def _entity_views(self, method, entity_type: EntityType, limit, skip, mongo_filter):
        """
        Save or fetch views over the entities db
        :return:
        """
        entity_views_collection = self.gui_dbs.entity_query_views_db_map[entity_type]
        if method == 'GET':
            mongo_filter = filter_archived(mongo_filter)
            fielded_plugins = self._entity_views_db_map[entity_type].distinct(f'specific_data.{PLUGIN_NAME}')

            def _validate_adapters_used(view):
                if not view.get('predefined'):
                    return True
                for expression in view['view']['query'].get('expressions', []):
                    adapter_matches = re.findall(r'adapters_data\.(\w*)\.', expression.get('field', ''))
                    if adapter_matches and list(filter(lambda x: x not in fielded_plugins, adapter_matches)):
                        return False
                return True

            # Fetching views according to parameters given to the method
            all_views = entity_views_collection.find(mongo_filter).sort([('timestamp', pymongo.DESCENDING)]).skip(
                skip).limit(limit)
            logger.info('Filtering views that use fields from plugins without persisted fields schema')
            logger.info(f'Remaining plugins include: {fielded_plugins}')
            # Returning only the views that do not contain fields whose plugin has no field schema saved
            return [gui_helpers.beautify_db_entry(entry) for entry in filter(_validate_adapters_used, all_views)]

        if method == 'POST':
            view_data = self.get_request_data_as_object()
            if not view_data.get('name'):
                return return_error(f'Name is required in order to save a view', 400)
            if not view_data.get('view'):
                return return_error(f'View data is required in order to save one', 400)
            view_data['timestamp'] = datetime.now()
            update_result = entity_views_collection.replace_one({'name': view_data['name']}, view_data, upsert=True)
            if not update_result.upserted_id and not update_result.modified_count:
                return return_error(f'View named {view_data.name} was not saved', 400)

            entity = entity_views_collection.find_one({'name': view_data['name']})
            return str(entity.get('_id'))

        if method == 'DELETE':
            query_ids = self.get_request_data_as_object()
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
            '$in': self.__get_selected_internal_axon_ids(entities_selection, entity_type, mongo_filter)
        }})
        self._request_db_rebuild(
            sync=True, internal_axon_ids=entities_selection['ids'] if entities_selection['include'] else None)

        return '', 200

    def __get_selected_internal_axon_ids(self, entities_selection, entity_type: EntityType, mongo_filter):
        """

        :param entities_selection: Represents the selection of entities.
                If include is True, then ids is the list of selected internal axon ids
                Otherwise, selected internal axon ids are all those fetched by the mongo filter excluding the ids list
        :param entity_type: Type of entity to fetch
        :param mongo_filter: Query to fetch entire data by
        :return: List of internal axon ids that were meant to be selected, according to given selection and filter
        """
        if entities_selection['include']:
            return entities_selection['ids']
        else:
            return [entry['internal_axon_id'] for entry in self._entity_views_db_map[entity_type].find({
                '$and': [
                    {'internal_axon_id': {
                        '$nin': entities_selection['ids']
                    }}, mongo_filter
                ]
            }, projection={'internal_axon_id': 1})]

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
            log_metric(logger, 'query.gui', filter_obj)

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
                '$in': self.__get_selected_internal_axon_ids(post_data['selection'], entity_type, mongo_filter)
            }
        }, projection={
            'internal_axon_id': True,
            f'adapters.{PLUGIN_UNIQUE_NAME}': True,
            'adapters.data.id': True
        }))

        entity_to_add = self._new_device_adapter() if entity_type == EntityType.Devices else self._new_user_adapter()
        for k, v in post_data['data'].items():
            allowed_types = [str, int, bool, float]
            if type(v) not in allowed_types:
                return return_error(f'{k} is of type {type(v)} which is not allowed')
            if not entity_to_add.set_static_field(k, v):
                # Save the field with a canonized name and title as received
                new_field_name = '_'.join(k.split(' ')).lower()
                entity_to_add.declare_new_field(new_field_name, Field(type(v), k))
                setattr(entity_to_add, new_field_name, v)

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

            pool.map_async(tag_adapter, entities).get()

        self._save_field_names_to_db(entity_type)
        self._request_db_rebuild(sync=True, internal_axon_ids=[x['internal_axon_id'] for x in entities])

    ##########
    # DEVICE #
    ##########

    @gui_helpers.historical()
    @gui_helpers.paginated()
    @gui_helpers.filtered()
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
    @gui_helpers.filtered()
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

    @gui_helpers.historical()
    @gui_add_rule_logged_in('devices/<device_id>', methods=['GET'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadOnly)})
    def device_by_id(self, device_id, history: datetime):
        return self._device_entity_by_id(device_id, history_date=history)

    @gui_helpers.filtered()
    @gui_helpers.historical()
    @gui_add_rule_logged_in('devices/count', required_permissions={Permission(PermissionType.Devices,
                                                                              PermissionLevel.ReadOnly)})
    def get_devices_count(self, mongo_filter, history: datetime):
        return gui_helpers.get_entities_count(mongo_filter, self._get_appropriate_view(history, EntityType.Devices),
                                              history_date=history)

    @gui_add_rule_logged_in('devices/fields', required_permissions={Permission(PermissionType.Devices,
                                                                               PermissionLevel.ReadOnly)})
    def device_fields(self):
        return jsonify(gui_helpers.entity_fields(EntityType.Devices))

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_add_rule_logged_in('devices/views', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             ReadOnlyJustForGet)})
    def device_views(self, limit, skip, mongo_filter):
        """
        Save or fetch views over the devices db
        :return:
        """
        return jsonify(self._entity_views(request.method, EntityType.Devices, limit, skip, mongo_filter))

    @gui_helpers.filtered()
    @gui_add_rule_logged_in('devices/labels', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             ReadOnlyJustForGet)})
    def device_labels(self, mongo_filter):
        return self._entity_labels(self.devices_db_view, self.devices, mongo_filter)

    @gui_helpers.filtered()
    @gui_add_rule_logged_in('devices/disable', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadWrite)})
    def disable_device(self, mongo_filter):
        return self._disable_entity(EntityType.Devices, mongo_filter)

    @gui_add_rule_logged_in('devices/<device_id>/notes', methods=['PUT', 'DELETE'],
                            required_permissions={Permission(PermissionType.Devices, PermissionLevel.ReadWrite)})
    def device_notes(self, device_id):
        return self._entity_notes(EntityType.Devices, device_id)

    @gui_add_rule_logged_in('devices/<device_id>/notes/<note_id>', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadWrite)})
    def device_notes_update(self, device_id, note_id):
        return self._entity_notes_update(EntityType.Devices, device_id, note_id)

    @gui_helpers.filtered()
    @gui_add_rule_logged_in('devices/custom', methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadWrite)})
    def devices_custom_Data(self, mongo_filter):
        """
        See self._entity_custom_data
        """
        self._entity_custom_data(EntityType.Devices, mongo_filter)
        return '', 200

    #########
    # USER #
    #########

    @gui_helpers.historical()
    @gui_helpers.paginated()
    @gui_helpers.filtered()
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
    @gui_helpers.filtered()
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

    @gui_helpers.historical()
    @gui_add_rule_logged_in('users/<user_id>', methods=['GET'], required_permissions={Permission(PermissionType.Users,
                                                                                                 PermissionLevel.ReadOnly)})
    def user_by_id(self, user_id, history: datetime):
        return self._user_entity_by_id(user_id, history_date=history)

    @gui_helpers.historical()
    @gui_helpers.filtered()
    @gui_add_rule_logged_in('users/count', required_permissions={Permission(PermissionType.Users,
                                                                            PermissionLevel.ReadOnly)})
    def get_users_count(self, mongo_filter, history: datetime):
        return gui_helpers.get_entities_count(mongo_filter, self._get_appropriate_view(history, EntityType.Users),
                                              history_date=history)

    @gui_add_rule_logged_in('users/fields', required_permissions={Permission(PermissionType.Users,
                                                                             PermissionLevel.ReadOnly)})
    def user_fields(self):
        return jsonify(gui_helpers.entity_fields(EntityType.Users))

    @gui_helpers.filtered()
    @gui_add_rule_logged_in('users/disable', methods=['POST'], required_permissions={Permission(PermissionType.Users,
                                                                                                PermissionLevel.ReadWrite)})
    def disable_user(self, mongo_filter):
        return self._disable_entity(EntityType.Users, mongo_filter)

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_add_rule_logged_in('users/views', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Users,
                                                             ReadOnlyJustForGet)})
    def user_views(self, limit, skip, mongo_filter):
        return jsonify(self._entity_views(request.method, EntityType.Users, limit, skip, mongo_filter))

    @gui_helpers.filtered()
    @gui_add_rule_logged_in('users/labels', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Users,
                                                             ReadOnlyJustForGet)})
    def user_labels(self, mongo_filter):
        return self._entity_labels(self.users_db_view, self.users, mongo_filter)

    @gui_add_rule_logged_in('users/<user_id>/notes', methods=['PUT', 'DELETE'],
                            required_permissions={Permission(PermissionType.Users, PermissionLevel.ReadWrite)})
    def user_notes(self, user_id):
        return self._entity_notes(EntityType.Users, user_id)

    @gui_add_rule_logged_in('users/<user_id>/notes/<note_id>', methods=['POST'],
                            required_permissions={Permission(PermissionType.Users,
                                                             PermissionLevel.ReadWrite)})
    def user_notes_update(self, user_id, note_id):
        return self._entity_notes_update(EntityType.Users, user_id, note_id)

    @gui_helpers.filtered()
    @gui_add_rule_logged_in('users/custom', methods=['POST'],
                            required_permissions={Permission(PermissionType.Users,
                                                             PermissionLevel.ReadWrite)})
    def users_custom_data(self, mongo_filter):
        """
        See self._entity_custom_data
        """
        self._entity_custom_data(EntityType.Users, mongo_filter)
        return '', 200

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
        """
        Get all adapters from the core
        :return:
        """
        plugins_available = self.get_available_plugins_from_core()
        with self._get_db_connection() as db_connection:
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

                clients_collection = db_connection[adapter_name]['clients']
                schema = self._get_plugin_schemas(db_connection, adapter_name).get('clients')
                nodes_metadata_collection = db_connection['core']['nodes_metadata']
                if not schema:
                    # there might be a race - in the split second that the adapter is up
                    # but it still hasn't written it's schema
                    continue

                clients = [gui_helpers.beautify_db_entry(client) for client in clients_collection.find()
                           .sort([('_id', pymongo.DESCENDING)])]
                for client in clients:
                    client['client_config'] = clear_passwords_fields(client['client_config'], schema)
                    client[NODE_ID] = adapter[NODE_ID]
                status = ''
                if len(clients):
                    clients_connected = clients_collection.count_documents({'status': 'success'})
                    status = 'success' if len(clients) == clients_connected else 'warning'

                node_name = nodes_metadata_collection.find_one(
                    {NODE_ID: adapter[NODE_ID]})

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

            return jsonify(adapters)

    @gui_add_rule_logged_in('adapter_features')
    def adapter_features(self):
        """
        Getting the features of each registered adapter, as they are saved in core's "configs" db.
        This is needed for the case that user has permissions to disable entities but is restricted from adapters.
        The user would need to know which entities can be disabled, according to the features of their adapters.

        :return: Dict between unique plugin name of the adapter and their list of features
        """
        plugins_available = self.get_available_plugins_from_core()
        with self._get_db_connection() as db_connection:
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
        if response.status_code == 200:
            self._client_insertion_threadpool.submit(self._fetch_after_clients_thread, adapter_unique_name,
                                                     response.json()['client_id'], clients)
        return response.text, response.status_code

    def _fetch_after_clients_thread(self, adapter_unique_name, client_id, client_to_add):
        # if there's no aggregator, that's fine
        try:
            logger.info(f'Stopping research phase after adding client {client_id}')
            response = self.request_remote_plugin('stop_all', SYSTEM_SCHEDULER_PLUGIN_NAME, 'POST')
            response.raise_for_status()
            logger.info(f'Requesting {adapter_unique_name} to fetch data from newly added client {client_id}')
            response = self.request_remote_plugin(f'trigger/insert_to_db',
                                                  adapter_unique_name, method='POST',
                                                  json={
                                                      'client_name': client_id
                                                  })
            logger.info(f'{adapter_unique_name} finished fetching data for {client_id}')
            if not (response.status_code == 400 and response.json()['message'] == 'Gracefully stopped'):
                response.raise_for_status()
                response = self.request_remote_plugin('trigger/execute?blocking=False',
                                                      SYSTEM_SCHEDULER_PLUGIN_NAME,
                                                      'POST')
                response.raise_for_status()
        except Exception:
            # if there's no aggregator, there's nothing we can do
            logger.exception(f'Error fetching devices from {adapter_unique_name} for client {client_to_add}')
            pass
        return

    @gui_add_rule_logged_in('adapters/<adapter_unique_name>/upload_file', methods=['POST'],
                            required_permissions={Permission(PermissionType.Adapters,
                                                             PermissionLevel.ReadWrite)})
    def adapter_upload_file(self, adapter_unique_name):
        return self._upload_file(adapter_unique_name)

    def _upload_file(self, plugin_unique_name):
        field_name = request.form.get('field_name')
        if not field_name:
            return return_error('Field name must be specified', 401)
        file = request.files.get('userfile')
        if not file or file.filename == '':
            return return_error('File must exist', 401)
        filename = file.filename
        with self._get_db_connection() as db_connection:
            fs = gridfs.GridFS(db_connection[plugin_unique_name])
            written_file = fs.put(file, filename=filename)
        return jsonify({'uuid': str(written_file)})

    @gui_add_rule_logged_in('adapters/<adapter_name>/clients', methods=['PUT', 'POST'],
                            required_permissions={Permission(PermissionType.Adapters,
                                                             PermissionLevel.ReadWrite)})
    def adapters_clients(self, adapter_name):
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
            self.__is_system_first_use = False
            return self._query_client_for_devices(adapter_unique_name, clients)
        else:
            return self._test_client_connectivity(adapter_unique_name)

    @gui_add_rule_logged_in('adapters/<adapter_name>/clients/<client_id>',
                            methods=['PUT', 'DELETE'], required_permissions={Permission(PermissionType.Adapters,
                                                                                        PermissionLevel.ReadWrite)})
    def adapters_clients_update(self, adapter_name, client_id=None):
        """
        Create or delete credential sets (clients) in the adapter
        :param adapter_unique_name: the adapter to refer to
        :param client_id: UUID of client to delete if DELETE is used
        :return:
        """
        data = self.get_request_data_as_object()
        node_id = data.pop('instanceName', self.node_id)
        old_node_id = data.pop('oldInstanceName', None)

        adapter_unique_name = self.request_remote_plugin(
            f'find_plugin_unique_name/nodes/{old_node_id or node_id}/plugins/{adapter_name}').json().get('plugin_unique_name')
        if request.method == 'DELETE':
            delete_entities = request.args.get('deleteEntities', False)
            self.delete_client_data(adapter_unique_name, client_id,
                                    data.get('nodeId', None), delete_entities)

        client_from_db = self._get_collection('clients', adapter_unique_name).find_one({'_id': ObjectId(client_id)})
        self.request_remote_plugin('clients/' + client_id, adapter_unique_name, method='delete')

        if request.method == 'PUT':
            if old_node_id != node_id:
                adapter_unique_name = self.request_remote_plugin(
                    f'find_plugin_unique_name/nodes/{node_id}/plugins/{adapter_name}').json().get(
                        'plugin_unique_name')

            return self._query_client_for_devices(adapter_unique_name, data,
                                                  data_from_db_for_unchanged=client_from_db)

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
                entities_to_rebuild = []
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

                    to_rebuild = list(self._entity_db_map[entity_type].find(
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
                        projection={'internal_axon_id': 1}
                    ))

                    logger.info(f'Set pending_delete on {res.modified_count} axonius entities '
                                f'(or some adapters in them) ' +
                                f'from {res.matched_count} matches, rebuilding {len(to_rebuild)} entities')

                    if not to_rebuild:
                        continue

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

                            pool.map_async(delete_adapters, entities_to_delete).get()

                        self._request_db_rebuild(sync=True)

                    # while we can quickly mark all adapters to be pending_delete
                    # we still want to run a background task to delete them
                    run_and_forget(lambda: async_delete_entities(entity_type, entities_to_pass_to_be_deleted))

                    entities_to_rebuild += to_rebuild

                if entities_to_rebuild:
                    self._request_db_rebuild(sync=True,
                                             internal_axon_ids=[x['internal_axon_id'] for x in entities_to_rebuild])
            return client_from_db

    def run_actions(self, action_data, mongo_filter):
        # The format of data is defined in device_control\service.py::run_shell
        action_type = action_data['action_type']
        entities_selection = action_data['entities']
        action_data['internal_axon_ids'] = entities_selection['ids'] if entities_selection['include'] else [
            str(entry['internal_axon_id']) for entry in self.devices_db_view.find({
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
            response = self.request_remote_plugin('run_action', self.device_control_plugin, 'post', json=action_data)
            if response.status_code != 200:
                message = f'Running action {action_type} failed because {str(json.loads(response.content)["message"])}'
                logger.error(message)
                return return_error(message, 400)
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
        return self._upload_file(self.device_control_plugin)

    def get_alerts(self, limit, mongo_filter, mongo_projection, mongo_sort, skip):
        sort = []
        for field, direction in mongo_sort.items():
            sort.append((field, direction))
        if not sort:
            sort.append(('report_creation_time', pymongo.DESCENDING))
        return [gui_helpers.beautify_db_entry(report) for report in self.reports_collection.find(
            mongo_filter, projection=mongo_projection).sort(sort).skip(skip).limit(limit)]

    def put_alert(self, report_to_add):
        view_name = report_to_add['view']
        entity = EntityType(report_to_add['viewEntity'])
        views_collection = self.gui_dbs.entity_query_views_db_map[entity]
        if views_collection.find_one({'name': view_name}) is None:
            return return_error(f'Missing view {view_name} requested for creating alert')
        response = self.request_remote_plugin('reports', 'reports', method='put', json=report_to_add)
        return response.text, response.status_code

    def delete_alert(self, alert_selection):
        # Since other method types cause the function to return - here we have DELETE request
        if alert_selection is None or (not alert_selection.get('ids')
                                       and alert_selection.get('include')):
            logger.error('No alert provided to be deleted')
            return ''

        response = self.request_remote_plugin('reports', 'reports', method='DELETE',
                                              json=alert_selection['ids'] if alert_selection['include'] else [
                                                  str(report['_id']) for report in self.reports_collection.find(
                                                      {}, projection={'_id': 1}) if str(report['_id'])
                                                  not in alert_selection['ids']])
        if response is None:
            return return_error('No response whether alert was removed')
        return response.text, response.status_code

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_add_rule_logged_in('alert', methods=['GET', 'PUT', 'DELETE'],
                            required_permissions={Permission(PermissionType.Alerts,
                                                             ReadOnlyJustForGet)})
    def alert(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        """
        GET results in list of all currently configured alerts, with their query id they were created with
        PUT Send report_service a new report to be configured

        :return:
        """
        if request.method == 'GET':
            return jsonify(self.get_alerts(limit, mongo_filter, mongo_projection, mongo_sort, skip))

        if request.method == 'PUT':
            report_to_add = request.get_json(silent=True)
            return self.put_alert(report_to_add)

        alert_selection = self.get_request_data_as_object()
        return self.delete_alert(alert_selection)

    @gui_helpers.filtered()
    @gui_add_rule_logged_in('alert/count', required_permissions={Permission(PermissionType.Alerts,
                                                                            PermissionLevel.ReadOnly)})
    def alert_count(self, mongo_filter):
        with self._get_db_connection() as db_connection:
            report_service = self.get_plugin_by_name('reports')[PLUGIN_UNIQUE_NAME]
            return jsonify(db_connection[report_service]['reports'].count_documents(mongo_filter))

    @gui_add_rule_logged_in('alert/<alert_id>', methods=['POST'],
                            required_permissions={Permission(PermissionType.Alerts,
                                                             PermissionLevel.ReadWrite)})
    def alerts_update(self, alert_id):
        """

        :param alert_id:
        :return:
        """
        alert_to_update = request.get_json(silent=True)
        view_name = alert_to_update['view']
        view_entity = alert_to_update['viewEntity']
        assert view_entity in [x.value for x in EntityType.__members__.values()]
        views = self.gui_dbs.entity_query_views_db_map[EntityType(view_entity)]
        if views.find_one({'name': view_name}) is None:
            return return_error(f'Missing view {view_name} requested for updating alert')

        response = self.request_remote_plugin(f'reports/{alert_id}', 'reports', method='post',
                                              json=alert_to_update)
        if response is None:
            return return_error('No response whether alert was updated')

        return response.text, response.status_code

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
        with self._get_db_connection() as db_connection:
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
                            required_permissions={Permission(PermissionType.Settings,
                                                             ReadOnlyJustForGet)})
    def plugins_configs_set(self, plugin_name, config_name):
        """
        Set a specific config on a specific plugin
        """
        if request.method == 'POST':
            config_to_set = request.get_json(silent=True)
            if config_to_set is None:
                return return_error('Invalid config', 400)
            email_settings = config_to_set.get('email_settings')
            if plugin_name == 'core' and config_name == CORE_CONFIG_NAME and email_settings and email_settings.get(
                    'enabled') is True:

                if not email_settings.get('smtpHost') or not email_settings.get('smtpPort'):
                    return return_error('Host and Port are required to connect to email server', 400)
                email_server = EmailServer(email_settings['smtpHost'], email_settings['smtpPort'],
                                           email_settings.get('smtpUser'), email_settings.get('smtpPassword'),
                                           ssl_state=SSLState[email_settings.get('use_ssl', SSLState.Unencrypted.name)],
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
            self._update_plugin_config(plugin_name, config_name, config_to_set)
            return ''
        if request.method == 'GET':
            with self._get_db_connection() as db_connection:
                config_collection = db_connection[plugin_name][CONFIGURABLE_CONFIGS_COLLECTION]
                schema_collection = db_connection[plugin_name]['config_schemas']
                return jsonify({'config': config_collection.find_one({'config_name': config_name})['config'],
                                'schema': schema_collection.find_one({'config_name': config_name})['schema']})

    @gui_add_rule_logged_in('configuration', methods=['GET'])
    def system_config(self):
        """
        Get only the GUIs settings as well as whether Mail Server and Syslog Server are enabled.
        This is needed for the case that user is restricted from the settings but can view pages that use them.
        They pages should render the same, so these settings must be permitted to read anyway.

        :return: Settings for the system and Global settings, indicating if Mail and Syslog are enabled
        """
        return jsonify({
            'system': self._system_settings, 'global': {
                'mail': self._email_settings['enabled'] if self._email_settings else False,
                'syslog': self._syslog_settings['enabled'] if self._system_settings else False
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
        with self._get_db_connection() as db_connection:
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
                            required_permissions={Permission(PermissionType.Dashboard,
                                                             ReadOnlyJustForGet)})
    def notifications(self, limit, skip, mongo_filter, mongo_sort):
        """
        Get all notifications
        :param limit: limit for pagination
        :param skip: start index for pagination
        :return:
        """
        with self._get_db_connection() as db:
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
                            required_permissions={Permission(PermissionType.Dashboard,
                                                             PermissionLevel.ReadOnly)})
    def notifications_count(self, mongo_filter):
        """
        Fetches from core's notification collection, according to given mongo_filter,
        and counts how many entries in retrieved cursor
        :param mongo_filter: Generated by the filtered() decorator, according to uri param "filter"
        :return: Number of notifications matching given filter
        """
        with self._get_db_connection() as db:
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
        with self._get_db_connection() as db:
            notification_collection = db['core']['notifications']
            return jsonify(
                gui_helpers.beautify_db_entry(notification_collection.find_one({'_id': ObjectId(notification_id)})))

    @gui_helpers.add_rule_unauth('get_login_options')
    def get_login_options(self):
        return jsonify({
            'okta': {
                'enabled': self.__okta['enabled'],
                'client_id': self.__okta['client_id'],
                'url': self.__okta['url'],
                'gui2_url': self.__okta['gui2_url']
            },
            'google': {
                'enabled': self.__google['enabled'],
                'client': self.__google['client']
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
                return return_error('', 401)
            if 'pic_name' not in user:
                user['pic_name'] = self.DEFAULT_AVATAR_PIC
            user = dict(user)
            user['permissions'] = {
                k.name: v.name for k, v in user['permissions'].items()
            }
            log_metric(logger, 'LOGIN_MARKER', 0)
            return jsonify(beautify_user_entry(user)), 200

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
        if self.never_logged_in:
            logger.info('First login occurred.')
            LOGGED_IN_MARKER_PATH.touch()
        user = dict(user)
        user['permissions'] = deserialize_db_permissions(user['permissions'])
        session['user'] = user
        session.permanent = remember_me

    def __exteranl_login_successful(self, source: str,
                                    username: str,
                                    first_name: str = None,
                                    last_name: str = None,
                                    picname: str = None,
                                    remember_me: bool = False):
        """
        Our system supports external login systems, such as LDAP, Okta and Google.
        To generically support such systems with our permission model we must normalize the login mechanism.
        Once the code that handles the login with the external source finishes it must call this method
        to finalize the login.
        :param source: the name of the service that made the connection, i.e. 'Google'
        :param username: the username from the service, could also be an email
        :param first_name: the first name of the user (optional)
        :param last_name: the last name of the user (optional)
        :param picname: the URL of the avatar of the user (optional)
        :param remember_me: whether or not to remember the session after the browser has been closed
        :return: None
        """
        role_name = None
        config_doc = self._get_collection('users_config').find_one({})
        if config_doc and config_doc.get('external_default_role'):
            role_name = config_doc['external_default_role']
        user = self.__create_user_if_doesnt_exist(username, first_name, last_name, picname, source, role_name=role_name)
        self.__perform_login_with_user(user, remember_me)

    def __create_user_if_doesnt_exist(self, username, first_name, last_name, picname=None, source='internal',
                                      password=None, role_name=None):
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
                'api_secret': secrets.token_urlsafe()
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
        okta_settings = self.__okta
        if not okta_settings['enabled']:
            return return_error('Okta login is disabled', 400)
        claims = try_connecting_using_okta(okta_settings)
        if claims:
            # Notice! If you change the first parameter, then our CURRENT customers will have their
            # users re-created next time they log in. This is bad! If you change this, please change
            # the upgrade script as well.
            self.__exteranl_login_successful(
                'okta',  # Look at the comment above
                claims['email'],
                claims.get('given_name', ''),
                claims.get('family_name', '')
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

            user = conn.get_user(user_name)
            if not user:
                return return_error('Failed login')

            needed_group = ldap_login['group_cn']
            if needed_group:
                # This does not check for nested groups. see AX-2339
                groups = user.get('memberOf', [])
                if not any((f'CN={needed_group}' in group) for group in groups):
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

    @gui_helpers.add_rule_unauth('login/google', methods=['POST'])
    def google_login(self):
        """
        Login with google
        """
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as google_requests
        except ImportError:
            return return_error('Import error, Google login isn\'t available')
        google_creds = self.__google

        if not google_creds['enabled']:
            return return_error('Google login is disabled', 400)

        log_in_data = self.get_request_data_as_object()
        if log_in_data is None:
            return return_error('No login data provided', 400)

        token = log_in_data.get('id_token')
        if token is None:
            return return_error('No id_token provided', 400)

        try:
            # Specify the CLIENT_ID of the app that accesses the backend:
            idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), google_creds['client'])

            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')

            # If auth request is from a G Suite domain:
            if google_creds['allowed_domain'] and idinfo.get('hd') != google_creds['allowed_domain']:
                return return_error('Wrong hosted domain.')

            if google_creds['allowed_group']:
                user_id = idinfo.get('sub')
                if not user_id:
                    return return_error('No user id present')
                auth_file = json.loads(self._grab_file_contents(google_creds[GOOGLE_KEYPAIR_FILE]))
                from axonius.clients.g_suite_admin_connection import GSuiteAdminConnection
                connection = GSuiteAdminConnection(auth_file, google_creds['account_to_impersonate'],
                                                   ['https://www.googleapis.com/auth/admin.directory.group.readonly'])
                if not any(google_creds['allowed_group'] in group.get('name', '')
                           for group
                           in connection.get_user_groups(user_id)):
                    return return_error(f'You\'re not in the allowed group {google_creds["allowed_group"]}')

            # ID token is valid. Get the user's Google Account ID from the decoded token.
            # Notice! If you change the first parameter, then our CURRENT customers will have their
            # users re-created next time they log in. This is bad! If you change this, please change
            # the upgrade script as well.
            self.__exteranl_login_successful('google',  # look at the comment above
                                             idinfo.get('name') or 'unamed',
                                             idinfo.get('given_name') or 'unamed',
                                             idinfo.get('family_name') or 'unamed',
                                             idinfo.get('picture') or self.DEFAULT_AVATAR_PIC)
            return ''
        except ValueError:
            logger.exception('Invalid token')
            return return_error('Invalid token')
        except Exception:
            logger.exception('Unknown exception')
            return return_error('Error logging in, please try again')

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
                            required_permissions={Permission(PermissionType.Settings,
                                                             PermissionLevel.ReadWrite)})
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
        if self.__users_collection.find_one(filter_archived({
                'user_name': post_data['user_name'],
                'source': 'internal'})):
            return return_error('User already exists', 400)
        self.__create_user_if_doesnt_exist(post_data['user_name'], post_data['first_name'], post_data['last_name'],
                                           picname=None, source='internal', password=post_data['password'],
                                           role_name=post_data.get('role_name'))
        return ''

    @gui_add_rule_logged_in('system/users/<user_id>/password', methods=['POST'])
    def system_users_password(self, user_id):
        """
        Change a password for a specific user. It must be the same user as currently logged in to the system.
        Post data is expected to have the old password, matching the one in the DB

        :param user_id:
        :return:
        """
        post_data = self.get_request_data_as_object()
        user = session.get('user')
        if str(user['_id']) != user_id:
            return return_error('Login to your user first')
        if not bcrypt.verify(post_data['old'], user['password']):
            return return_error('Given password is wrong')

        self.__users_collection.update({'_id': ObjectId(user_id)},
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
        self.__users_collection.update({'_id': ObjectId(user_id)},
                                       {'$set': post_data})
        self.__invalidate_sessions(user_id)
        return ''

    @gui_add_rule_logged_in('system/users/<user_id>', methods=['DELETE'],
                            required_permissions={Permission(PermissionType.Settings,
                                                             PermissionLevel.ReadWrite)})
    def system_users_delete(self, user_id):
        """
        Allows changing a users' permission set
        """
        self.__users_collection.update({'_id': ObjectId(user_id)},
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
            config_doc = self._get_collection('users_config').find_one({})
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
        self._get_collection('users_config').replace_one({}, {
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
        return jsonify(constants)

    def __invalidate_sessions(self, user_id: str):
        """
        Invalidate all sessions for this user except the current one
        :param user_name: username to invalidate all sessions for
        :return:
        """
        for k, v in self.__all_sessions.items():
            if k == session.sid:
                continue
            d = v.get('d')
            if not d:
                continue
            if d.get('user') and str(d['user'].get('_id')) == user_id:
                d['user'] = None

    @gui_add_rule_logged_in('api_key', methods=['GET', 'POST'])
    def api_creds(self):
        """
        Get or change the API key
        """
        if request.method == 'POST':
            new_token = secrets.token_urlsafe()
            new_api_key = secrets.token_urlsafe()
            self.__users_collection.update(
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

    @gui_helpers.paginated()
    @gui_add_rule_logged_in('logs')
    def logs(self, limit, skip):
        """
        Maybe this should be datewise paginated, perhaps the whole scheme will change.
        :param limit: pagination
        :param skip:
        :return:
        """
        es = Elasticsearch(hosts=[self._elk_addr], http_auth=self._elk_auth)
        res = es.search(index='logstash-*', doc_type='logstash-log',
                        body={'size': limit,
                              'from': skip,
                              'sort': [{'@timestamp': {'order': 'desc'}}]})
        return jsonify(res['hits']['hits'])

    #############
    # DASHBOARD #
    #############

    @gui_add_rule_logged_in('dashboard/first_use', methods=['GET'])
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

        card = self._get_collection('dashboard').find_one({'_id': ObjectId(card_uuid)})
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

    @gui_add_rule_logged_in('first_historical_date', methods=['GET'],
                            required_permissions={Permission(PermissionType.Dashboard,
                                                             PermissionLevel.ReadOnly)})
    def first_historical_date(self):
        dates = {}
        for entity_type in EntityType:
            historical_for_entity = self._historical_entity_views_db_map[entity_type].find_one({}, sort=[(
                'accurate_for_datetime', 1)], projection=['accurate_for_datetime'])
            if historical_for_entity:
                dates[entity_type.value] = historical_for_entity['accurate_for_datetime']

        return jsonify(dates)

    @gui_add_rule_logged_in('get_allowed_dates', required_permissions=[Permission(PermissionType.Dashboard,
                                                                                  PermissionLevel.ReadOnly)])
    def all_historical_dates(self):
        dates = {}
        for entity_type in EntityType:
            entity_dates = self._historical_entity_views_db_map[entity_type].distinct('accurate_for_datetime')
            dates[entity_type.value] = {x.date().isoformat(): x.isoformat() for x in entity_dates}
        return jsonify(dates)

    @gui_helpers.paginated()
    @gui_add_rule_logged_in('dashboard', methods=['POST', 'GET'],
                            required_permissions={Permission(PermissionType.Dashboard,
                                                             ReadOnlyJustForGet)})
    def get_dashboard(self, skip, limit):
        if request.method == 'GET':
            return jsonify(self._get_dashboard(skip, limit))

        # Handle 'POST' request method - save dashboard configuration
        dashboard_data = self.get_request_data_as_object()
        if not dashboard_data.get('name'):
            return return_error('Name required in order to save Dashboard Chart', 400)
        if not dashboard_data.get('config'):
            return return_error('At least one query required in order to save Dashboard Chart', 400)
        update_result = self._get_collection('dashboard').replace_one(
            {'name': dashboard_data['name']}, dashboard_data, upsert=True)
        if not update_result.upserted_id and not update_result.modified_count:
            return return_error('Error saving dashboard chart', 400)
        return str(update_result.upserted_id)

    def _get_dashboard(self, skip=0, limit=0):
        """
        GET Fetch current dashboard chart definitions. For each definition, fetch each of it's views and
        fetch devices_db_view with their view. Amount of results is mapped to each views' name, under 'data' key,
        to be returned with the dashboard definition.

        POST Save a new dashboard chart definition, given it has a name and at least one query attached

        :return:
        """
        logger.info('Getting dashboard')
        for dashboard in self._get_collection('dashboard').find(filter=filter_archived(), skip=skip, limit=limit):
            if not dashboard.get('name'):
                logger.info(f'No name for dashboard {dashboard["_id"]}')
            elif not dashboard.get('config'):
                logger.info(f'No config found for dashboard {dashboard.get("name")}')
            else:
                # Let's fetch and execute them query filters, depending on the chart's type
                try:
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
                    yield gui_helpers.beautify_db_entry(dashboard)
                except Exception as e:
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
                data_item['value'] = self._entity_views_db_map[entity].count_documents(
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
        data_collection = self._entity_views_db_map[entity]

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
        data_collection = self._entity_views_db_map[entity]
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
        aggregate_results = data_collection.aggregate([
            {
                '$match': base_query
            },
            {
                '$group': {
                    '_id': {
                        '$arrayElemAt': [
                            {
                                '$filter': {
                                    'input': '$' + field['name'],
                                    'cond': {
                                        '$ne': ['$$this', '']
                                    }
                                }
                            }, 0
                        ]
                    },
                    'value': {
                        '$sum': 1
                    }
                }
            },
            {
                '$project': {
                    'value': 1,
                    'name': {
                        '$ifNull': [
                            '$_id', 'No Value'
                        ]
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
        for item in aggregate_results:
            field_value = item['name']
            if field_value == 'No Value':
                field_value = 'exists(false)'
            else:
                if (isinstance(field_value, str)):
                    field_value = f'\"{field_value}\"'
                if (isinstance(field_value, bool)):
                    field_value = str(field_value).lower()
            data.append({'name': str(item['name']), 'value': item['value'], 'module': entity.value,
                         'view': {**base_view, 'query': {'filter': f'{base_filter}{field["name"]} == {field_value}'}}})

        if chart_view == ChartViews.pie:
            total = data_collection.count_documents(base_query)
            return [{'name': view or 'ALL', 'value': 0}, *[{**x, 'value': x['value'] / total} for x in data]]
        return data

    def _fetch_chart_abstract(self, _: ChartViews, entity: EntityType, view, field, func, for_date=None):
        """

        :param _: Placeholder to create uniform interface for the chart fetching methods
        :return: One piece of data that is the calculation of given func on the values of given field, returning from
                 given view's query
        """
        # Query and data collections according to given module
        data_collection = self._entity_views_db_map[entity]
        base_view = {'query': {'filter': ''}}
        base_query = {
            field['name']: {
                '$exists': True
            }
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
        results = data_collection.find(base_query, projection={field['name']: 1})
        count = 0
        sigma = 0
        for item in results:
            field_values = gui_helpers.find_entity_field(item, field['name'])
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
        entity = EntityType(views[0]['entity'])
        base_query = {}
        if views[0].get('name'):
            base_query = parse_filter(self._find_filter_by_name(entity, views[0]['name'])['query']['filter'])
        yield {
            'title': views[0]['name'],
            'points': self._fetch_timeline_points(entity, base_query, date_ranges)
        }
        intersecting_view = self._find_filter_by_name(entity, views[1]['name'])
        intersecting_query = parse_filter(intersecting_view['query']['filter'])
        if base_query:
            intersecting_query = {
                '$and': [
                    base_query, intersecting_query
                ]
            }
        yield {
            'title': f'{views[0]["name"]} and {views[1]["name"]}',
            'points': self._fetch_timeline_points(entity, intersecting_query, date_ranges)
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
        update_result = self._get_collection('dashboard').update_one(
            {'_id': ObjectId(dashboard_id)}, {'$set': {'archived': True}})
        if not update_result.modified_count:
            return return_error(f'No dashboard by the id {dashboard_id} found or updated', 400)
        return ''

    @gui_add_rule_logged_in('dashboard/lifecycle', methods=['GET'],
                            required_permissions={Permission(PermissionType.Dashboard,
                                                             PermissionLevel.ReadOnly)})
    def get_system_lifecycle(self):
        """
        Fetches and build data needed for presenting current status of the system's lifecycle in a graph

        :return: Data containing:
         - All research phases names, for showing the whole picture
         - Current research sub-phase, which is empty if system is not stable
         - Portion of work remaining for the current sub-phase
         - The time next cycle is scheduled to run
        """
        state_response = self.request_remote_plugin('state', SYSTEM_SCHEDULER_PLUGIN_NAME)
        if state_response.status_code != 200:
            return return_error(f'Error fetching status of system scheduler. Reason: {state_response.text}')

        state_response = state_response.json()
        state = SchedulerState(**state_response['state'])
        is_stopping = state_response['stopping']
        is_research = state.Phase == Phases.Research.name

        if is_stopping:
            nice_state = ResearchStatus.stopping
        elif is_research:
            nice_state = ResearchStatus.running
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

        run_time_response = self.request_remote_plugin('next_run_time', SYSTEM_SCHEDULER_PLUGIN_NAME)
        if run_time_response.status_code != 200:
            return return_error(f'Error fetching run time of system scheduler. Reason: {run_time_response.text}')

        return jsonify({
            'sub_phases': sub_phases,
            'next_run_time': run_time_response.text,
            'status': nice_state.name
        })

    def _adapter_data(self, entity_type: EntityType):
        """
        For each adapter currently registered in system, count how many devices it fetched.

        :return: Map between each adapter and the number of devices it has, unless no devices
        """
        logger.info(f'Getting adapter data for entity {entity_type.name}')

        entity_collection = self._entity_views_db_map[entity_type]
        adapter_entities = {
            'seen': 0, 'seen_gross': 0, 'unique': entity_collection.count_documents({}), 'counters': []
        }

        # First value is net adapters count, second is gross adapters count (refers to AX-2430)
        # If an Axonius entity has 2 adapter entities from the same plugin it will be counted for each time it is there
        entities_per_adapters = defaultdict(lambda: {'value': 0, 'meta': 0})
        for res in entity_collection.aggregate([
                {
                    '$group': {
                        '_id': '$adapters',
                        'count': {
                            '$sum': 1
                        }
                    }
                }]):
            for plugin_name in set(res['_id']):
                entities_per_adapters[plugin_name]['value'] += res['count']
                adapter_entities['seen'] += res['count']

            for plugin_name in res['_id']:
                entities_per_adapters[plugin_name]['meta'] += res['count']
                adapter_entities['seen_gross'] += res['count']
        for name, value in entities_per_adapters.items():
            adapter_entities['counters'].append({'name': name, **value})

        return adapter_entities

    @gui_add_rule_logged_in('dashboard/adapter_data/<entity_name>', methods=['GET'],
                            required_permissions={Permission(PermissionType.Dashboard,
                                                             PermissionLevel.ReadOnly)})
    def get_adapter_data(self, entity_name):
        try:
            return jsonify(self._adapter_data(EntityType(entity_name)))
        except KeyError:
            error = f'No such entity {entity_name}'
        except Exception:
            error = f'Could not get adapter data for entity {entity_name}'
            logger.exception(error)
        return return_error(error, 400)

    def _get_dashboard_coverage(self):
        """
        Measures the coverage portion, according to sets of properties that devices' adapters may have.
        Portion is calculated out of total devices amount.
        Currently returns coverage for devices composed of adapters that are:
        - Managed ('Manager' or 'Agent')
        - Endpoint Protected
        - Vulnerability Assessed

        :return:
        """
        logger.info('Getting dashboard coverage')
        devices_total = self.devices_db_view.count_documents({})
        if not devices_total:
            return []
        coverage_list = [
            {'name': 'managed_coverage', 'title': 'Managed Device',
             'properties': [AdapterProperty.Manager.name, AdapterProperty.Agent.name],
             'description': 'Deploy appropriate agents on unmanaged devices, and add them to Active Directory.'},
            {'name': 'endpoint_coverage', 'title': 'Endpoint Protection',
             'properties': [AdapterProperty.Endpoint_Protection_Platform.name],
             'description': 'Add an endpoint protection solution to uncovered devices.'},
            {'name': 'vulnerability_coverage', 'title': 'VA Scanner',
             'properties': [AdapterProperty.Vulnerability_Assessment.name],
             'description': 'Add uncovered devices to the next scheduled vulnerability assessment scan.'}
        ]
        for item in coverage_list:
            devices_property = self.devices_db_view.count_documents({
                'specific_data.adapter_properties':
                    {'$in': item['properties']}
            })
            item['portion'] = devices_property / devices_total
        return coverage_list

    @gui_add_rule_logged_in('dashboard/coverage', methods=['GET'],
                            required_permissions={Permission(PermissionType.Dashboard,
                                                             PermissionLevel.ReadOnly)})
    def get_dashboard_coverage(self):
        return jsonify(self._get_dashboard_coverage())

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
        response = self.request_remote_plugin('trigger/execute?blocking=False', SYSTEM_SCHEDULER_PLUGIN_NAME, 'POST')

        if response.status_code != 200:
            logger.error('Error in running research phase')
            return return_error('Error in running research phase', response.status_code)

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
                f'Could not stop research phase. returned code: {response.status_code}, reason: {str(response.content)}')
            return return_error(f'Could not stop research phase {str(response.content)}', response.status_code)

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
        adapter_data = []
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
                        'count': self._entity_views_db_map[entity].count_documents(view_parsed)
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

            adapter_data.append({'name': adapter['title'], 'queries': views, 'views': adapter_clients_report})
        return adapter_data

    def _get_saved_views_data(self):
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
        for entity in EntityType:
            field_to_title = _get_field_titles(entity)
            # Fetch only saved views that were added by user, excluding out-of-the-box queries
            saved_views = self.gui_dbs.entity_query_views_db_map[entity].find(filter_archived({
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
            }))
            for i, view_doc in enumerate(saved_views):
                try:
                    view = view_doc.get('view')
                    if view:
                        filter_query = view.get('query', {}).get('filter', '')
                        log_metric(logger, 'query.report', filter_query)
                        field_list = view.get('fields', [])
                        views_data.append({
                            'name': view_doc.get('name', f'View {i}'), 'entity': entity.value,
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
                    logger.exception(f'Problem with View {str(i)} ViewDoc {str(view_doc)}')
        return views_data

    def _triggered(self, job_name: str, post_json: dict, *args):
        if job_name != 'execute':
            logger.error(f'Got bad trigger request for non-existent job: {job_name}')
            return return_error('Got bad trigger request for non-existent job', 400)
        self.dump_metrics()
        return self.generate_new_report_offline()

    def generate_new_report_offline(self):
        """
        Generates a new version of the report as a PDF file and saves it to the db
        (this method is NOT an endpoint)

        :return: "Success" if successful, error if there is an error
        """

        logger.info('Rendering Report.')
        # generate_report() renders the report html
        report_html = self.generate_report()
        # Writes the report pdf to a file-like object and use seek() to point to the beginning of the stream
        with io.BytesIO() as report_data:
            report_html.write_pdf(report_data)
            report_data.seek(0)
            # Uploads the report to the db and returns a uuid to retrieve it
            uuid = self._upload_report(report_data)
            logger.info(f'Report was saved to the db {uuid}')
            # Stores the uuid in the db in the "reports" collection
            self._get_collection('reports').replace_one(
                {'filename': 'most_recent_report'},
                {'uuid': uuid, 'filename': 'most_recent_report', 'time': datetime.now()}, True
            )
        return 'Success'

    def _upload_report(self, report):
        """
        Uploads the latest report PDF to the db
        :param report: report data
        :return:
        """
        if not report:
            return return_error('Report must exist', 401)

        # First, need to delete the old report
        self._delete_last_report()

        report_name = 'most_recent_report'
        with self._get_db_connection() as db_connection:
            fs = gridfs.GridFS(db_connection[GUI_NAME])
            written_file_id = fs.put(report, filename=report_name)
            logger.info('Report successfully placed in the db')
        return str(written_file_id)

    def _delete_last_report(self):
        """
        Deletes the last version of the report pdf to avoid having too many saved versions
        :return:
        """
        report_collection = self._get_collection('reports')
        if report_collection != None:
            most_recent_report = report_collection.find_one({'filename': 'most_recent_report'})
            if most_recent_report != None:
                uuid = most_recent_report.get('uuid')
                if uuid != None:
                    logger.info(f'DELETE: {uuid}')
                    with self._get_db_connection() as db_connection:
                        fs = gridfs.GridFS(db_connection[GUI_NAME])
                        fs.delete(ObjectId(uuid))

    @gui_add_rule_logged_in('export_report', required_permissions={Permission(PermissionType.Dashboard,
                                                                              PermissionLevel.ReadOnly)})
    def export_report(self):
        """
        Gets definition of report from DB for the dynamic content.
        Gets all the needed data for both pre-defined and dynamic content definitions.
        Sends the complete data to the report generator to be composed to one document and generated as a pdf file.

        If background report generation setting is turned off, the report will be generated here, as well.

        TBD Should receive ID of the report to export (once there will be an option to save many report definitions)
        :return:
        """
        report_path = self._get_existing_executive_report()
        return send_file(report_path, mimetype='application/pdf', as_attachment=True,
                         attachment_filename=report_path)

    def _get_existing_executive_report(self):
        report = self._get_collection('reports').find_one({'filename': 'most_recent_report'})
        if not report:
            self.generate_new_report_offline()

        uuid = report['uuid']
        report_path = f'/tmp/axonius-report_{datetime.now()}.pdf'
        with self._get_db_connection() as db_connection:
            with gridfs.GridFS(db_connection[GUI_NAME]).get(ObjectId(uuid)) as report_content:
                open(report_path, 'wb').write(report_content.read())
                return report_path

    def generate_report(self):
        """
        Generates the report and returns html.
        :return: the generated report file path.
        """
        logger.info('Starting to generate report')
        report_data = {
            'adapter_devices': self._adapter_data(EntityType.Devices),
            'adapter_users': self._adapter_data(EntityType.Users),
            'covered_devices': self._get_dashboard_coverage(),
            'custom_charts': list(self._get_dashboard()),
            'views_data': self._get_saved_views_data()
        }
        report = self._get_collection('reports_config').find_one({'name': 'Main Report'})
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
            recipients = self.get_request_data_as_object()
            self._send_report_thread(recipients=recipients)
            return ''
        except Exception as e:
            logger.exception('Failed sending test report by email.')
            return return_error(f'Problem testing report by email:\n{str(e.args[0]) if e.args else e}', 400)

    def _get_exec_report_settings(self, exec_reports_settings_collection):
        settings_object = exec_reports_settings_collection.find_one({}, projection={'_id': False, 'period': True,
                                                                                    'recipients': True})
        return settings_object or {}

    def _schedule_exec_report(self, exec_reports_settings_collection, exec_report_data):
        logger.info('rescheduling exec_report')
        time_period = exec_report_data['period']
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

        exec_report_job = self._job_scheduler.get_job(EXEC_REPORT_THREAD_ID)

        # If job doesn't exist generate it
        if exec_report_job is None:
            self._job_scheduler.add_job(func=self._send_report_thread,
                                        trigger=new_interval_triggger,
                                        next_run_time=next_run_time,
                                        name=EXEC_REPORT_THREAD_ID,
                                        id=EXEC_REPORT_THREAD_ID,
                                        max_instances=1)
        else:
            exec_report_job.modify(next_run_time=next_run_time)
            self._job_scheduler.reschedule_job(EXEC_REPORT_THREAD_ID, trigger=new_interval_triggger)

        exec_reports_settings_collection.replace_one({}, exec_report_data, upsert=True)
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
            return self._schedule_exec_report(self.exec_report_collection, exec_report_data)

    def _send_report_thread(self, recipients=None):
        with self.exec_report_lock:
            if not recipients:
                exec_report = self.exec_report_collection.find_one()
                if exec_report:
                    recipients = exec_report.get('recipients', [])
            report_path = self._get_existing_executive_report()
            if self.mail_sender:
                email = self.mail_sender.new_email(EXEC_REPORT_TITLE, recipients)
                with open(report_path, 'rb') as report_file:
                    email.add_pdf(EXEC_REPORT_FILE_NAME, bytes(report_file.read()))
                email.send(EXEC_REPORT_EMAIL_CONTENT)
            else:
                logger.info('Email cannot be sent because no email server is configured')
                raise RuntimeWarning('No email server configured')

    def _stop_temp_maintenance(self):
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
            adapter_devices = self._adapter_data(EntityType.Devices)
            adapter_users = self._adapter_data(EntityType.Users)

            log_metric(logger, 'system.gui.users', self.__users_collection.count_documents({}))
            log_metric(logger, 'system.devices.seen', adapter_devices['seen'])
            log_metric(logger, 'system.devices.unique', adapter_devices['unique'])

            log_metric(logger, 'system.users.seen', adapter_users['seen'])
            log_metric(logger, 'system.users.unique', adapter_users['unique'])

            def dump_per_adapter(mapping, subtype):
                counters = mapping['counters']
                for counter in counters:
                    log_metric(logger, f'adapter.{subtype}.{counter["name"]}.entities', counter['value'])
                    log_metric(logger, f'adapter.{subtype}.{counter["name"]}.entities.meta', counter['meta'])

            dump_per_adapter(adapter_devices, 'devices')
            dump_per_adapter(adapter_users, 'users')
        except Exception:
            logger.exception('Failed to dump metrics')

    @gui_add_rule_logged_in('metadata', methods=['GET'], required_permissions={Permission(PermissionType.Settings,
                                                                                          PermissionLevel.ReadOnly)})
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
        :param history_date: Date that the data should be fetched for
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

        current_user = session.get('user')
        if not current_user:
            logger.error('Login in order to update notes')
            return return_error('Login in order to update notes', 400)
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
            if not session.get('user').get('admin') and session.get('user').get('role_name') != PREDEFINED_ROLE_ADMIN:
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

        current_user = session.get('user')
        if not current_user:
            logger.error('Login in order to update notes')
            return return_error('Login in order to update notes', 400)
        if current_user['_id'] != note_doc['user_id'] and not session.get('user').get('admin') and \
                session.get('user').get('role_name') != PREDEFINED_ROLE_ADMIN:
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
        if request.method == 'GET':
            with self._get_db_connection() as db_connection:
                nodes = []
                for current_node in db_connection['core']['configs'].distinct('node_id'):
                    node_data = db_connection['core']['nodes_metadata'].find_one({'node_id': current_node})
                    if node_data is not None:
                        nodes.append({'node_id': current_node, 'node_name': node_data.get('node_name', {}), 'tags': node_data.get('tags', {}),
                                      'last_seen': self.request_remote_plugin(f'nodes/last_seen/{current_node}').json()[
                                          'last_seen'], NODE_USER_PASSWORD: node_data.get(NODE_USER_PASSWORD, '')})
                    else:
                        nodes.append({'node_id': current_node, 'node_name': current_node, 'tags': {},
                                      'last_seen': self.request_remote_plugin(f'nodes/last_seen/{current_node}').json()[
                                          'last_seen'], NODE_USER_PASSWORD: ''})
                system_config = db_connection['gui']['system_collection'].find_one({'type': 'server'}) or {}
                return jsonify({'instances': nodes, 'connection_data': {'key': self.encryption_key, 'host': system_config.get('server_name', '<axonius-hostname>')}})
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
                    for current_client in self._get_collection('clients', adapter[PLUGIN_UNIQUE_NAME]).find({}, projection={'_id': 1}):
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

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.PostCorrelation

    @property
    def system_collection(self):
        return self._get_collection(GUI_SYSTEM_CONFIG_COLLECTION)

    @property
    def reports_collection(self):
        return self._get_collection('reports', db_name=self.get_plugin_by_name('reports')[PLUGIN_UNIQUE_NAME])

    @property
    def exec_report_collection(self):
        return self._get_collection('exec_reports_settings')

    @property
    def device_control_plugin(self):
        return self.get_plugin_by_name(DEVICE_CONTROL_PLUGIN_NAME)[PLUGIN_UNIQUE_NAME]

    def get_plugin_unique_name(self, plugin_name):
        return self.get_plugin_by_name(plugin_name)[PLUGIN_UNIQUE_NAME]

    def _on_config_update(self, config):
        logger.info(f'Loading GuiService config: {config}')
        self.__okta = config['okta_login_settings']
        self.__google = config['google_login_settings']
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

    @gui_helpers.add_rule_unauth('provision')
    def get_provision(self):
        return jsonify(
            self._maintenance_config.get('provision', False) or self._maintenance_config.get('timeout') != None)

    @gui_helpers.add_rule_unauth('analytics')
    def get_analytics(self):
        return jsonify(
            self._maintenance_config.get('analytics', False) or self._maintenance_config.get('timeout') != None)

    @gui_helpers.add_rule_unauth('troubleshooting')
    def get_troubleshooting(self):
        return jsonify(
            self._maintenance_config.get('troubleshooting', False) or self._maintenance_config.get('timeout') != None)

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
                            'title': 'Allow Google logins',
                            'type': 'bool'
                        },
                        {
                            'name': 'client',
                            'title': 'Google client id',
                            'type': 'string'
                        },
                        {
                            'name': 'account_to_impersonate',
                            'title': 'Email of an admin account to impersonate',
                            'type': 'string'
                        },
                        {
                            'name': GOOGLE_KEYPAIR_FILE,
                            'title': 'JSON Key pair for the service account',
                            'description': 'The binary contents of the keypair file',
                            'type': 'file',
                        },
                        {
                            'name': 'allowed_domain',
                            'title': 'Allowed G Suite domain (Leave empty for all domains)',
                            'type': 'string'
                        },
                        {
                            'name': 'allowed_group',
                            'title': 'Only users in this group will be allowed (Leave empty for all groups)',
                            'type': 'string'
                        }
                    ],
                    'required': ['enabled', 'client', 'account_to_impersonate', GOOGLE_KEYPAIR_FILE],
                    'name': 'google_login_settings',
                    'title': 'Google Login Settings',
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
            'google_login_settings': {
                'enabled': False,
                'client': None,
                'allowed_domain': None,
                'allowed_group': None,
                'account_to_impersonate': None,
                GOOGLE_KEYPAIR_FILE: None
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
                'refreshRate': 30,
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
