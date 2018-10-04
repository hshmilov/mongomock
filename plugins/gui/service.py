import configparser
import io
import json
import logging
import os
import re
import secrets
import tarfile
import threading
import time
from datetime import date, datetime, timedelta
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool
from typing import Iterable, Tuple

import gridfs
import ldap3
import pymongo
import requests
from apscheduler.executors.pool import \
    ThreadPoolExecutor as ThreadPoolExecutorApscheduler
from apscheduler.triggers.cron import CronTrigger
from axonius.adapter_base import AdapterProperty
from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.clients.ldap.exceptions import LdapException
from axonius.clients.ldap.ldap_connection import LdapConnection
from axonius.consts.plugin_consts import (AGGREGATOR_PLUGIN_NAME,
                                          ANALYTICS_SETTING,
                                          CONFIGURABLE_CONFIGS,
                                          CORE_UNIQUE_NAME,
                                          DEVICE_CONTROL_PLUGIN_NAME, GUI_NAME,
                                          GUI_SYSTEM_CONFIG_COLLECTION,
                                          MAINTENANCE_SETTINGS, METADATA_PATH,
                                          PLUGIN_NAME, PLUGIN_UNIQUE_NAME,
                                          SYSTEM_SCHEDULER_PLUGIN_NAME,
                                          SYSTEM_SETTINGS,
                                          TROUBLESHOOTING_SETTING)
from axonius.consts.scheduler_consts import Phases, ResearchPhases, StateLevels
from axonius.email_server import EmailServer
from axonius.mixins.configurable import Configurable
from axonius.mixins.triggerable import Triggerable
from axonius.plugin_base import EntityType, PluginBase, return_error
from axonius.thread_pool_executor import LoggedThreadPoolExecutor
from axonius.thread_stopper import stoppable
from axonius.types.ssl_state import SSLState
from axonius.utils import gui_helpers
from axonius.utils.datetime import next_weekday, time_from_now
from axonius.utils.files import create_temp_file, get_local_config_file
from axonius.utils.gui_helpers import beautify_user_entry, PermissionType, Permission, \
    PermissionLevel, deserialize_db_permissions, check_permissions, ReadOnlyJustForGet
from axonius.utils.parsing import bytes_image_to_base64, parse_filter
from bson import ObjectId
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta
from elasticsearch import Elasticsearch
from flask import (after_this_request, jsonify, make_response, redirect,
                   request, send_file, session)
from passlib.hash import bcrypt
from urllib3.util.url import parse_url

from gui.api import API
from gui.cached_session import CachedSessionInterface
from gui.consts import (EXEC_REPORT_EMAIL_CONTENT, EXEC_REPORT_FILE_NAME,
                        EXEC_REPORT_THREAD_ID, EXEC_REPORT_TITLE,
                        SUPPORT_ACCESS_THREAD_ID, ChartFuncs, ChartMetrics,
                        ChartViews, ResearchStatus)
from gui.okta_login import try_connecting_using_okta
from gui.report_generator import ReportGenerator

logger = logging.getLogger(f'axonius.{__name__}')


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
            return return_error("You are lacking some permissions for this request", 401)

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
                tarinfo = tarfile.TarInfo(f"{filename}.{extension}")
                tarinfo.size = len(response.data)
                tar.addfile(tarinfo, fileobj=uncompressed)
                tar.close()

                response.data = compressed.getbuffer()
                if "Content-Disposition" not in response.headers:
                    response.headers["Content-Disposition"] = f"attachment;filename={filename}.tar.gz"
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
        raise RuntimeError("We shouldn't have lists in schemas")

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
    DEFAULT_AVATAR_PIC = '/src/assets/images/users/avatar.png'

    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__),
                         requested_unique_plugin_name=GUI_NAME, *args, **kwargs)
        self.__all_sessions = {}
        self.wsgi_app.session_interface = CachedSessionInterface(self.__all_sessions)

        # this command sets mongo's query space to be larger default
        # which allows for faster queries using the RAM alone
        self._get_db_connection()['admin'].command({
            'setParameter': 1,
            'internalQueryExecMaxBlockingSortBytes': 2 * 1024 * 1024 * 1024 - 1  # max size mongo allows
        })
        self.wsgi_app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

        self._elk_addr = self.config['gui_specific']['elk_addr']
        self._elk_auth = self.config['gui_specific']['elk_auth']
        self.__users_collection = self._get_collection('users')
        current_user = self.__users_collection.find_one({'user_name': 'admin'})
        if current_user is None:
            # User doesn't exist, this must be the installation process
            self.__users_collection.update({'user_name': 'admin'},
                                           {'user_name': 'admin',
                                            'password':
                                                '$2b$12$SjT4qshlg.uUpsgE3vHwp.7A0UtkGEoWfUR0wFet3WZuXTnMgOCIK',
                                            'first_name': 'administrator', 'last_name': '',
                                            'pic_name': self.DEFAULT_AVATAR_PIC,
                                            'permissions': {},
                                            'admin': True,
                                            'source': 'internal',
                                            'api_key': secrets.token_urlsafe(),
                                            'api_secret': secrets.token_urlsafe()
                                            }, upsert=True)

        self.add_default_views(EntityType.Devices, 'default_views_devices.ini')
        self.add_default_views(EntityType.Users, 'default_views_users.ini')
        self._mark_demo_views()
        self.add_default_reports('default_reports.ini')
        self.add_default_dashboard_charts('default_dashboard_charts.ini')
        if not self.system_collection.find({'type': 'server'}):
            self.system_collection.insert_one({'type': 'server', 'server_name': 'localhost'})

        # Start exec report scheduler
        self.exec_report_lock = threading.RLock()

        self._client_insertion_threadpool = LoggedThreadPoolExecutor(max_workers=20)  # Only for client insertion

        self._job_scheduler = LoggedBackgroundScheduler(executors={'default': ThreadPoolExecutorApscheduler(1)})
        current_exec_report_setting = self._get_exec_report_settings(self.exec_report_collection)
        if current_exec_report_setting != {}:
            self._schedule_exec_report(self.exec_report_collection, current_exec_report_setting)
        self._job_scheduler.start()

        self.metadata = self.load_metadata()
        self._activate('execute')
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
            if os.path.exists(METADATA_PATH):
                with open(METADATA_PATH, 'r') as metadata_file:
                    metadata_bytes = metadata_file.read()[:-1].replace('\\', '\\\\')
                    return json.loads(metadata_bytes)
        except Exception:
            logger.exception(f"Bad __build_metadata file {metadata_bytes}")
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
        reports_collection = self._get_collection("reports_config")
        existed_report = reports_collection.find_one({'name': name})
        if existed_report is not None and not existed_report.get('archived'):
            logger.info(f'Report {name} already exists under id: {existed_report["_id"]}')
            return

        result = reports_collection.replace_one({'name': name},
                                                {'name': name, 'adapters': json.loads(report['adapters'])}, upsert=True)
        logger.info(f'Added report {name} id: {result.upserted_id}')

    def _insert_dashboard_chart(self, dashboard_name, dashboard_metric, dashboard_view, dashboard_data):
        dashboard_collection = self._get_collection("dashboard")
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
        plugins_available = requests.get(self.core_address + '/register').json()
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

    ########
    # DATA #
    ########

    def _entity_by_id(self, entity_type: EntityType, entity_id, advanced_fields=[]):
        """
        Retrieve or delete device by the given id, from current devices DB or update it
        Currently, update works only for tags because that is the only edit operation user has
        :return:
        """

        def _basic_generic_field_names():
            with self._get_db_connection() as db_connection:
                generic_field_names = list(map(lambda field: field.get(
                    'name'), gui_helpers.entity_fields(entity_type, self.core_address, db_connection)['generic']))
            return filter(
                lambda field: field != 'adapters' and field != 'labels' and
                len([category for category in advanced_fields if category in field]) == 0,
                generic_field_names)

        entity = self._entity_views_db_map[entity_type].find_one({'internal_axon_id': entity_id})
        if entity is None:
            return return_error("Entity ID wasn't found", 404)
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
            'internal_axon_id': entity['internal_axon_id']
        })

    def _disable_entity(self, entity_type: EntityType):
        entity_map = {
            EntityType.Devices: ("Devicedisabelable", "devices/disable"),
            EntityType.Users: ("Userdisabelable", "users/disable")
        }
        if entity_type not in entity_map:
            raise Exception("Weird entity type given")

        featurename, urlpath = entity_map[entity_type]

        entitys_uuids = self.get_request_data_as_object()
        if not entitys_uuids:
            return return_error("No entity uuids provided")
        entity_disabelables_adapters, entity_ids_by_adapters = \
            self._find_entities_by_uuid_for_adapter_with_feature(entitys_uuids, featurename, entity_type)

        err = ""
        for adapter_unique_name in entity_disabelables_adapters:
            entitys_by_adapter = entity_ids_by_adapters.get(adapter_unique_name)
            if entitys_by_adapter:
                response = self.request_remote_plugin(urlpath, adapter_unique_name, method='POST',
                                                      json=entitys_by_adapter)
                if response.status_code != 200:
                    logger.error(f"Error on disabling on {adapter_unique_name}: {response.content}")
                    err += f"Error on disabling on {adapter_unique_name}: {response.content}\n"

        return return_error(err, 500) if err else ("", 200)

    def _find_entities_by_uuid_for_adapter_with_feature(self, entity_uuids, feature, entity_type: EntityType):
        """
        Find all entity from adapters that have a given feature, from a given set of entities
        :return: plugin_unique_names of entity with given features, dict of plugin_unique_name -> id of adapter entity
        """
        with self._get_db_connection() as db_connection:
            entities = list(self._entity_db_map.get(entity_type).find(
                {'internal_axon_id': {
                    "$in": entity_uuids
                }}))

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
                                                               "$in": list(entities_ids_by_adapters.keys())
                                                           }
                                                       },
                                                       projection={
                                                           PLUGIN_UNIQUE_NAME: 1
                                                       }
                    )]
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
                    adapter_matches = re.findall('adapters_data\.(\w*)\.', expression.get('field', ''))
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
            return ''

        if method == 'DELETE':
            query_ids = self.get_request_data_as_object()
            entity_views_collection.update_many({'_id': {'$in': [ObjectId(i) for i in query_ids]}},
                                                {'$set': {'archived': True}})
            return ""

    def _entity_labels(self, db, namespace):
        """
        GET Find all tags that currently belong to devices, to form a set of current tag values
        POST Add new tags to the list of given devices
        DELETE Remove old tags from the list of given devices
        :return:
        """
        all_labels = set()
        with self._get_db_connection() as db_connection:
            if request.method == 'GET':
                for current_device in db.find({'$or': [{'labels': {'$exists': False}}, {'labels': {'$ne': []}}]},
                                              projection={'labels': 1}):
                    all_labels.update(current_device['labels'])
                return jsonify(all_labels)

            # Now handling POST and DELETE - they determine if the label is an added or removed one
            entities_and_labels = self.get_request_data_as_object()
            if not entities_and_labels.get('entities'):
                return return_error("Cannot label entities without list of entities.", 400)
            if not entities_and_labels.get('labels'):
                return return_error("Cannot label entities without list of labels.", 400)

            entities = [db.find_one({'internal_axon_id': entity_id})['specific_data'][0]
                        for entity_id in entities_and_labels['entities']]
            entities = [(entity[PLUGIN_UNIQUE_NAME], entity['data']['id']) for entity in entities]

            response = namespace.add_many_labels(entities, labels=entities_and_labels['labels'],
                                                 are_enabled=request.method == 'POST')

            if response.status_code != 200:
                logger.error(f"Tagging did not complete. First {response.json()}")
                return_error(f'Tagging did not complete. First error: {response.json()}', 400)

            return '', 200

    def __delete_entities_by_internal_axon_id(self, entity_type: EntityType, internal_axon_ids: Iterable[str]):
        internal_axon_ids = list(internal_axon_ids)
        self._entity_db_map[entity_type].update_many({'internal_axon_id': {
            "$in": internal_axon_ids
        }},
            {
                "$set": {
                    "adapters.$[].pending_delete": True
                }
        })
        self._request_db_rebuild(sync=True, internal_axon_ids=internal_axon_ids)

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

    ##########
    # DEVICE #
    ##########

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_add_rule_logged_in("devices", methods=['GET', 'DELETE'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             ReadOnlyJustForGet)})
    def get_devices(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        if request.method == 'DELETE':
            to_delete = self.get_request_data_as_object().get('internal_axon_ids', [])
            return self.__delete_entities_by_internal_axon_id(EntityType.Devices, to_delete)
        self._save_query_to_history(EntityType.Devices, mongo_filter, skip, limit, mongo_sort, mongo_projection)
        return jsonify(
            gui_helpers.get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection,
                                     EntityType.Devices,
                                     default_sort=self._system_settings['defaultSort']))

    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_add_rule_logged_in("devices/csv", required_permissions={Permission(PermissionType.Devices,
                                                                            PermissionLevel.ReadOnly)})
    def get_devices_csv(self, mongo_filter, mongo_sort, mongo_projection):
        with self._get_db_connection() as db_connection:
            csv_string = gui_helpers.get_csv(mongo_filter, mongo_sort, mongo_projection,
                                             db_connection, EntityType.Devices,
                                             default_sort=self._system_settings['defaultSort'])
            output = make_response(csv_string.getvalue().encode('utf-8'))
            timestamp = datetime.now().strftime('%d%m%Y-%H%M%S')
            output.headers['Content-Disposition'] = f'attachment; filename=axonius-data_{timestamp}.csv'
            output.headers['Content-type'] = 'text/csv'
            return output

    @gui_add_rule_logged_in("devices/<device_id>", methods=['GET'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadOnly)})
    def device_by_id(self, device_id):
        return self._entity_by_id(EntityType.Devices, device_id, ['installed_software', 'software_cves',
                                                                  'security_patches', 'available_security_patches',
                                                                  'users', 'connected_hardware', 'local_admins'])

    @gui_helpers.filtered()
    @gui_add_rule_logged_in("devices/count", required_permissions={Permission(PermissionType.Devices,
                                                                              PermissionLevel.ReadOnly)})
    def get_devices_count(self, mongo_filter):
        return gui_helpers.get_entities_count(mongo_filter, self._entity_views_db_map[EntityType.Devices])

    @gui_add_rule_logged_in("devices/fields", required_permissions={Permission(PermissionType.Devices,
                                                                               PermissionLevel.ReadOnly)})
    def device_fields(self):
        with self._get_db_connection() as db_connection:
            return jsonify(gui_helpers.entity_fields(EntityType.Devices, self.core_address, db_connection))

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_add_rule_logged_in("devices/views", methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             ReadOnlyJustForGet)})
    def device_views(self, limit, skip, mongo_filter):
        """
        Save or fetch views over the devices db
        :return:
        """
        return jsonify(self._entity_views(request.method, EntityType.Devices, limit, skip, mongo_filter))

    @gui_add_rule_logged_in("devices/labels", methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             ReadOnlyJustForGet)})
    def device_labels(self):
        return self._entity_labels(self.devices_db_view, self.devices)

    @gui_add_rule_logged_in("devices/disable", methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadWrite)})
    def disable_device(self):
        return self._disable_entity(EntityType.Devices)

    #########
    # USER #
    #########

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_add_rule_logged_in("users", methods=['GET', 'DELETE'], required_permissions={Permission(PermissionType.Users,
                                                                                                 ReadOnlyJustForGet)})
    def get_users(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        if request.method == 'DELETE':
            to_delete = self.get_request_data_as_object().get('internal_axon_ids', [])
            return self.__delete_entities_by_internal_axon_id(EntityType.Users, to_delete)
        self._save_query_to_history(EntityType.Users, mongo_filter, skip, limit, mongo_sort, mongo_projection)
        return jsonify(
            gui_helpers.get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection,
                                     EntityType.Users,
                                     default_sort=self._system_settings['defaultSort']))

    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_add_rule_logged_in("users/csv", required_permissions={Permission(PermissionType.Users,
                                                                          PermissionLevel.ReadOnly)})
    def get_users_csv(self, mongo_filter, mongo_sort, mongo_projection):
        with self._get_db_connection() as db_connection:
            # Deleting image from the CSV (we dont need this base64 blob in the csv)
            if "specific_data.data.image" in mongo_projection:
                del mongo_projection["specific_data.data.image"]
            csv_string = gui_helpers.get_csv(mongo_filter, mongo_sort, mongo_projection,
                                             db_connection, EntityType.Users,
                                             default_sort=self._system_settings['defaultSort'])
            output = make_response(csv_string.getvalue().encode('utf-8'))
            timestamp = datetime.now().strftime('%d%m%Y-%H%M%S')
            output.headers['Content-Disposition'] = f'attachment; filename=axonius-data_{timestamp}.csv'
            output.headers['Content-type'] = 'text/csv'
            return output

    @gui_add_rule_logged_in("users/<user_id>", methods=['GET'], required_permissions={Permission(PermissionType.Users,
                                                                                                 PermissionLevel.ReadOnly)})
    def user_by_id(self, user_id):
        return self._entity_by_id(EntityType.Users, user_id, ['associated_devices'])

    @gui_helpers.filtered()
    @gui_add_rule_logged_in("users/count", required_permissions={Permission(PermissionType.Users,
                                                                            PermissionLevel.ReadOnly)})
    def get_users_count(self, mongo_filter):
        return gui_helpers.get_entities_count(mongo_filter, self._entity_views_db_map[EntityType.Users])

    @gui_add_rule_logged_in("users/fields", required_permissions={Permission(PermissionType.Users,
                                                                             PermissionLevel.ReadOnly)})
    def user_fields(self):
        with self._get_db_connection() as db_connection:
            return jsonify(gui_helpers.entity_fields(EntityType.Users, self.core_address, db_connection))

    @gui_add_rule_logged_in("users/disable", methods=['POST'], required_permissions={Permission(PermissionType.Users,
                                                                                                PermissionLevel.ReadWrite)})
    def disable_user(self):
        return self._disable_entity(EntityType.Users)

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_add_rule_logged_in("users/views", methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Users,
                                                             ReadOnlyJustForGet)})
    def user_views(self, limit, skip, mongo_filter):
        return jsonify(self._entity_views(request.method, EntityType.Users, limit, skip, mongo_filter))

    @gui_add_rule_logged_in("users/labels", methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Users,
                                                             ReadOnlyJustForGet)})
    def user_labels(self):
        return self._entity_labels(self.users_db_view, self.users)

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

    @gui_add_rule_logged_in("adapters", required_permissions={Permission(PermissionType.Adapters,
                                                                         PermissionLevel.ReadOnly)})
    def adapters(self):
        """
        Get all adapters from the core
        :return:
        """
        plugins_available = requests.get(self.core_address + '/register').json()
        with self._get_db_connection() as db_connection:
            adapters_from_db = db_connection['core']['configs'].find({
                'plugin_type': {'$in': ['Adapter', 'ScannerAdapter']}}).sort([(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
            adapters_to_return = []
            for adapter in adapters_from_db:
                adapter_name = adapter[PLUGIN_UNIQUE_NAME]
                if adapter_name not in plugins_available:
                    # Plugin not registered - unwanted in UI
                    continue

                clients_collection = db_connection[adapter_name]['clients']
                schema = self._get_plugin_schemas(db_connection, adapter_name).get('clients')
                if not schema:
                    # there might be a race - in the split second that the adapter is up
                    # but it still hasn't written it's schema
                    continue

                clients = [gui_helpers.beautify_db_entry(client) for client in clients_collection.find()
                           .sort([('_id', pymongo.DESCENDING)])]
                for client in clients:
                    client['client_config'] = clear_passwords_fields(client['client_config'], schema)
                status = ''
                if len(clients):
                    clients_connected = clients_collection.count_documents({'status': 'success'})
                    status = 'success' if len(clients) == clients_connected else 'warning'

                adapters_to_return.append({'plugin_name': adapter['plugin_name'],
                                           'unique_plugin_name': adapter_name,
                                           'status': status,
                                           'supported_features': adapter['supported_features'],
                                           'schema': schema,
                                           'clients': clients,
                                           'config': self.__extract_configs_and_schemas(db_connection,
                                                                                        adapter_name)
                                           })

            return jsonify(adapters_to_return)

    @gui_add_rule_logged_in("adapter_features")
    def adapter_features(self):
        """
        Getting the features of each registered adapter, as they are saved in core's "configs" db.
        This is needed for the case that user has permissions to disable entities but is restricted from adapters.
        The user would need to know which entities can be disabled, according to the features of their adapters.

        :return: Dict between unique plugin name of the adapter and their list of features
        """
        plugins_available = requests.get(self.core_address + '/register').json()
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
            return return_error("Invalid client", 400)
        if data_from_db_for_unchanged:
            client_to_test = refill_passwords_fields(client_to_test, data_from_db_for_unchanged['client_config'])
        # adding client to specific adapter
        response = self.request_remote_plugin("client_test", adapter_unique_name, method='post', json=client_to_test)
        return response.text, response.status_code

    def _query_client_for_devices(self, adapter_unique_name, data_from_db_for_unchanged=None):
        client_to_add = request.get_json(silent=True)
        if client_to_add is None:
            return return_error("Invalid client", 400)
        if data_from_db_for_unchanged:
            client_to_add = refill_passwords_fields(client_to_add, data_from_db_for_unchanged['client_config'])
        # adding client to specific adapter
        response = self.request_remote_plugin("clients", adapter_unique_name, method='put', json=client_to_add)
        if response.status_code == 200:
            self._client_insertion_threadpool.submit(self._fetch_after_clients_thread, adapter_unique_name,
                                                     response.json()['client_id'], client_to_add)
        return response.text, response.status_code

    def _fetch_after_clients_thread(self, adapter_unique_name, client_id, client_to_add):
        # if there's no aggregator, that's fine
        try:
            logger.info(f"Stopping research phase after adding client {client_id}")
            response = self.request_remote_plugin('stop_all', SYSTEM_SCHEDULER_PLUGIN_NAME, 'POST')
            response.raise_for_status()
            logger.info(f"Requesting {adapter_unique_name} to fetch data from newly added client {client_id}")
            response = self.request_remote_plugin(f"insert_to_db?client_name={client_id}",
                                                  adapter_unique_name, method='PUT')
            logger.info(f"{adapter_unique_name} finished fetching data for {client_id}")
            if not (response.status_code == 400 and response.json()['message'] == 'Gracefully stopped'):
                response.raise_for_status()
                response = self.request_remote_plugin('trigger/execute', SYSTEM_SCHEDULER_PLUGIN_NAME, 'POST')
                response.raise_for_status()
        except Exception:
            # if there's no aggregator, there's nothing we can do
            logger.exception(f"Error fetching devices from {adapter_unique_name} for client {client_to_add}")
            pass
        return

    @gui_add_rule_logged_in("adapters/<adapter_unique_name>/upload_file", methods=['POST'],
                            required_permissions={Permission(PermissionType.Adapters,
                                                             PermissionLevel.ReadWrite)})
    def adapter_upload_file(self, adapter_unique_name):
        return self._upload_file(adapter_unique_name)

    def _upload_file(self, plugin_unique_name):
        import gridfs
        field_name = request.form.get('field_name')
        if not field_name:
            return return_error("Field name must be specified", 401)
        file = request.files.get("userfile")
        if not file or file.filename == '':
            return return_error("File must exist", 401)
        filename = file.filename
        with self._get_db_connection() as db_connection:
            fs = gridfs.GridFS(db_connection[plugin_unique_name])
            written_file = fs.put(file, filename=filename)
        return jsonify({'uuid': str(written_file)})

    @gui_add_rule_logged_in("adapters/<adapter_unique_name>/clients", methods=['PUT', 'POST'],
                            required_permissions={Permission(PermissionType.Adapters,
                                                             PermissionLevel.ReadWrite)})
    def adapters_clients(self, adapter_unique_name):
        """
        Gets or creates clients in the adapter
        :param adapter_unique_name: the adapter to refer to
        :return:
        """
        with self._get_db_connection() as db_connection:
            if request.method == 'PUT':
                self.__is_system_first_use = False
                return self._query_client_for_devices(adapter_unique_name)
            else:
                return self._test_client_connectivity(adapter_unique_name)

    @gui_add_rule_logged_in("adapters/<adapter_unique_name>/clients/<client_id>",
                            methods=['PUT', 'DELETE'], required_permissions={Permission(PermissionType.Adapters,
                                                                                        PermissionLevel.ReadWrite)})
    def adapters_clients_update(self, adapter_unique_name, client_id=None):
        """
        Create or delete credential sets (clients) in the adapter
        :param adapter_unique_name: the adapter to refer to
        :param client_id: UUID of client to delete if DELETE is used
        :return:
        """
        if request.method == 'DELETE':
            plugin_name = self.get_plugin_by_name(adapter_unique_name)[PLUGIN_NAME]
            delete_entities = request.args.get('deleteEntities', False)
            if delete_entities:
                client_from_db = self._get_collection('clients', adapter_unique_name). \
                    find_one({'_id': ObjectId(client_id)})
                if client_from_db:
                    # this is the "client_id" - i.e. AD server or AWS Access Key
                    local_client_id = client_from_db['client_id']
                    for entity_type in EntityType:
                        res = self._entity_db_map[entity_type].update_many(
                            {
                                'adapters': {
                                    '$elemMatch': {
                                        "$and": [
                                            {
                                                PLUGIN_NAME: plugin_name
                                            },
                                            {
                                                # and the device must be from this adapter
                                                "client_used": local_client_id
                                            }
                                        ]
                                    }
                                }
                            },
                            {
                                "$set": {
                                    "adapters.$[i].pending_delete": True
                                }
                            },
                            array_filters=[
                                {
                                    "$and": [
                                        {f"i.{PLUGIN_NAME}": plugin_name},
                                        {"i.client_used": local_client_id}
                                    ]
                                }
                            ]
                        )
                        logger.info(f"Set pending_delete on {res.modified_count} axonius entities "
                                    f"(or some adapters in them)" +
                                    f"from {res.matched_count} matches")
                    self._request_db_rebuild(sync=True)

        if request.method == 'PUT':
            client_from_db = self._get_collection('clients', adapter_unique_name).find_one({'_id': ObjectId(client_id)})
        self.request_remote_plugin("clients/" + client_id, adapter_unique_name, method='delete')
        if request.method == 'PUT':
            return self._query_client_for_devices(adapter_unique_name,
                                                  data_from_db_for_unchanged=client_from_db)

        return '', 200

    def run_actions(self, action_data):
        # The format of data is defined in device_control\service.py::run_shell
        action_type = action_data['action_type']
        try:
            response = self.request_remote_plugin('run_action', self.device_control_plugin, 'post', json=action_data)
            if response.status_code != 200:
                message = f'Running action {action_type} failed because {str(json.loads(response.content)["message"])}'
                logger.error(message)
                return return_error(message, 400)
            return '', 200
        except Exception as e:
            return return_error(f'Attempt to run action {action_type} caused exception. Reason: {repr(e)}', 400)

    @gui_add_rule_logged_in("actions/<action_type>", methods=['POST'],
                            required_permissions={Permission(PermissionType.Devices,
                                                             PermissionLevel.ReadWrite)})
    def actions_run(self, action_type):
        action_data = self.get_request_data_as_object()
        action_data['action_type'] = action_type
        return self.run_actions(action_data)

    @gui_add_rule_logged_in("actions/upload_file", methods=['POST'],
                            required_permissions={Permission(PermissionType.Adapters,
                                                             PermissionLevel.ReadWrite)})
    def actions_upload_file(self):
        return self._upload_file(self.device_control_plugin)

    def get_alerts(self, limit, mongo_filter, mongo_projection, mongo_sort, skip):
        report_service = self.get_plugin_by_name('reports')[PLUGIN_UNIQUE_NAME]
        sort = []
        for field, direction in mongo_sort.items():
            sort.append((field, direction))
        if not sort:
            sort.append(('report_creation_time', pymongo.DESCENDING))
        return [gui_helpers.beautify_db_entry(report) for report in
                self._get_collection('reports', db_name=report_service).find(
                    mongo_filter, projection=mongo_projection).sort(sort).skip(skip).limit(limit)]

    def put_alert(self, report_to_add):
        view_name = report_to_add['view']
        entity = EntityType(report_to_add['viewEntity'])
        views_collection = self.gui_dbs.entity_query_views_db_map[entity]
        if views_collection.find_one({'name': view_name}) is None:
            return return_error(f"Missing view {view_name} requested for creating alert")
        response = self.request_remote_plugin("reports", "reports", method='put', json=report_to_add)
        return response.text, response.status_code

    def delete_alert(self, report_ids):
        # Since other method types cause the function to return - here we have DELETE request
        if report_ids is None or len(report_ids) == 0:
            logger.error('No alert provided to be deleted')
            return ''
        response = self.request_remote_plugin("reports", "reports", method='DELETE', json=report_ids)
        if response is None:
            return return_error("No response whether alert was removed")
        return response.text, response.status_code

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_add_rule_logged_in("alert", methods=['GET', 'PUT', 'DELETE'],
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

        report_ids = self.get_request_data_as_object()
        return self.delete_alert(report_ids)

    @gui_helpers.filtered()
    @gui_add_rule_logged_in("alert/count", required_permissions={Permission(PermissionType.Alerts,
                                                                            PermissionLevel.ReadOnly)})
    def alert_count(self, mongo_filter):
        with self._get_db_connection() as db_connection:
            report_service = self.get_plugin_by_name('reports')[PLUGIN_UNIQUE_NAME]
            return jsonify(db_connection[report_service]['reports'].count_documents(mongo_filter))

    @gui_add_rule_logged_in("alert/<alert_id>", methods=['POST'],
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
            return return_error(f"Missing view {view_name} requested for updating alert")

        response = self.request_remote_plugin(f"reports/{alert_id}", "reports", method='post',
                                              json=alert_to_update)
        if response is None:
            return return_error("No response whether alert was updated")

        return response.text, response.status_code

    @gui_add_rule_logged_in("plugins")
    def plugins(self):
        """
        Get all plugins configured in core and update each one's status.
        Status will be "error" if the plugin is not registered.
        Otherwise it will be "success", if currently running or "warning", if  stopped.

        :mongo_filter
        :return: List of plugins with
        """
        plugins_available = requests.get(self.core_address + '/register').json()
        with self._get_db_connection() as db_connection:
            plugins_from_db = db_connection['core']['configs'].find({'plugin_type': 'Plugin'}).sort(
                [(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
            plugins_to_return = []
            for plugin in plugins_from_db:
                # TODO check supported features
                if plugin['plugin_type'] != "Plugin" or plugin['plugin_name'] in [AGGREGATOR_PLUGIN_NAME,
                                                                                  "gui",
                                                                                  "watch_service",
                                                                                  "execution",
                                                                                  "system_scheduler"]:
                    continue

                processed_plugin = {'plugin_name': plugin['plugin_name'],
                                    'unique_plugin_name': plugin[PLUGIN_UNIQUE_NAME],
                                    'status': 'error',
                                    'state': 'Disabled'
                                    }
                if plugin[PLUGIN_UNIQUE_NAME] in plugins_available:
                    processed_plugin['status'] = 'warning'
                    response = self.request_remote_plugin(
                        "trigger_state/execute", plugin[PLUGIN_UNIQUE_NAME])
                    if response.status_code != 200:
                        logger.error("Error getting state of plugin {0}".format(
                            plugin[PLUGIN_UNIQUE_NAME]))
                        processed_plugin['status'] = 'error'
                    else:
                        processed_plugin['state'] = response.json()
                        if (processed_plugin['state']['state'] != 'Disabled'):
                            processed_plugin['status'] = "success"
                plugins_to_return.append(processed_plugin)

            return jsonify(plugins_to_return)

    @staticmethod
    def __extract_configs_and_schemas(db_connection, plugin_unique_name):
        """
        Gets the configs and configs schemas in a nice way for a specific plugin
        """
        plugin_data = {}
        schemas = list(db_connection[plugin_unique_name]['config_schemas'].find())
        configs = list(db_connection[plugin_unique_name][CONFIGURABLE_CONFIGS].find())
        for schema in schemas:
            associated_config = [c for c in configs if c['config_name'] == schema['config_name']]
            if not associated_config:
                logger.error(f"Found schema without associated config for {plugin_unique_name}" +
                             f" - {schema['config_name']}")
                continue
            associated_config = associated_config[0]
            plugin_data[associated_config['config_name']] = {
                "schema": schema['schema'],
                "config": associated_config['config']
            }
        return plugin_data

    @gui_add_rule_logged_in("plugins/configs/<plugin_unique_name>/<config_name>", methods=['POST', 'GET'],
                            required_permissions={Permission(PermissionType.Settings,
                                                             ReadOnlyJustForGet)})
    def plugins_configs_set(self, plugin_unique_name, config_name):
        """
        Set a specific config on a specific plugin
        """
        if request.method == 'POST':
            config_to_set = request.get_json(silent=True)
            if config_to_set is None:
                return return_error("Invalid config", 400)
            email_settings = config_to_set.get('email_settings')
            if plugin_unique_name == 'core' and config_name == 'CoreService' and email_settings and email_settings.get(
                    'enabled') is True:

                if not email_settings.get('smtpHost') or not email_settings.get('smtpPort'):
                    return return_error('Host and Port are required to connect to email server', 400)
                email_server = EmailServer(email_settings['smtpHost'], email_settings['smtpPort'],
                                           email_settings.get('smtpUser'), email_settings.get('smtpPassword'),
                                           self._grab_file_contents(email_settings.get(
                                               'smtpKey'), stored_locally=False),
                                           self._grab_file_contents(email_settings.get('smtpCert'),
                                                                    stored_locally=False))
                try:
                    with email_server:
                        # Just to test connection
                        logger.info(f'Connection to email server with host {email_settings["smtpHost"]}')
                except Exception:
                    message = f'Could not connect to mail server "{email_settings["smtpHost"]}"'
                    logger.exception(message)
                    return return_error(message, 400)
            self._update_plugin_config(plugin_unique_name, config_name, config_to_set)
            return ""
        if request.method == 'GET':
            with self._get_db_connection() as db_connection:
                config_collection = db_connection[plugin_unique_name][CONFIGURABLE_CONFIGS]
                schema_collection = db_connection[plugin_unique_name]['config_schemas']
                return jsonify({'config': config_collection.find_one({'config_name': config_name})['config'],
                                'schema': schema_collection.find_one({'config_name': config_name})['schema']})

    @gui_add_rule_logged_in("configuration", methods=['GET'])
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

    def _update_plugin_config(self, plugin_unique_name, config_name, config_to_set):
        """
        Update given configuration settings for given configuration name, under given plugin.
        Finally, updates the plugin on the change.

        :param plugin_unique_name: Of whom to update the configuration
        :param config_name: To update
        :param config_to_set:
        """
        with self._get_db_connection() as db_connection:
            config_collection = db_connection[plugin_unique_name][CONFIGURABLE_CONFIGS]
            config_collection.replace_one(filter={
                'config_name': config_name
            },
                replacement={
                    "config_name": config_name,
                    "config": config_to_set
            })
            self.request_remote_plugin("update_config", plugin_unique_name, method='POST')

    @gui_add_rule_logged_in("plugins/<plugin_unique_name>/<command>", methods=['POST'],
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
        response = self.request_remote_plugin(f"{command}/{request_data['trigger']}", plugin_unique_name, method='post')
        if response and response.status_code == 200:
            return ""
        return response.json(), response.status_code

    @gui_add_rule_logged_in("config/<config_name>", methods=['POST', 'GET'],
                            required_permissions={Permission(PermissionType.Settings,
                                                             ReadOnlyJustForGet)})
    def config(self, config_name):
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
                return return_error("Invalid filter", 400)
            configs_collection.update({'name': config_name},
                                      {'name': config_name, 'value': config_to_add},
                                      upsert=True)
            return ""

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_add_rule_logged_in("notifications", methods=['POST', 'GET'],
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
                    pipeline = [{"$group": {"_id": "$title", "count": {"$sum": 1}, "date": {"$last": "$_id"},
                                            "severity": {"$last": "$severity"}, "seen": {"$last": "$seen"}}},
                                {"$addFields": {"title": "$_id"}}]
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
                        mongo_filter, projection={"_id": 1, "who": 1, "plugin_name": 1, "type": 1, "title": 1,
                                                  "seen": 1, "severity": 1}).sort(sort).skip(skip).limit(limit)]

                return jsonify(notifications)
            # POST
            elif request.method == 'POST':
                # if no ID is sent all notifications will be changed to seen.
                notifications_to_see = request.get_json(silent=True)
                if notifications_to_see is None or len(notifications_to_see['notification_ids']) == 0:
                    update_result = notification_collection.update_many(
                        {"seen": False}, {"$set": {'seen': notifications_to_see.get('seen', True)}})
                else:
                    update_result = notification_collection.update_many(
                        {"_id": {"$in": [ObjectId(x) for x in notifications_to_see.get('notification_ids', [])]}
                         }, {"$set": {'seen': True}})
                return str(update_result.modified_count), 200

    @gui_helpers.filtered()
    @gui_add_rule_logged_in("notifications/count", methods=['GET'],
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

    @gui_add_rule_logged_in("notifications/<notification_id>", methods=['GET'],
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

    @gui_helpers.add_rule_unauth("get_login_options")
    def get_login_options(self):
        return jsonify({
            "okta": {
                'enabled': self.__okta['enabled'],
                "client_id": self.__okta['client_id'],
                "url": self.__okta['url'],
                "gui_url": self.__okta['gui_url']
            },
            "google": {
                'enabled': self.__google['enabled'],
                'client_id': self.__google['client_id']
            },
            "ldap": {
                'enabled': self.__ldap_login['enabled'],
                'default_domain': self.__ldap_login['default_domain']
            }
        })

    @staticmethod
    def __validate_master_password(user_name: str, password: str) -> bool:
        """
        If the user has forgotten his password it is possible to allow a 'master' password
        by placing a file with that master password in a well defined location on this machine
        :return: whether or not the given password is the master password
        """
        if user_name != 'admin':
            return False
        try:
            master_password = open('master_password').read()
            return master_password and master_password == password
        except Exception:
            return False

    @gui_helpers.add_rule_unauth("login", methods=['GET', 'POST'])
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
            return jsonify(beautify_user_entry(user)), 200

        log_in_data = self.get_request_data_as_object()
        if log_in_data is None:
            return return_error("No login data provided", 400)
        user_name = log_in_data.get('user_name')
        password = log_in_data.get('password')
        remember_me = log_in_data.get('remember_me', False)
        if not isinstance(remember_me, bool):
            return return_error("remember_me isn't boolean", 401)
        user_from_db = self.__users_collection.find_one({
            'user_name': user_name,
            'source': 'internal'  # this means that the user must be a local user and not one from an external service
        })
        if user_from_db is None:
            logger.info(f"Unknown user {user_name} tried logging in")
            return return_error("Wrong user name or password", 401)

        if not bcrypt.verify(password, user_from_db['password']) and not self.__validate_master_password(user_name, password):
            logger.info(f"User {user_name} tried logging in with wrong password")
            return return_error("Wrong user name or password", 401)
        if request and request.referrer and 'localhost' not in request.referrer and '127.0.0.1' not in request.referrer:
            self.system_collection.replace_one({'type': 'server'},
                                               {'type': 'server', 'server_name': parse_url(request.referrer).host},
                                               upsert=True)
        self.__perform_login_with_user(user_from_db, remember_me)
        return ""

    def __perform_login_with_user(self, user, remember_me=False):
        """
        Given a user, mark the current session as associated with it
        """
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
        user = self.__create_user_if_doesnt_exist(username, first_name, last_name, picname, source)
        self.__perform_login_with_user(user, remember_me)

    def __create_user_if_doesnt_exist(self, username, first_name, last_name, picname=None, source='internal',
                                      password=None):
        """
        Create a new user in the system if it does not exist already
        :return: Created user
        """
        if source != 'internal' and password:
            password = bcrypt.hash(password)

        user = self.__users_collection.find_one({
            'user_name': username,
            'source': source
        })
        if not user:
            user = {
                'user_name': username,
                'first_name': first_name,
                'last_name': last_name,
                'pic_name': picname or self.DEFAULT_AVATAR_PIC,
                'permissions': {
                    p.name: PermissionLevel.Restricted.name for p in PermissionType
                },
                'source': source,
                'password': password,
                'api_key': secrets.token_urlsafe(),
                'api_secret': secrets.token_urlsafe()
            }
            user['permissions'][PermissionType.Dashboard.name] = PermissionLevel.ReadOnly.name
            self.__users_collection.insert_one(user)
        return user

    @gui_helpers.add_rule_unauth("okta-redirect")
    def okta_redirect(self):
        okta_settings = self.__okta
        if not okta_settings['enabled']:
            return return_error("Okta login is disabled", 400)
        claims = try_connecting_using_okta(okta_settings)
        if claims:
            self.__exteranl_login_successful(
                'okta',
                claims['email'],
                claims.get('given_name', ''),
                claims.get('family_name', '')
            )

        return redirect("/", code=302)

    @gui_helpers.add_rule_unauth("ldap-login", methods=['POST'])
    def ldap_login(self):
        try:
            log_in_data = self.get_request_data_as_object()
            if log_in_data is None:
                return return_error("No login data provided", 400)
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
                logger.exception("Failed login")
                return return_error("Failed logging into AD")
            except Exception:
                logger.exception("Unexpected exception")
                return return_error("Failed logging into AD")

            user = conn.get_user(user_name)
            if not user:
                return return_error("Failed login")

            needed_group = ldap_login["group_cn"]
            if needed_group:
                groups = user.get('memberOf', [])
                if not any((f'CN={needed_group}' in group) for group in groups):
                    return return_error(f"The provided user is not in the group {needed_group}")
            image = None
            try:
                thumbnail_photo = user.get("thumbnailPhoto") or \
                    user.get("exchangePhoto") or \
                    user.get("jpegPhoto") or \
                    user.get("photo") or \
                    user.get("thumbnailLogo")
                if thumbnail_photo is not None:
                    if type(thumbnail_photo) == list:
                        thumbnail_photo = thumbnail_photo[0]  # I think this can happen from some reason..
                    image = bytes_image_to_base64(thumbnail_photo)
            except Exception:
                logger.exception(f"Exception while setting thumbnailPhoto for user {user_name}")

            self.__exteranl_login_successful('ldap',
                                             user.get('displayName') or user_name,
                                             user.get('givenName') or '',
                                             user.get('sn') or '',
                                             image or self.DEFAULT_AVATAR_PIC)
            return ""
        except ldap3.core.exceptions.LDAPException:
            return return_error("LDAP verification has failed, please try again")
        except Exception:
            logger.exception("LDAP Verification error")
            return return_error("An error has occurred while verifying your account")

    @gui_helpers.add_rule_unauth("google-login", methods=['POST'])
    def google_login(self):
        """
        Login with google
        """
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests
        except ImportError:
            return return_error("Import error, Google login isn't available")
        google_creds = self.__google

        if not google_creds['enabled']:
            return return_error('Google login is disabled', 400)

        log_in_data = self.get_request_data_as_object()
        if log_in_data is None:
            return return_error("No login data provided", 400)

        token = log_in_data.get('id_token')
        if token is None:
            return return_error("No id_token provided", 400)

        try:
            # Specify the CLIENT_ID of the app that accesses the backend:
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), google_creds['client_id'])

            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')

            # If auth request is from a G Suite domain:
            if google_creds['allowed_domain'] and idinfo.get('hd') != google_creds['allowed_domain']:
                return return_error('Wrong hosted domain.')

            if google_creds['allowed_group']:
                user_id = idinfo.get('sub')
                if not user_id:
                    return return_error("No user id present")
                auth_file = json.loads(self._grab_file_contents(google_creds['keypair_file']))
                from axonius.clients.g_suite_admin_connection import GSuiteAdminConnection
                connection = GSuiteAdminConnection(auth_file, google_creds['account_to_impersonate'],
                                                   ['https://www.googleapis.com/auth/admin.directory.group.readonly'])
                if not any(google_creds['allowed_group'] in group.get('name', '')
                           for group
                           in connection.get_user_groups(user_id)):
                    return return_error(f"You're not in the allowed group {google_creds['allowed_group']}")

            # ID token is valid. Get the user's Google Account ID from the decoded token.
            self.__exteranl_login_successful('google',
                                             idinfo.get('name') or 'unamed',
                                             idinfo.get('given_name') or 'unamed',
                                             idinfo.get('family_name') or 'unamed',
                                             idinfo.get('picture') or self.DEFAULT_AVATAR_PIC)
            return ""
        except ValueError:
            logger.exception("Invalid token")
            return return_error("Invalid token")
        except Exception:
            logger.exception("Unknown exception")
            return return_error("Error logging in, please try again")

    @gui_add_rule_logged_in("logout", methods=['GET'])
    def logout(self):
        """
        Clears session, logs out
        :return:
        """
        logger.info(f"User {session} has logged out")
        session['user'] = None
        return ""

    @gui_helpers.paginated()
    @gui_add_rule_logged_in("authusers", methods=['GET', 'POST'],
                            required_permissions={Permission(PermissionType.Settings,
                                                             ReadOnlyJustForGet)})
    def authusers(self, limit, skip):
        """
        View users or change user password
        :param limit: limit for pagination
        :param skip: start index for pagination
        :return:
        """
        if request.method == 'GET':
            return jsonify(beautify_user_entry(n) for n in
                           self.__users_collection.find({}).sort(
                               [
                                   ('_id', pymongo.ASCENDING)
                               ])
                           .skip(skip)
                           .limit(limit))
        elif request.method == 'POST':
            post_data = self.get_request_data_as_object()
            user = session.get('user')
            if user['user_name'] != post_data['user_name']:
                return return_error("Login to your user first")
            if not bcrypt.verify(post_data['old_password'], user['password']):
                return return_error("Given password is wrong")
            self.__users_collection.update({'user_name': user['user_name']},
                                           {
                                               "$set": {
                                                   'password': bcrypt.hash(post_data['new_password'])
                                               }
            })
            self.__invalidate_sessions(user['user_name'])
            self.__users_collection.find_one({'user_name': user['user_name']})
            return "", 200

    @gui_add_rule_logged_in("edit_foreign_user", methods=['POST', 'PUT'],
                            required_permissions={Permission(PermissionType.Settings,
                                                             PermissionLevel.ReadWrite)})
    def edit_foreign_user(self):
        """
        Allows changing a users' permission set
        """
        post_data = self.get_request_data_as_object()
        if request.method == 'POST':
            self.__users_collection.update({'user_name': post_data['user_name']},
                                           {
                                               "$set": {
                                                   'permissions': post_data['permissions']
                                               }
            })
            self.__invalidate_sessions(post_data['user_name'])
            return ""
        elif request.method == 'PUT':
            post_data['password'] = bcrypt.hash(post_data['password'])
            if self.__users_collection.find_one({
                'user_name': post_data['user_name'],
                'source': 'internal'
            }):
                return return_error("User already exists", 400)
            self.__create_user_if_doesnt_exist(post_data['user_name'], post_data['first_name'], post_data['last_name'],
                                               picname=None, source='internal', password=post_data['password'])
            return ""

    @gui_helpers.add_rule_unauth("get_constants")
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

    def __invalidate_sessions(self, user_name: str):
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
            if d.get('user') and d['user'].get('user_name') == user_name:
                d['user'] = None

    @gui_add_rule_logged_in("get_api_key", methods=['GET', 'POST'])
    def get_api_key(self):
        """
        Get or change the API key
        """
        if request.method == 'POST':
            new_token = secrets.token_urlsafe()
            new_api_key = secrets.token_urlsafe()
            self.__users_collection.update({'user_name': session['user']['user_name']},
                                           {
                                               "$set": {
                                                   'api_key': new_api_key,
                                                   'api_secret': new_token
                                               }
            })
        api_data = self.__users_collection.find_one({'user_name': session['user']['user_name']})
        return jsonify({
            'api_key': api_data['api_key'],
            'api_secret': api_data['api_secret']
        })

    @gui_helpers.paginated()
    @gui_add_rule_logged_in("logs")
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

    @gui_add_rule_logged_in("dashboard/first_use", methods=['GET'])
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
                logger.exception(f"When dealing with {view_name} and {view['entity']}")
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

    @gui_add_rule_logged_in("saved_card_results/<card_uuid>", methods=['GET'],
                            required_permissions={Permission(PermissionType.Dashboard,
                                                             PermissionLevel.ReadOnly)})
    def saved_card_results(self, card_uuid: str):
        """
        Saved results for cards, i.e. the mechanism used to show the user the results
        of some "card" (collection of views) in the past
        """
        from_given_date = request.args.get('date_from')
        if not from_given_date:
            return return_error("date_from must be provided")
        to_given_date = request.args.get('date_to')
        if not to_given_date:
            return return_error("date_to must be provided")
        try:
            from_given_date = parse_date(from_given_date)
            to_given_date = parse_date(to_given_date)
        except Exception:
            return return_error("Given date is invalid")
        card = self._get_collection('dashboard').find_one({'_id': ObjectId(card_uuid)})
        if not card:
            return return_error("Card doesn't exist")

        res = None
        try:
            card_metric = ChartMetrics[card['metric']]
            handler_by_metric = {
                ChartMetrics.compare: self._fetch_historical_chart_compare,
                ChartMetrics.intersect: self._fetch_historical_chart_intersect,
                ChartMetrics.segment: self._fetch_historical_chart_segment,
                ChartMetrics.abstract: self._fetch_historical_chart_abstract
            }
            res = handler_by_metric[card_metric](card, from_given_date, to_given_date)
        except KeyError:
            logger.exception(f'Card {card["name"]} must have metric field in order to be fetched')

        if res is None:
            logger.error(f"Unexpected card found - {card['name']} {card['metric']}")
            return return_error("Unexpected error")

        return jsonify({x['name']: x for x in res})

    @gui_add_rule_logged_in("first_historical_date", methods=['GET'],
                            required_permissions={Permission(PermissionType.Dashboard,
                                                             PermissionLevel.ReadOnly)})
    def saved_card_results_min(self):
        dates = [self._historical_entity_views_db_map[entity_type].find_one({},
                                                                            sort=[('accurate_for_datetime', 1)],
                                                                            projection=['accurate_for_datetime'])
                 for entity_type in EntityType]
        minimum_date = min(
            (d['accurate_for_datetime']
             for d in dates
             if d), default=None)
        return jsonify(minimum_date)

    @gui_add_rule_logged_in("dashboard", methods=['POST', 'GET'],
                            required_permissions={Permission(PermissionType.Dashboard,
                                                             ReadOnlyJustForGet)})
    def get_dashboard(self):
        if request.method == 'GET':
            return jsonify(self._get_dashboard())

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

    def _get_dashboard(self):
        """
        GET Fetch current dashboard chart definitions. For each definition, fetch each of it's views and
        fetch devices_db_view with their view. Amount of results is mapped to each views' name, under 'data' key,
        to be returned with the dashboard definition.

        POST Save a new dashboard chart definition, given it has a name and at least one query attached

        :return:
        """
        logger.info("Getting dashboard")
        for dashboard in self._get_collection('dashboard').find(filter_archived()):
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
                        config['entity'] = EntityType(dashboard['config']['entity'])
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
            view_dict = self._find_filter_by_name(entity, view["name"])
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
            return [{'name': 'ALL', 'value': 0}, *map(lambda x: {**x, 'value': x['value'] / total}, data)]
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
                     'view': {**base_view, 'query': {'filter': base_view["query"]["filter"]}}, 'module': entity.value}]

        child1_view = self._find_filter_by_name(entity, intersecting[0])
        child1_filter = child1_view['query']['filter']
        child1_query = parse_filter(child1_filter)
        base_filter = f'({base_view["query"]["filter"]}) and ' if base_view["query"]["filter"] else ''
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
            child1_view['query']['filter'] = f'{base_filter}({child1_filter}) and NOT [{child2_filter}]'
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
                {'name': ' + '.join(intersecting), 'intersection': True, 'value': data_collection.count_documents({
                    '$and': base_queries + [
                        child1_query, child2_query
                    ]
                }) / total, 'view': {**base_view,
                                     'query': {'filter': f'{base_filter}({child1_filter}) and ({child2_filter})'}},
                    'module': entity.value})

            # Child2 + Parent - Intersection
            child2_view['query']['filter'] = f'{base_filter}({child2_filter}) and NOT [{child1_filter}]'
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
            **base_view, 'query': {'filter': f'{base_filter}NOT [({child1_filter}){child2_or}]'}
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
        base_filter = f'({base_view["query"]["filter"]}) and ' if base_view["query"]["filter"] else ''
        data = []
        for item in aggregate_results:
            field_value = item["name"]
            if field_value == 'No Value':
                field_value = 'exists(false)'
            else:
                if (isinstance(field_value, str)):
                    field_value = f'\"{field_value}\"'
                if (isinstance(field_value, bool)):
                    field_value = str(field_value).lower()
            data.append({'name': str(item["name"]), 'value': item["value"], 'module': entity.value,
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
        base_query = {}
        if view:
            base_view = self._find_filter_by_name(entity, view)
            base_query = parse_filter(base_view['query']['filter'])
            base_view['query']['filter'] = f'({base_view["query"]["filter"]}) and ' if view else ''
        base_view['query']['filter'] = f'{base_view["query"]["filter"]}{field["name"]} == exists(true)'
        if for_date:
            # If history requested, fetch from appropriate historical db
            data_collection = self._historical_entity_views_db_map[entity]
            if base_query:
                base_query = {
                    '$and': [
                        base_query, {
                            field['name']: {
                                '$exists': True
                            }
                        }, {
                            'accurate_for_datetime': for_date
                        }
                    ]
                }
            else:
                base_query = {
                    'accurate_for_datetime': for_date
                }
        results = data_collection.find(base_query, projection={field['name']: 1})
        count = 0
        sigma = 0
        for item in results:
            field_values = gui_helpers.find_entity_field(item, field['name'])
            if field_values:
                if isinstance(field_values, list):
                    count += len(field_values)
                    if ChartFuncs[func] == ChartFuncs.average:
                        sigma += sum(field_values)
                else:
                    count += 1
                    if ChartFuncs[func] == ChartFuncs.average:
                        sigma += field_values
        if not count:
            return [{'name': view, 'value': 0, 'view': base_view, 'module': entity.value}]
        name = f'{func} of {field["title"]} on {view or "ALL"} results'
        if ChartFuncs[func] == ChartFuncs.average:
            return [
                {'name': name, 'value': (sigma / count), 'schema': field, 'view': base_view, 'module': entity.value}]
        return [{'name': name, 'value': count, 'view': base_view, 'module': entity.value}]

    def _fetch_chart_timeline(self, _: ChartViews, views, datefrom, dateto):
        """
        Fetch and count results for each view from given views, per day in given range of datefrom to dateto.
        Create for each view a sequence of points that represent the count for each day in the range.

        :param views: List of view for which to fetch results over timeline
        :param dateFrom: Date to start fetching from
        :param dateTo: Date to fetch up to
        :return:
        """
        logger.info(f'Gathering data between {datefrom} and {dateto}')
        try:
            dateto = parse_date(dateto)
            datefrom = parse_date(datefrom)
        except Exception:
            logger.exception('Given date to or from is invalid')
            return None

        return {
            'lines': self._fetch_view_timeline(views, datefrom, dateto),
            'scale': [(datefrom + timedelta(i)).strftime('%m/%d/%Y') for i in range((dateto - datefrom).days + 1)]
        }

    def _fetch_view_timeline(self, views, date_from, date_to):
        date_ranges = list(_get_date_ranges(date_from, date_to))
        for view in views:
            if not view.get('name'):
                continue
            entity = EntityType(view['entity'])
            base_view = self._find_filter_by_name(entity, view['name'])
            base_query = parse_filter(base_view['query']['filter'])

            def aggregate_for_date_range(args):
                rangefrom, rangeto = args
                return self._historical_entity_views_db_map[entity].aggregate([
                    {
                        '$match': {
                            '$and': [
                                base_query, {
                                    'accurate_for_datetime': {
                                        '$lte': datetime.combine(rangeto, datetime.min.time()),
                                        '$gte': datetime.combine(rangefrom, datetime.min.time())
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
            yield {
                'title': view['name'],
                'points': points
            }

    @gui_add_rule_logged_in("dashboard/<dashboard_id>", methods=['DELETE'],
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

    @gui_add_rule_logged_in("dashboard/lifecycle", methods=['GET'],
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
            return return_error(f"Error fetching status of system scheduler. Reason: {state_response.text}")

        state_response = state_response.json()
        state = state_response['state']
        is_stopping = state_response['stopping']
        is_research = state[StateLevels.Phase.name] == Phases.Research.name

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
            if is_research and sub_phase.name == state[StateLevels.SubPhase.name]:
                # Reached current status - set complementary of SubPhaseStatus value
                found_current = True
                sub_phases.append({'name': sub_phase.name, 'status': 1 - (state[StateLevels.SubPhaseStatus.name] or 1)})
            else:
                # Set 0 or 1, depending if reached current status yet
                sub_phases.append({'name': sub_phase.name, 'status': 0 if found_current else 1})

        run_time_response = self.request_remote_plugin('next_run_time', SYSTEM_SCHEDULER_PLUGIN_NAME)
        if run_time_response.status_code != 200:
            return return_error(f"Error fetching run time of system scheduler. Reason: {run_time_response.text}")

        return jsonify({
            'sub_phases': sub_phases, 'next_run_time': run_time_response.text, 'status': nice_state.name
        })

    @gui_add_rule_logged_in("dashboard/lifecycle_rate", methods=['GET', 'POST'],
                            required_permissions={Permission(PermissionType.Dashboard,
                                                             ReadOnlyJustForGet)})
    def system_lifecycle_rate(self):
        """

        """
        if self.get_method() == 'GET':
            response = self.request_remote_plugin('research_rate', SYSTEM_SCHEDULER_PLUGIN_NAME)
            return response.content
        elif self.get_method() == 'POST':
            response = self.request_remote_plugin(
                'research_rate', SYSTEM_SCHEDULER_PLUGIN_NAME, method='POST',
                json=self.get_request_data_as_object())
            logger.info(f"response code: {response.status_code} response crap: {response.content}")
            return ''

    def _adapter_data(self, entity_type: EntityType):
        """
        For each adapter currently registered in system, count how many devices it fetched.

        :return: Map between each adapter and the number of devices it has, unless no devices
        """
        logger.info(f'Getting adapter data for entity {entity_type.name}')
        adapter_entities = {'seen': 0, 'counters': []}
        entity_collection = self._entity_views_db_map[entity_type]
        adapter_entities['unique'] = entity_collection.count_documents({})
        entities_per_adapters = {}
        for res in entity_collection.aggregate([
            {
                "$group": {
                    "_id": "$adapters",
                    "count": {
                        "$sum": 1
                    }
                }
            }
        ]):
            for plugin_name in set(res['_id']):
                entities_per_adapters[plugin_name] = entities_per_adapters.get(plugin_name, 0) + res['count']
                adapter_entities['seen'] += res['count']

        for name, value in entities_per_adapters.items():
            adapter_entities['counters'].append({'name': name, 'value': value})

        return adapter_entities

    @gui_add_rule_logged_in("dashboard/adapter_data/<entity_name>", methods=['GET'],
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
        logger.info("Getting dashboard coverage")
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

    @gui_add_rule_logged_in("dashboard/coverage", methods=['GET'],
                            required_permissions={Permission(PermissionType.Dashboard,
                                                             PermissionLevel.ReadOnly)})
    def get_dashboard_coverage(self):
        return jsonify(self._get_dashboard_coverage())

    @gui_add_rule_logged_in("get_latest_report_date", methods=['GET'],
                            required_permissions={Permission(PermissionType.Reports,
                                                             PermissionLevel.ReadOnly)})
    def get_latest_report_date(self):
        recent_report = self._get_collection("reports").find_one({'filename': 'most_recent_report'})
        if recent_report is not None:
            return jsonify(recent_report['time'])
        return ''

    @gui_add_rule_logged_in("research_phase", methods=['POST'],
                            required_permissions={Permission(PermissionType.Dashboard,
                                                             PermissionLevel.ReadWrite)})
    def schedule_research_phase(self):
        """
        Schedules or initiates research phase.

        :return: Map between each adapter and the number of devices it has, unless no devices
        """
        scheduled_time = request.get_json(silent=True) or {}
        logger.info(f'Scheduling Research Phase to: {scheduled_time.get("timestamp", "Now!")}')
        if scheduled_time.get('timestamp'):
            response = self.request_remote_plugin(
                'trigger/execute', SYSTEM_SCHEDULER_PLUGIN_NAME, 'POST', json=scheduled_time)
        else:
            response = self.request_remote_plugin('trigger/execute', SYSTEM_SCHEDULER_PLUGIN_NAME, 'POST')

        if response.status_code != 200:
            message = f'Could not schedule research phase to: {scheduled_time.get("timestamp", "Now!")}'
            logger.error(message)
            return return_error(message, response.status_code)

        return ''

    @gui_add_rule_logged_in("stop_research_phase", methods=['POST'],
                            required_permissions={Permission(PermissionType.Dashboard,
                                                             PermissionLevel.ReadWrite)})
    def stop_research_phase(self):
        """
        Stops currently running research phase.
        """
        logger.info("Stopping research phase")
        response = self.request_remote_plugin('stop_all', SYSTEM_SCHEDULER_PLUGIN_NAME, 'POST')

        if response.status_code != 204:
            logger.error(
                f"Could not stop research phase. returned code: {response.status_code}, reason: {str(response.content)}")
            return return_error(f"Could not stop research phase {str(response.content)}", response.status_code)

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
                    logger.info(f'Executing filter {view_filter} on entity {entity.value}')
                    view_parsed = parse_filter(view_filter['query']['filter'])
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
                found_report = adapter_reports_db['report'].find_one({"name": "report"}) or {}
                adapter_clients_report = found_report.get('data', {})
            except Exception:
                logger.exception(f"Error contacting the report db for adapter {adapter_unique_name}")

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
            with self._get_db_connection() as db_connection:
                current_entity_fields = gui_helpers.entity_fields(entity, self.core_address, db_connection)
            name_to_title = {}
            for field in current_entity_fields['generic']:
                name_to_title[field['name']] = field['title']
            for type in current_entity_fields['specific']:
                for field in current_entity_fields['specific'][type]:
                    name_to_title[field['name']] = field['title']
            return name_to_title

        logger.info("Getting views data")
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
                        field_list = view.get('fields', [])
                        views_data.append({
                            'name': view_doc.get('name', f'View {i}'), 'entity': entity.value,
                            'fields': [{field_to_title.get(field, field): field} for field in field_list],
                            'data': list(gui_helpers.get_entities(limit=view.get('pageSize', 20),
                                                                  skip=0,
                                                                  view_filter=parse_filter(
                                                                      view.get('query', {}).get('filter', '')),
                                                                  sort=gui_helpers.get_sort(view),
                                                                  projection={field: 1 for field in field_list},
                                                                  entity_type=entity,
                                                                  default_sort=self._system_settings['defaultSort']))
                        })
                except Exception:
                    logger.exception(f"Problem with View {str(i)} ViewDoc {str(view_doc)}")
        return views_data

    @stoppable
    def _on_trigger(self):
        with self._get_db_connection() as db_connection:
            schemas = dict(db_connection['system_scheduler']['configurable_configs'].find_one())
            if schemas['config']['generate_report'] is True:
                return self.generate_new_report_offline()
            else:
                return

    def _triggered(self, job_name: str, post_json: dict, *args):
        if job_name != 'execute':
            logger.error(f"Got bad trigger request for non-existent job: {job_name}")
            return return_error("Got bad trigger request for non-existent job", 400)
        else:
            return self._on_trigger()

    def generate_new_report_offline(self):
        '''
        Generates a new version of the report as a PDF file and saves it to the db
        (this method is NOT an endpoint)

        :return: "Success" if successful, error if there is an error
        '''

        try:
            logger.info("Rendering Report.")
            # generate_report() renders the report html
            report_html = self.generate_report()
            # Writes the report pdf to a file-like object and use seek() to point to the beginning of the stream
            with io.BytesIO() as report_data:
                report_html.write_pdf(report_data)
                report_data.seek(0)
                # Uploads the report to the db and returns a uuid to retrieve it
                uuid = self._upload_report(report_data)
                logger.info(f"Report was saved to the db {uuid}")
                # Stores the uuid in the db in the "reports" collection
                self._get_collection("reports").replace_one(
                    {'filename': 'most_recent_report'},
                    {'uuid': uuid, 'filename': 'most_recent_report', 'time': datetime.now()}, True
                )
            return "Success"
        except Exception as e:
            logger.exception('Failed to generate report.')
            return return_error(f'Problem generating report:\n{str(e.args[0]) if e.args else e}', 400)

    def _upload_report(self, report):
        """
        Uploads the latest report PDF to the db
        :param report: report data
        :return:
        """
        if not report:
            return return_error("Report must exist", 401)

        # First, need to delete the old report
        self._delete_last_report()

        report_name = "most_recent_report"
        with self._get_db_connection() as db_connection:
            fs = gridfs.GridFS(db_connection[GUI_NAME])
            written_file_id = fs.put(report, filename=report_name)
            logger.info("Report successfully placed in the db")
        return str(written_file_id)

    def _delete_last_report(self):
        """
        Deletes the last version of the report pdf to avoid having too many saved versions
        :return:
        """
        report_collection = self._get_collection("reports")
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
        with self._get_db_connection() as db_connection:
            schemas = dict(db_connection['system_scheduler']['configurable_configs'].find_one())
            if schemas['config']['generate_report'] is False:
                self.generate_new_report_offline()

            uuid = self._get_collection("reports").find_one({'filename': 'most_recent_report'})['uuid']
            report_path = f'/tmp/axonius-report_{datetime.now()}.pdf'
            with gridfs.GridFS(db_connection[GUI_NAME]).get(ObjectId(uuid)) as report_content:
                open(report_path, 'wb').write(report_content.read())
                return report_path

    def generate_report(self):
        """
        Generates the report and returns html.
        :return: the generated report file path.
        """
        logger.info("Starting to generate report")
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
            return ""
        except Exception as e:
            logger.exception('Failed sending test report by email.')
            return return_error(f'Problem testing report by email:\n{str(e.args[0]) if e.args else e}', 400)

    def _get_exec_report_settings(self, exec_reports_settings_collection):
        settings_object = exec_reports_settings_collection.find_one({}, projection={'_id': False, 'period': True,
                                                                                    'recipients': True})
        return settings_object or {}

    def _schedule_exec_report(self, exec_reports_settings_collection, exec_report_data):
        logger.info("rescheduling exec_report")
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
            raise ValueError("period have to be in ('daily', 'monthly', 'weekly').")

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
        logger.info(f"Scheduling an exec_report sending for {next_run_time} and period of {time_period}.")
        return "Scheduled next run."

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
                logger.info("Email cannot be sent because no email server is configured")
                raise RuntimeWarning("No email server configured")

    @gui_add_rule_logged_in('support_access', methods=['GET', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Settings,
                                                             ReadOnlyJustForGet)})
    def support_access(self):
        """
        Try retrieving current job for stopping the support access.
        If GET request, return its scheduled time or empty, if doesn't exist.
        If POST request, update the time of the job or create one, if doesn't exist.
        The time to stop is according to the given duration.

        :return: Current time of stop jon for GET request, empty string otherwise
        """
        support_access_job = self._job_scheduler.get_job(SUPPORT_ACCESS_THREAD_ID)
        if request.method == 'POST':
            duration_param = self.get_request_data_as_object().get('duration', 24)
            try:
                next_run_time = time_from_now(float(duration_param))
            except ValueError:
                message = f'Value for "duration" parameter must be a number, instead got {duration_param}'
                logger.exception(message)
                return return_error(message, 400)

            logger.info('Starting Support Access')
            self._update_support_access(True)
            if support_access_job is not None:
                # Job exists, not creating another
                logger.info(f'Job already existing - updating its run time to {next_run_time}')
                support_access_job.modify(next_run_time=next_run_time)
                # self._job_scheduler.reschedule_job(SUPPORT_ACCESS_THREAD_ID, trigger='date')
            else:
                logger.info(f'Creating a stop job for the time {next_run_time}')
                self._job_scheduler.add_job(func=self._stop_support_access,
                                            trigger='date',
                                            next_run_time=next_run_time,
                                            name=SUPPORT_ACCESS_THREAD_ID,
                                            id=SUPPORT_ACCESS_THREAD_ID,
                                            max_instances=1)

        elif request.method == 'GET':
            if not support_access_job:
                logger.info('No current job for ending the support access - it was already triggered')
                return ''
            return str(int(time.mktime(support_access_job.next_run_time.timetuple())))

        elif request.method == 'DELETE':
            self._stop_support_access()
            if support_access_job:
                support_access_job.remove()
        return ''

    def _stop_support_access(self):
        logger.info('Stopping Support Access')
        self._update_support_access(False)

    def _update_support_access(self, support_access_on):
        """
        Fetch current config belong
        :param support_access_on:
        :return:
        """
        config_document = self._get_collection(CONFIGURABLE_CONFIGS, CORE_UNIQUE_NAME).find_one({
            'config_name': 'CoreService'
        })
        if not config_document:
            logger.error('Cannot start the support access, since controlling configuration is not found')
            return
        config_to_set = config_document['config']
        config_to_set[MAINTENANCE_SETTINGS][ANALYTICS_SETTING] = support_access_on
        config_to_set[MAINTENANCE_SETTINGS][TROUBLESHOOTING_SETTING] = support_access_on
        self._update_plugin_config(CORE_UNIQUE_NAME, 'CoreService', config_to_set)

    @gui_add_rule_logged_in('metadata', methods=['GET'], required_permissions={Permission(PermissionType.Settings,
                                                                                          PermissionLevel.ReadOnly)})
    def get_metadata(self):
        """
        Gets the system metadata.
        :return:
        """
        return jsonify(self.metadata)

    @property
    def plugin_subtype(self):
        return "Post-Correlation"

    @property
    def system_collection(self):
        return self._get_collection(GUI_SYSTEM_CONFIG_COLLECTION)

    @property
    def exec_report_collection(self):
        return self._get_collection('exec_reports_settings')

    @property
    def device_control_plugin(self):
        return self.get_plugin_by_name(DEVICE_CONTROL_PLUGIN_NAME)[PLUGIN_UNIQUE_NAME]

    def get_plugin_unique_name(self, plugin_name):
        return self.get_plugin_by_name(plugin_name)[PLUGIN_UNIQUE_NAME]

    def _on_config_update(self, config):
        logger.info(f"Loading GuiService config: {config}")
        self.__okta = config['okta_login_settings']
        self.__google = config['google_login_settings']
        self.__ldap_login = config['ldap_login_settings']
        self._system_settings = config[SYSTEM_SETTINGS]

    @gui_helpers.add_rule_unauth('analytics')
    def get_analytics(self):
        return jsonify(self._maintenance_settings[ANALYTICS_SETTING])

    @gui_helpers.add_rule_unauth('troubleshooting')
    def get_troubleshooting(self):
        return jsonify(self._maintenance_settings[TROUBLESHOOTING_SETTING])

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            "items": [
                {
                    "items": [
                        {
                            "name": "refreshRate",
                            "title": "Auto-Refresh Rate (seconds)",
                            "type": "number"
                        },
                        {
                            "name": "singleAdapter",
                            "title": "Use Single Adapter View",
                            "type": "bool"
                        },
                        {
                            "name": "multiLine",
                            "title": "Use Table Multi Line View",
                            "type": "bool"
                        },
                        {
                            "name": "defaultSort",
                            "title": "Sort by Number of Adapters in Default View",
                            "type": "bool"
                        },
                        {
                            "name": "percentageThresholds",
                            "title": "Percentage Fields Severity Scopes",
                            "type": "array",
                            "items": [
                                {
                                    "name": "error",
                                    "title": "Poor under:",
                                    "type": "integer"
                                },
                                {
                                    "name": "warning",
                                    "title": "Average under:",
                                    "type": "integer"
                                },
                                {
                                    "name": "success",
                                    "title": "Good under:",
                                    "type": "integer"
                                }
                            ],
                            "required": ["error", "warning", "success"]
                        },
                        {
                            "name": "tableView",
                            "title": "Present advanced General Data of entity in a table",
                            "type": "bool"
                        }
                    ],
                    "required": ["refreshRate", "singleAdapter", "multiLine", "defaultSort", "tableView"],
                    "name": SYSTEM_SETTINGS,
                    "title": "System Settings",
                    "type": "array"
                },
                {
                    "items": [
                        {
                            "name": "enabled",
                            "title": "Allow Okta logins",
                            "type": "bool"
                        },
                        {
                            "name": "client_id",
                            "title": "Okta application client id",
                            "type": "string"
                        },
                        {
                            "name": "client_secret",
                            "title": "Okta application client secret",
                            "type": "string"
                        },
                        {
                            "name": "url",
                            "title": "Okta application URL",
                            "type": "string"
                        },
                        {
                            "name": "gui_url",
                            "title": "The URL of Axonius GUI",
                            "type": "string"
                        }
                    ],
                    "required": ["enabled", "client_id", "client_secret", "url", "gui_url"],
                    "name": "okta_login_settings",
                    "title": "Okta Login Settings",
                    "type": "array"
                },
                {
                    "items": [
                        {
                            "name": "enabled",
                            "title": "Allow Google logins",
                            "type": "bool"
                        },
                        {
                            "name": "client_id",
                            "title": "Google client id",
                            "type": "string"
                        },
                        {
                            "name": "account_to_impersonate",
                            "title": "Email of an admin account to impersonate",
                            "type": "string"
                        },
                        {
                            "name": "keypair_file",
                            "title": "JSON Key pair for the service account",
                            "description": "The binary contents of the keypair file",
                            "type": "file",
                        },
                        {
                            "name": "allowed_domain",
                            "title": "Allowed G Suite domain (Leave empty for all domains)",
                            "type": "string"
                        },
                        {
                            "name": "allowed_group",
                            "title": "Only users in this group will be allowed (Leave empty for all groups)",
                            "type": "string"
                        }
                    ],
                    "required": ["enabled", "client_id", 'account_to_impersonate', 'keypair_file'],
                    "name": "google_login_settings",
                    "title": "Google Login Settings",
                    "type": "array"
                },
                {
                    "items": [
                        {
                            "name": "enabled",
                            "title": "Allow LDAP logins",
                            "type": "bool"
                        },
                        {
                            "name": "dc_address",
                            "title": "The host domain controller IP or DNS",
                            "type": "string"
                        },
                        {
                            "name": "group_cn",
                            "title": "A group the user must be a part of",
                            "type": "string"
                        },
                        {
                            "name": "default_domain",
                            "title": "Default domain to present to the user",
                            "type": "string"
                        },
                        {
                            "name": "use_ssl",
                            "title": "Use SSL for connection",
                            "type": "string",
                            "enum": [SSLState.Unencrypted.name, SSLState.Verified.name, SSLState.Unverified.name],
                            "default": SSLState.Unverified.name,
                        },
                        {
                            "name": "ca_file",
                            "title": "CA File",
                            "description": "The binary contents of the ca_file",
                            "type": "file"
                        },
                        {
                            "name": "cert_file",
                            "title": "Certificate File",
                            "description": "The binary contents of the cert_file",
                            "type": "file"
                        },
                        {
                            "name": "private_key",
                            "title": "Private Key File",
                            "description": "The binary contents of the private_key",
                            "type": "file"
                        },
                    ],
                    "required": ["enabled", "dc_address"],
                    "name": "ldap_login_settings",
                    "title": "Ldap Login Settings",
                    "type": "array"
                }
            ],
            "type": "array"
        }

    @classmethod
    def _db_config_default(cls):
        return {
            "okta_login_settings": {
                "enabled": False,
                "client_id": "",
                "client_secret": "",
                "url": "https://yourname.okta.com",
                "gui_url": "https://127.0.0.1"
            },
            "ldap_login_settings": {
                "enabled": False,
                "dc_address": "",
                "default_domain": "",
                "group_cn": "",
                "use_ssl": SSLState.Unencrypted.name,
                "ca_file": None,
                "cert_file": None,
                "private_key": None
            },
            "google_login_settings": {
                "enabled": False,
                "client_id": None,
                "allowed_domain": None,
                "allowed_group": None,
                'account_to_impersonate': None,
                'keypair_file': None
            },
            SYSTEM_SETTINGS: {
                "refreshRate": 30,
                "singleAdapter": False,
                "multiLine": False,
                "defaultSort": True,
                "percentageThresholds": {
                    "error": 40,
                    "warning": 60,
                    "success": 100,
                },
                "tableView": True
            }
        }
