import csv
import logging
import threading
from typing import Iterable

import gridfs
import ldap3

from axonius.clients.ldap.exceptions import LdapException
from axonius.clients.ldap.ldap_connection import LdapConnection
from axonius.mixins.configurable import Configurable
from axonius.types.ssl_state import SSLState
from gui.okta_login import try_connecting_using_okta

logger = logging.getLogger(f"axonius.{__name__}")
from axonius.adapter_base import AdapterProperty

from axonius.thread_stopper import stoppable
from axonius.utils.files import get_local_config_file, create_temp_file
from axonius.utils.datetime import next_weekday
from axonius.plugin_base import PluginBase, add_rule, return_error, EntityType
from axonius.devices.device_adapter import DeviceAdapter
from axonius.users.user_adapter import UserAdapter
from axonius.consts.plugin_consts import ADAPTERS_LIST_LENGTH, PLUGIN_UNIQUE_NAME, DEVICE_CONTROL_PLUGIN_NAME, \
    PLUGIN_NAME, SYSTEM_SCHEDULER_PLUGIN_NAME, AGGREGATOR_PLUGIN_NAME, GUI_SYSTEM_CONFIG_COLLECTION, GUI_NAME, \
    METADATA_PATH, SYSTEM_SETTINGS, ANALYTICS_SETTING, TROUBLESHOOTING_SETTING, CONFIGURABLE_CONFIGS
from axonius.consts.scheduler_consts import ResearchPhases, StateLevels, Phases
from gui.consts import ChartTypes, EXEC_REPORT_THREAD_ID, EXEC_REPORT_TITLE, EXEC_REPORT_FILE_NAME, \
    EXEC_REPORT_EMAIL_CONTENT
from gui.report_generator import ReportGenerator
from axonius.thread_pool_executor import LoggedThreadPoolExecutor
from axonius.email_server import EmailServer
from axonius.mixins.triggerable import Triggerable
from axonius.utils import gui_helpers
from gui.api import API

import tarfile
from apscheduler.executors.pool import ThreadPoolExecutor as ThreadPoolExecutorApscheduler
from axonius.background_scheduler import LoggedBackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import io
import os
from datetime import date, datetime, timezone
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse as parse_date
from flask import jsonify, request, session, after_this_request, make_response, send_file, redirect
from passlib.hash import bcrypt
from elasticsearch import Elasticsearch
import requests
import configparser
import pymongo
from bson import ObjectId
import json
from axonius.utils.parsing import parse_filter, bytes_image_to_base64
from urllib3.util.url import parse_url
import re


# Caution! These decorators must come BEFORE @add_rule
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


class GuiService(PluginBase, Triggerable, Configurable, API):
    DEFAULT_AVATAR_PIC = '/src/assets/images/users/avatar.png'

    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__),
                         requested_unique_plugin_name=GUI_NAME, *args, **kwargs)
        self.wsgi_app.config['SESSION_TYPE'] = 'memcached'
        self.wsgi_app.config['SECRET_KEY'] = 'this is my secret key which I like very much, I have no idea what is this'
        self._elk_addr = self.config['gui_specific']['elk_addr']
        self._elk_auth = self.config['gui_specific']['elk_auth']
        current_user = self._get_collection('users').find_one({'user_name': 'admin'})
        if current_user is None:
            # User doesn't exist, this must be the installation process
            self._get_collection('users').update({'user_name': 'admin'},
                                                 {'user_name': 'admin',
                                                  'password':
                                                      '$2b$12$SjT4qshlg.uUpsgE3vHwp.7A0UtkGEoWfUR0wFet3WZuXTnMgOCIK',
                                                  'first_name': 'administrator', 'last_name': '',
                                                  'pic_name': self.DEFAULT_AVATAR_PIC}, upsert=True)

        self.add_default_views(EntityType.Devices, 'default_views_devices.ini')
        self.add_default_views(EntityType.Users, 'default_views_users.ini')
        self.add_default_reports('default_reports.ini')
        self.add_default_dashboard_charts('default_dashboard_charts.ini')
        if not self.system_collection.find({'type': 'server'}):
            self.system_collection.insert_one({'type': 'server', 'server_name': 'localhost'})

        # Start exec report scheduler
        self.exec_report_lock = threading.RLock()

        self._client_insertion_threadpool = LoggedThreadPoolExecutor(max_workers=20)  # Only for client insertion

        executors = {'default': ThreadPoolExecutorApscheduler(1)}
        self._exec_report_scheduler = LoggedBackgroundScheduler(executors=executors)

        current_exec_report_setting = self._get_exec_report_settings(self.exec_report_collection)
        if current_exec_report_setting != {}:
            self._schedule_exec_report(self.exec_report_collection, current_exec_report_setting)
        self._exec_report_scheduler.start()
        self.metadata = self.load_metadata()
        self._activate('execute')

    def load_metadata(self):
        try:
            if os.path.exists(METADATA_PATH):
                with open(METADATA_PATH, 'r') as metadata_file:
                    metadata_bytes = metadata_file.read()[:-1].replace('\\', '\\\\')
                    return json.loads(metadata_bytes)
        except Exception:
            logger.exception("Bad __build_metadata file.")
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
                    self._insert_view(self.gui.entity_query_views_db_map[entity_type], name, json.loads(view['view']))
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
                    self._insert_dashboard_chart(name, data['type'], json.loads(data['views']))
                except Exception as e:
                    logger.exception(f'Error adding default dashboard chart {name}. Reason: {repr(e)}')
        except Exception as e:
            logger.exception(f'Error adding default dashboard chart. Reason: {repr(e)}')

    def _insert_view(self, views_collection, name, mongo_view):
        existed_view = views_collection.find_one({'name': name})
        if existed_view is not None and not existed_view.get('archived'):
            logger.info(f'view {name} already exists id: {existed_view["_id"]}')
            return existed_view['_id']

        result = views_collection.insert_one({
            'name': name,
            'view': mongo_view,
            'query_type': 'saved',
            'timestamp': datetime.now()
        })
        logger.info(f'Added view {name} id: {result.inserted_id}')
        return result.inserted_id

    def _insert_report_config(self, name, report):
        reports_collection = self._get_collection("reports_config")
        existed_report = reports_collection.find_one({'name': name})
        if existed_report is not None and not existed_report.get('archived'):
            logger.info(f'Report {name} already exists under id: {existed_report["_id"]}')
            return

        result = reports_collection.insert_one({'name': name, 'adapters': json.loads(report['adapters'])})
        logger.info(f'Added report {name} id: {result.inserted_id}')

    def _insert_dashboard_chart(self, dashboard_name, dashboard_type, dashboard_views):
        dashboard_collection = self._get_collection("dashboard")
        existed_dashboard_chart = dashboard_collection.find_one({'name': dashboard_name})
        if existed_dashboard_chart is not None and not existed_dashboard_chart.get('archived'):
            logger.info(f'Report {dashboard_name} already exists under id: {existed_dashboard_chart["_id"]}')
            return

        result = dashboard_collection.insert_one({'name': dashboard_name,
                                                  'type': dashboard_type,
                                                  'views': dashboard_views})

        logger.info(f'Added report {dashboard_name} id: {result.inserted_id}')

    ########
    # DATA #
    ########

    def _get_csv(self, mongo_filter, mongo_sort, mongo_projection, entity_type: EntityType):
        """
        Given a entity_type, retrieve it's entities, according to given filter, sort and requested fields.
        The resulting list is processed into csv format and returned as a file content, to be downloaded by browser.

        :param mongo_filter:
        :param mongo_sort:
        :param mongo_projection:
        :param entity_type:
        :return:
        """
        logger.info("Generating csv")
        string_output = io.StringIO()
        entities = gui_helpers.get_entities(None, None, mongo_filter, mongo_sort, mongo_projection,
                                            self.gui.entity_query_views_db_map[entity_type],
                                            self._entity_views_db_map[entity_type], entity_type,
                                            default_sort=self._system_settings['defaultSort'])
        output = ''
        if len(entities) > 0:
            # Beautifying the resulting csv.
            del mongo_projection['internal_axon_id']
            del mongo_projection['unique_adapter_names']
            del mongo_projection[ADAPTERS_LIST_LENGTH]
            # Getting pretty titles for all generic fields as well as specific
            entity_fields = self._entity_fields(entity_type)
            for field in entity_fields['generic']:
                if field['name'] in mongo_projection:
                    mongo_projection[field['name']] = field['title']
            for type in entity_fields['specific']:
                for field in entity_fields['specific'][type]:
                    if field['name'] in mongo_projection:
                        mongo_projection[field['name']] = f'{" ".join(type.split("_")).capitalize()}: {field["title"]}'
            for current_entity in entities:
                del current_entity['internal_axon_id']
                del current_entity['unique_adapter_names']
                del current_entity[ADAPTERS_LIST_LENGTH]
                for field in mongo_projection.keys():
                    # Replace field paths with their pretty titles
                    if field in current_entity:
                        current_entity[mongo_projection[field]] = current_entity[field]
                        del current_entity[field]
                        if isinstance(current_entity[mongo_projection[field]], list):
                            canonized_values = [str(val) for val in current_entity[mongo_projection[field]]]
                            current_entity[mongo_projection[field]] = ','.join(canonized_values)
            dw = csv.DictWriter(string_output, mongo_projection.values())
            dw.writeheader()
            dw.writerows(entities)
            output = make_response(string_output.getvalue().encode('utf-8'))
            timestamp = datetime.now().strftime("%d%m%Y-%H%M%S")
            output.headers['Content-Disposition'] = f'attachment; filename=axonius-data_{timestamp}.csv'
            output.headers['Content-type'] = 'text/csv'
        return output

    def _entity_by_id(self, entity_type: EntityType, entity_id, advanced_fields=[]):
        """
        Retrieve or delete device by the given id, from current devices DB or update it
        Currently, update works only for tags because that is the only edit operation user has
        :return:
        """

        def _basic_generic_field_names():
            generic_field_names = list(map(lambda field: field.get(
                'name'), self._entity_fields(entity_type)['generic']))
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

    def _get_entities_count(self, filter, entity_type: EntityType):
        """
        Count total number of devices answering given mongo_filter

        :param filter: Object defining a Mongo query
        :return: Number of devices
        """
        data_collection = self._entity_views_db_map[entity_type]
        return str(data_collection.count(filter))

    def _flatten_fields(self, schema, name='', exclude=[]):
        def _merge_title(schema, title):
            """
            If exists, add given title before that of given schema or set it if none existing
            :param schema:
            :param title:
            :return:
            """
            new_schema = {**schema}
            if title:
                new_schema['title'] = f'{title}: {new_schema["title"]}' if new_schema.get('title') else title
            return new_schema

        if (schema.get('name')):
            if schema['name'] in exclude:
                return []
            name = f'{name}.{schema["name"]}' if name else schema['name']

        if schema['type'] == 'array' and schema.get('items'):
            if type(schema['items']) == list:
                children = []
                for item in schema['items']:
                    if not item.get('title'):
                        continue
                    children = children + self._flatten_fields(_merge_title(item, schema.get('title')), name)
                return children

            if schema['items']['type'] != 'array':
                if not schema.get('title'):
                    return []
                return [{**schema, 'name': name}]
            return self._flatten_fields(_merge_title(schema['items'], schema.get('title')), name, exclude)

        if not schema.get('title'):
            return []
        return [{**schema, 'name': name}]

    def _entity_fields(self, entity_type: EntityType):
        """
        Get generic fields schema as well as adapter-specific parsed fields schema.
        Together these are all fields that any device may have data for and should be presented in UI accordingly.

        :return:
        """

        def _get_generic_fields():
            if entity_type == EntityType.Devices:
                return DeviceAdapter.get_fields_info()
            elif entity_type == EntityType.Users:
                return UserAdapter.get_fields_info()
            return dict()

        all_supported_properties = [x.name for x in AdapterProperty.__members__.values()]

        generic_fields = _get_generic_fields()
        fields = {
            'schema': {'generic': generic_fields, 'specific': {}},
            'generic': [{
                'name': 'adapters', 'title': 'Adapters', 'type': 'array', 'items': {
                    'type': 'string', 'format': 'logo', 'enum': []
                }}, {
                'name': 'specific_data.adapter_properties', 'title': 'Adapter Properties', 'type': 'string',
                'enum': all_supported_properties
            }] + self._flatten_fields(generic_fields, 'specific_data.data', ['scanner']) + [{
                'name': 'labels', 'title': 'Tags', 'type': 'array', 'items': {'type': 'string', 'format': 'tag'}
            }],
            'specific': {}
        }
        plugins_available = requests.get(self.core_address + '/register').json()
        exclude_specific_schema = [item['name'] for item in generic_fields.get('items', [])]
        with self._get_db_connection() as db_connection:
            plugins_from_db = list(db_connection['core']['configs'].find({}).
                                   sort([(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)]))
            for plugin in plugins_from_db:
                if not plugin[PLUGIN_UNIQUE_NAME] in plugins_available:
                    continue
                plugin_fields = db_connection[plugin[PLUGIN_UNIQUE_NAME]][f'{entity_type.value}_fields']
                if not plugin_fields:
                    continue
                plugin_fields_record = plugin_fields.find_one({'name': 'parsed'}, projection={'schema': 1})
                if not plugin_fields_record:
                    continue
                fields['schema']['specific'][plugin[PLUGIN_NAME]] = {
                    'type': plugin_fields_record['schema']['type'],
                    'required': plugin_fields_record['schema'].get('required', []),
                    'items': filter(lambda x: x['name'] not in exclude_specific_schema,
                                    plugin_fields_record['schema'].get('items', []))
                }
                fields['specific'][plugin[PLUGIN_NAME]] = self._flatten_fields(
                    plugin_fields_record['schema'], f'adapters_data.{plugin[PLUGIN_NAME]}', ['scanner'])

        return fields

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
        entity_views_collection = self.gui.entity_query_views_db_map[entity_type]
        if method == 'GET':
            mongo_filter = filter_archived(mongo_filter)
            fielded_plugins = []
            for plugin in requests.get(self.core_address + '/register').json().values():
                # From registered plugins, saving those that have a 'fields' DB for given entity_type
                if self._get_collection(f'{entity_type.value}_fields', plugin[PLUGIN_UNIQUE_NAME]).count():
                    fielded_plugins.append(plugin[PLUGIN_NAME])

            def _validate_adapters_used(view):
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
            return jsonify(gui_helpers.beautify_db_entry(entry) for entry in filter(_validate_adapters_used, all_views))

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
        self._entity_db_map[entity_type].update_many({'internal_axon_id': {
            "$in": list(internal_axon_ids)
        }},
            {
                "$set": {
                    "adapters.$[].pending_delete": True
                }
        })
        return '', 200

    ##########
    # DEVICE #
    ##########

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_helpers.add_rule_unauthenticated("devices", methods=['GET', 'DELETE'])
    def get_devices(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        if request.method == 'DELETE':
            to_delete = self.get_request_data_as_object().get('internal_axon_ids', [])
            return self.__delete_entities_by_internal_axon_id(EntityType.Devices, to_delete)
        return jsonify(
            gui_helpers.get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection,
                                     self.gui.entity_query_views_db_map[EntityType.Devices],
                                     self._entity_views_db_map[EntityType.Devices], EntityType.Devices, True,
                                     default_sort=self._system_settings['defaultSort']))

    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_helpers.add_rule_unauthenticated("devices/csv")
    def get_devices_csv(self, mongo_filter, mongo_sort, mongo_projection):
        return self._get_csv(mongo_filter, mongo_sort, mongo_projection, EntityType.Devices)

    @gui_helpers.add_rule_unauthenticated("devices/<device_id>", methods=['GET'])
    def device_by_id(self, device_id):
        return self._entity_by_id(EntityType.Devices, device_id, ['installed_software', 'software_cves',
                                                                  'security_patches', 'available_security_patches',
                                                                  'users', 'connected_hardware', 'local_admins'])

    @gui_helpers.filtered()
    @gui_helpers.add_rule_unauthenticated("devices/count")
    def get_devices_count(self, mongo_filter):
        return self._get_entities_count(mongo_filter, EntityType.Devices)

    @gui_helpers.add_rule_unauthenticated("devices/fields")
    def device_fields(self):
        return jsonify(self._entity_fields(EntityType.Devices))

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.add_rule_unauthenticated("devices/views", methods=['GET', 'POST', 'DELETE'])
    def device_views(self, limit, skip, mongo_filter):
        """
        Save or fetch views over the devices db
        :return:
        """
        return self._entity_views(request.method, EntityType.Devices, limit, skip, mongo_filter)

    @gui_helpers.add_rule_unauthenticated("devices/labels", methods=['GET', 'POST', 'DELETE'])
    def device_labels(self):
        return self._entity_labels(self.devices_db_view, self.devices)

    @gui_helpers.add_rule_unauthenticated("devices/disable", methods=['POST'])
    def disable_device(self):
        return self._disable_entity(EntityType.Devices)

    #########
    # USER #
    #########

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_helpers.add_rule_unauthenticated("users", methods=['GET', 'DELETE'])
    def get_users(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        if request.method == 'DELETE':
            to_delete = self.get_request_data_as_object().get('internal_axon_ids', [])
            return self.__delete_entities_by_internal_axon_id(EntityType.Users, to_delete)
        return jsonify(
            gui_helpers.get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection,
                                     self.gui.entity_query_views_db_map[EntityType.Users],
                                     self._entity_views_db_map[EntityType.Users], EntityType.Users, True,
                                     default_sort=self._system_settings['defaultSort']))

    @gui_helpers.filtered()
    @gui_helpers.sorted_endpoint()
    @gui_helpers.projected()
    @gui_helpers.add_rule_unauthenticated("users/csv")
    def get_users_csv(self, mongo_filter, mongo_sort, mongo_projection):
        return self._get_csv(mongo_filter, mongo_sort, mongo_projection, EntityType.Users)

    @gui_helpers.add_rule_unauthenticated("users/<user_id>", methods=['GET'])
    def user_by_id(self, user_id):
        return self._entity_by_id(EntityType.Users, user_id, ['associated_devices'])

    @gui_helpers.filtered()
    @gui_helpers.add_rule_unauthenticated("users/count")
    def get_users_count(self, mongo_filter):
        return self._get_entities_count(mongo_filter, EntityType.Users)

    @gui_helpers.add_rule_unauthenticated("users/fields")
    def user_fields(self):
        return jsonify(self._entity_fields(EntityType.Users))

    @gui_helpers.add_rule_unauthenticated("users/disable", methods=['POST'])
    def disable_user(self):
        return self._disable_entity(EntityType.Users)

    @gui_helpers.paginated()
    @gui_helpers.filtered()
    @gui_helpers.add_rule_unauthenticated("users/views", methods=['GET', 'POST', 'DELETE'])
    def user_views(self, limit, skip, mongo_filter):
        return self._entity_views(request.method, EntityType.Users, limit, skip, mongo_filter)

    @gui_helpers.add_rule_unauthenticated("users/labels", methods=['GET', 'POST', 'DELETE'])
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

    @gui_helpers.filtered()
    @gui_helpers.add_rule_unauthenticated("adapters")
    def adapters(self, mongo_filter):
        """
        Get all adapters from the core
        :mongo_filter
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
                schema = self._get_plugin_schemas(db_connection, adapter_name)['clients']
                clients = [gui_helpers.beautify_db_entry(client) for client in clients_collection.find()
                           .sort([('_id', pymongo.DESCENDING)])]
                for client in clients:
                    client['client_config'] = clear_passwords_fields(client['client_config'], schema)
                status = ''
                if len(clients):
                    clients_connected = clients_collection.find({'status': 'success'}, projection={'_id': 1}).count()
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

    @gui_helpers.add_rule_unauthenticated("adapters/<adapter_unique_name>/upload_file", methods=['POST'])
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

    @gui_helpers.add_rule_unauthenticated("adapters/<adapter_unique_name>/clients", methods=['PUT'])
    def adapters_clients(self, adapter_unique_name):
        """
        Gets or creates clients in the adapter
        :param adapter_unique_name: the adapter to refer to
        :return:
        """
        with self._get_db_connection() as db_connection:
            return self._query_client_for_devices(adapter_unique_name)

    @gui_helpers.add_rule_unauthenticated("adapters/<adapter_unique_name>/clients/<client_id>", methods=['PUT', 'DELETE'])
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
                logger.error(
                    f"Execute of {action_type} returned {response.status_code}. Reason: {str(response.content)}")
                raise ValueError(
                    f"Execute of {action_type} returned {response.status_code}. Reason: {str(response.content)}")
            return '', 200
        except Exception as e:
            return return_error(f'Attempt to run action {action_type} caused exception. Reason: {repr(e)}', 400)

    @gui_helpers.add_rule_unauthenticated("actions/<action_type>", methods=['POST'])
    def actions_run(self, action_type):
        action_data = self.get_request_data_as_object()
        action_data['action_type'] = action_type
        return self.run_actions(action_data)

    @gui_helpers.add_rule_unauthenticated("actions/upload_file", methods=['POST'])
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
        views_collection = self.gui.entity_query_views_db_map[entity]
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
    @gui_helpers.add_rule_unauthenticated("alert", methods=['GET', 'PUT', 'DELETE'])
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
    @gui_helpers.add_rule_unauthenticated("alert/count")
    def alert_count(self, mongo_filter):
        with self._get_db_connection() as db_connection:
            report_service = self.get_plugin_by_name('reports')[PLUGIN_UNIQUE_NAME]
            return jsonify(db_connection[report_service]['reports'].find(mongo_filter).count())

    @gui_helpers.add_rule_unauthenticated("alert/<alert_id>", methods=['POST'])
    def alerts_update(self, alert_id):
        """

        :param alert_id:
        :return:
        """
        alert_to_update = request.get_json(silent=True)
        view_name = alert_to_update['view']
        view_entity = alert_to_update['viewEntity']
        assert view_entity in [x.value for x in EntityType.__members__.values()]
        views = self.gui.entity_query_views_db_map[EntityType(view_entity)]
        if views.find_one({'name': view_name}) is None:
            return return_error(f"Missing view {view_name} requested for updating alert")

        response = self.request_remote_plugin(f"reports/{alert_id}", "reports", method='post',
                                              json=alert_to_update)
        if response is None:
            return return_error("No response whether alert was updated")

        return response.text, response.status_code

    @gui_helpers.filtered()
    @gui_helpers.add_rule_unauthenticated("plugins")
    def plugins(self, mongo_filter):
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

    @gui_helpers.add_rule_unauthenticated("plugins/configs/<plugin_unique_name>/<config_name>", methods=['POST', 'GET'])
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

            return ""
        if request.method == 'GET':
            with self._get_db_connection() as db_connection:
                config_collection = db_connection[plugin_unique_name][CONFIGURABLE_CONFIGS]
                schema_collection = db_connection[plugin_unique_name]['config_schemas']
                return jsonify({'config': config_collection.find_one({'config_name': config_name})['config'],
                                'schema': schema_collection.find_one({'config_name': config_name})['schema']})

    @gui_helpers.add_rule_unauthenticated("plugins/<plugin_unique_name>/<command>", methods=['POST'])
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

    @gui_helpers.add_rule_unauthenticated("config/<config_name>", methods=['POST', 'GET'])
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
    @gui_helpers.add_rule_unauthenticated("notifications", methods=['POST', 'GET'])
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
    @gui_helpers.add_rule_unauthenticated("notifications/count", methods=['GET'])
    def notifications_count(self, mongo_filter):
        """
        Fetches from core's notification collection, according to given mongo_filter,
        and counts how many entries in retrieved cursor
        :param mongo_filter: Generated by the filtered() decorator, according to uri param "filter"
        :return: Number of notifications matching given filter
        """
        with self._get_db_connection() as db:
            notification_collection = db['core']['notifications']
            return str(notification_collection.find(mongo_filter).count())

    @gui_helpers.add_rule_unauthenticated("notifications/<notification_id>", methods=['GET'])
    def notifications_by_id(self, notification_id):
        """
        Get all notification data
        :param notification_id: Notification ID
        :return:
        """
        with self._get_db_connection() as db:
            notification_collection = db['core']['notifications']
            return jsonify(gui_helpers.beautify_db_entry(notification_collection.find_one({'_id': ObjectId(notification_id)})))

    @add_rule("get_login_options", should_authenticate=False)
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

    @add_rule("login", methods=['GET', 'POST'], should_authenticate=False)
    def login(self):
        """
        Get current user or login
        :return:
        """
        if request.method == 'GET':
            user = session.get('user')
            if user is None:
                return return_error('', 401)
            if 'password' in user:
                user = {k: v for k, v in user.items() if k != 'password'}
            return jsonify(user), 200

        users_collection = self._get_collection('users')
        log_in_data = self.get_request_data_as_object()
        if log_in_data is None:
            return return_error("No login data provided", 400)
        user_name = log_in_data.get('user_name')
        password = log_in_data.get('password')
        remember_me = log_in_data.get('remember_me', False)
        if not isinstance(remember_me, bool):
            return return_error("remember_me isn't boolean", 401)
        user_from_db = users_collection.find_one({'user_name': user_name})
        if user_from_db is None:
            logger.info(f"Unknown user {user_name} tried logging in")
            return return_error("Wrong user name or password", 401)
        if not bcrypt.verify(password, user_from_db['password']):
            logger.info(f"User {user_name} tried logging in with wrong password")
            return return_error("Wrong user name or password", 401)
        if request and request.referrer and 'localhost' not in request.referrer and '127.0.0.1' not in request.referrer:
            self.system_collection.replace_one({'type': 'server'},
                                               {'type': 'server', 'server_name': parse_url(request.referrer).host},
                                               upsert=True)
        session['user'] = user_from_db
        session.permanent = remember_me
        return ""

    @add_rule("okta-redirect", methods=['GET'], should_authenticate=False)
    def okta_redirect(self):
        try_connecting_using_okta(self.__okta)
        return redirect("/", code=302)

    @add_rule("ldap-login", methods=['POST'], should_authenticate=False)
    def ldap_login(self):
        try:
            log_in_data = self.get_request_data_as_object()
            if log_in_data is None:
                return return_error("No login data provided", 400)
            user_name = log_in_data.get('user_name')
            password = log_in_data.get('password')
            domain = log_in_data.get('domain')
            ldap_login = self.__ldap_login

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

            session['user'] = {'user_name': user.get('displayName') or user_name,
                               'first_name': user.get('givenName') or '',
                               'last_name': user.get('sn') or '',
                               'pic_name': image or self.DEFAULT_AVATAR_PIC,
                               }
            return ""
        except ldap3.core.exceptions.LDAPException:
            return return_error("LDAP verification has failed, please try again")
        except Exception:
            logger.exception("LDAP Verification error")
            return return_error("An error has occurred while verifying your account")

    @add_rule("google-login", methods=['POST'], should_authenticate=False)
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
            session['user'] = {
                'user_name': idinfo.get('name') or 'unamed',
                'first_name': idinfo.get('given_name') or 'unamed',
                'last_name': idinfo.get('family_name') or 'unamed',
                'pic_name': idinfo.get('picture') or self.DEFAULT_AVATAR_PIC,
            }
            return ""
        except ValueError:
            logger.exception("Invalid token")
            return return_error("Invalid token")
        except Exception:
            logger.exception("Unknown exception")
            return return_error("Error logging in, please try again")

    @gui_helpers.add_rule_unauthenticated("logout", methods=['GET'])
    def logout(self):
        """
        Clears session, logs out
        :return:
        """
        session['user'] = None
        return ""

    @gui_helpers.paginated()
    @gui_helpers.add_rule_unauthenticated("authusers", methods=['GET', 'POST'])
    def authusers(self, limit, skip):
        """
        View or add users
        :param limit: limit for pagination
        :param skip: start index for pagination
        :return:
        """
        users_collection = self._get_collection('users')
        if request.method == 'GET':
            return jsonify(gui_helpers.beautify_db_entry(n) for n in
                           users_collection.find(projection={
                               "_id": 1,
                               "user_name": 1,
                               "first_name": 1,
                               "last_name": 1,
                               "pic_name": 1}).sort(
                               [('_id', pymongo.ASCENDING)]).skip(skip).limit(limit))
        elif request.method == 'POST':
            post_data = self.get_request_data_as_object()
            user = session.get('user')
            if user['user_name'] != post_data['user_name']:
                return return_error("Login to your user first")
            if not bcrypt.verify(post_data['old_password'], user['password']):
                return return_error("Given password is wrong")
            users_collection.update({'user_name': user['user_name']},
                                    {
                                        "$set": {
                                            'password': bcrypt.hash(post_data['new_password'])
                                        }
            })
            user_from_db = users_collection.find_one({'user_name': user['user_name']})
            session['user'] = user_from_db
            return "", 200

    @gui_helpers.paginated()
    @gui_helpers.add_rule_unauthenticated("logs")
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

    @gzipped_downloadable("axonius_logs_{}", "json")
    @add_rule("logs/export", should_authenticate=False)
    def logs_export(self):
        """
        Pass 'start_date' and/or 'end_date' in GET parameters
        :return:
        """
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        es = Elasticsearch(hosts=[self._elk_addr], http_auth=self._elk_auth)
        res = es.search(index='logstash-*', doc_type='logstash-log',
                        body={
                            "query": {
                                "range": {  # expect this to return the one result on 2012-12-20
                                    "@timestamp": {
                                        "gte": start_date,
                                        "lte": end_date,
                                    }
                                }
                            }
                        })
        return json.dumps(list(res['hits']['hits']))

    #############
    # DASHBOARD #
    #############

    def __get_saved_view_result_from_views(self, views, from_given_date, to_given_date):
        """
        Finds the latest saved result from the given view list (from card) that are in the given date range
        """
        module_name = None
        for view in views:
            view_name = view.get('name')
            # pie charts don't save the `module` for all views, so we can just 'use' the last one
            module_name = view.get('module') or module_name
            if not module_name or not view_name:
                continue
            try:
                saved_result = self.gui.entity_views_results_db_map[EntityType(module_name)].find_one(
                    {
                        'view': view_name,
                        'accurate_for_datetime': {
                            '$lt': to_given_date,
                            '$gt': from_given_date,
                        }
                    },
                    sort=[
                        ['accurate_for_datetime', -1]
                    ]
                )
                if not saved_result:
                    continue
                yield {
                    'name': view_name,
                    'count': saved_result['count'],
                    'accurate_for_datetime': saved_result['accurate_for_datetime']
                }
            except Exception:
                logger.exception(f"When dealing with {view_name} and {module_name}")

    @gui_helpers.add_rule_unauthenticated("saved_card_results/<card_name>", methods=['GET'])
    def saved_card_results(self, card_name: str):
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
        card = self._get_collection('dashboard').find_one({'name': card_name})
        if not card:
            return return_error("Card doesn't exist")
        return jsonify({x['name']: x for x in self.__get_saved_view_result_from_views(card['views'],
                                                                                      from_given_date, to_given_date)})

    @gui_helpers.add_rule_unauthenticated("dashboard", methods=['POST', 'GET'])
    def get_dashboard(self):
        if request.method == 'GET':
            return jsonify(self._get_dashboard())

        # Handle 'POST' request method - save dashboard configuration
        dashboard_data = self.get_request_data_as_object()
        if not dashboard_data.get('name'):
            return return_error('Name required in order to save Dashboard Chart', 400)
        if not dashboard_data.get('views'):
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
            elif not dashboard.get('views'):
                logger.info(f'No views found for dashboard {dashboard.get("name")}')
            else:
                # Let's fetch and execute them query filters, depending on the chart's type
                try:
                    if dashboard['type'] == ChartTypes.compare.name:
                        dashboard['data'] = self._fetch_data_for_chart_compare(dashboard['views'])
                    elif dashboard['type'] == ChartTypes.intersect.name:
                        dashboard['data'] = self._fetch_data_for_chart_intersect(dashboard['views'])
                    yield gui_helpers.beautify_db_entry(dashboard)
                except Exception as e:
                    # Since there is no data, not adding this chart to the list
                    logger.exception(
                        f'Error fetching data for chart {dashboard["name"]} ({dashboard["_id"]}). Reason: {e}')

    def _fetch_data_for_chart_compare(self, dashboard_views):
        """
        Iterate given views, fetch each one's filter from the appropriate query collection, according to its module,
        and execute the filter on the appropriate entity collection.

        :param dashboard_views:
        :return:
        """
        if not dashboard_views:
            raise Exception('No views for the chart')
        data = []
        for view in dashboard_views:
            # Can be optimized by taking all names in advance and querying each module's collection once
            # But since list is very short the simpler and more readable implementation is fine
            module = view.get('module', EntityType.Devices.value)
            entity = EntityType(module)
            view_object = self.gui.entity_query_views_db_map[entity].find_one({'name': view['name']})
            if not view_object:
                raise Exception(f'No filter found for query {view["name"]}')
            data.append({'name': view_object['name'], 'filter': view_object['view']['query']['filter'],
                         'module': module,
                         'count': self._entity_views_db_map[entity].find(
                             parse_filter(view_object['view']['query']['filter']),
                             {'_id': 1}).count()})
        return data

    def _fetch_data_for_chart_intersect(self, dashboard_views):
        """
        This chart shows intersection of 1 or 2 'Child' views with a 'Parent' (expected not to be a subset of them).
        Module to be queried is defined by the parent query.

        :param dashboard_views: List of 2 or 3 views
        :return: List of result portions for the query executions along with their names. First represents Parent query.
                 If 1 child, second represents Child intersecting with Parent.
                 If 2 children, intersection between all three is calculated, namely 'Intersection'.
                                Second and third represent each Child intersecting with Parent, excluding Intersection.
                                Fourth represents Intersection.
        """
        if not dashboard_views or len(dashboard_views) < 2:
            raise Exception('Pie chart requires at least two views')
        entity = EntityType(dashboard_views[0]['module']) if dashboard_views[0].get(
            'module') else EntityType.Devices
        # Query and data collections according to given parent's module
        views_collection = self.gui.entity_query_views_db_map[entity]
        data_collection = self._entity_views_db_map[entity]

        parent_name = dashboard_views[0]['name']
        parent_filter = {}
        if parent_name:
            parent_filter = parse_filter(views_collection.find_one({'name': parent_name})['view']['query']['filter'])
        data = [{'name': parent_name, 'count': data_collection.find(parent_filter, {'_id': 1}).count()}]

        child_name_1 = dashboard_views[1]['name']
        child_filter_1 = parse_filter(views_collection.find_one({'name': child_name_1})['view']['query']['filter'])
        if len(dashboard_views) == 2:
            # Fetch the only child, intersecting with parent
            data.append({'name': child_name_1,
                         'count': data_collection.find({'$and': [parent_filter, child_filter_1]}, {'_id': 1}).count()})
        else:
            child_name_2 = dashboard_views[2]['name']
            child_filter_2 = parse_filter(views_collection.find_one({'name': child_name_2})['view']['query']['filter'])

            # Fetch the intersection of parent and 2 children and create match to exclude their _IDs
            intersection_cursor = data_collection.find({'$and': [parent_filter, child_filter_1, child_filter_2]},
                                                       {'_id': 1})
            not_intersection = {'_id': {'$not': {'$in': [ObjectId(entry['_id']) for entry in intersection_cursor]}}}
            # Child1 + Parent - Intersection
            data.append({'name': child_name_1,
                         'count': data_collection.find({'$and': [parent_filter, child_filter_1, not_intersection]},
                                                       {'_id': 1}).count()})
            # Intersection
            data.append({'name': [child_name_1, child_name_2], 'count': intersection_cursor.count()})
            # Child2 + Parent - Intersection
            data.append({'name': child_name_2,
                         'count': data_collection.find({'$and': [parent_filter, child_filter_2, not_intersection]},
                                                       {'_id': 1}).count()})
        return data

    @gui_helpers.add_rule_unauthenticated("dashboard/<dashboard_id>", methods=['DELETE'])
    def remove_dashboard(self, dashboard_id):
        """
        Fetches data, according to definition saved for the dashboard named by given name

        :param dashboard_name: Name of the dashboard to fetch data for
        :return:
        """
        update_result = self._get_collection('dashboard').replace_one(
            {'_id': ObjectId(dashboard_id)}, {'archived': True})
        if not update_result.modified_count:
            return return_error(f'No dashboard by the id {dashboard_id} found or updated', 400)
        return ''

    @gui_helpers.add_rule_unauthenticated("dashboard/lifecycle", methods=['GET'])
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

        state = state_response.json()
        is_research = state[StateLevels.Phase.name] == Phases.Research.name

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

        return jsonify({'sub_phases': sub_phases, 'next_run_time': run_time_response.text})

    @gui_helpers.add_rule_unauthenticated("dashboard/lifecycle_rate", methods=['GET', 'POST'])
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

    def _adapter_devices(self):
        """
        For each adapter currently registered in system, count how many devices it fetched.

        :return: Map between each adapter and the number of devices it has, unless no devices
        """
        logger.info("Getting adapter devices")
        plugins_available = requests.get(self.core_address + '/register').json()
        adapter_devices = {'total_gross': 0, 'adapter_count': []}
        with self._get_db_connection() as db_connection:
            adapter_devices['total_net'] = self.devices_db.count()
            adapters_from_db = db_connection['core']['configs'].find({'plugin_type': 'Adapter'})
            for adapter in adapters_from_db:
                if not adapter[PLUGIN_UNIQUE_NAME] in plugins_available:
                    # Plugin not registered - unwanted in UI
                    continue
                devices_count = self.devices_db_view.count({'specific_data.plugin_name': adapter['plugin_name']})
                if not devices_count:
                    # No need to document since adapter has no devices
                    continue
                adapter_devices['adapter_count'].append({'name': adapter['plugin_name'], 'count': devices_count})
                adapter_devices['total_gross'] = adapter_devices['total_gross'] + devices_count
        return adapter_devices

    @gui_helpers.add_rule_unauthenticated("dashboard/adapter_devices", methods=['GET'])
    def get_adapter_devices(self):
        return jsonify(self._adapter_devices())

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
        devices_total = self.devices_db_view.count()
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
            devices_property = self.devices_db_view.count({
                'specific_data.adapter_properties':
                    {'$in': item['properties']}
            })
            # Update the count, in case we are in the middle of lifecycle and devices are being added
            # Otherwise, count of devices for properties may be larger than total devices
            devices_total = self.devices_db_view.count()
            item['portion'] = devices_property / devices_total
        return coverage_list

    @gui_helpers.add_rule_unauthenticated("dashboard/coverage", methods=['GET'])
    def get_dashboard_coverage(self):
        return jsonify(self._get_dashboard_coverage())

    @gui_helpers.add_rule_unauthenticated("get_latest_report_date", methods=['GET'])
    def get_latest_report_date(self):
        recent_report = self._get_collection("reports").find_one({'filename': 'most_recent_report'})
        if recent_report is not None:
            return jsonify(recent_report['time'])
        return ''

    @gui_helpers.add_rule_unauthenticated("research_phase", methods=['POST'])
    def schedule_research_phase(self):
        """
        Schedules or initiates research phase.

        :return: Map between each adapter and the number of devices it has, unless no devices
        """

        data = self.get_request_data_as_object()
        logger.info(f"Scheduling Research Phase to: {data if data else 'Now'}")
        response = self.request_remote_plugin(
            'trigger/execute', SYSTEM_SCHEDULER_PLUGIN_NAME, 'POST', json=data)

        if response.status_code != 200:
            logger.error(f"Could not schedule research phase to: {data if data else 'Now'}")
            return return_error(f"Could not schedule research phase to: {data if data else 'Now'}",
                                response.status_code)

        return ''

    @gui_helpers.add_rule_unauthenticated("stop_research_phase", methods=['POST'])
    def stop_research_phase(self):
        """
        Stops currently running research phase.
        """
        logger.info("stopping research phase")
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
                view = self.gui.entity_query_views_db_map[entity].find_one({'name': query['name']})
                if view:
                    view_filter = view['view']['query']['filter']
                    logger.info(f'Executing filter {view_filter} on entity {entity.name}')
                    views.append({
                        **query,
                        'count': self._entity_views_db_map[entity].find(parse_filter(view_filter), {'_id': 1}).count()
                    })
            adapter_clients_report = {}
            try:
                # Exception thrown if adapter is down or report missing, and section will appear with views only
                adapter_unique_name = self.get_plugin_unique_name(adapter['name'])
                adapter_reports_db = self._get_db_connection()[adapter_unique_name]
                adapter_clients_report = adapter_reports_db['report'].find_one({"name": "report"}).get('data', {})
            except Exception:
                logger.exception("Error contacting the report db for adapter {adapter_unique_name}")

            adapter_data.append({'name': adapter['title'], 'queries': views, 'views': adapter_clients_report})
        return adapter_data

    def _get_saved_views_data(self):
        """
        For each entity in system, fetch all saved views.
        For each view, fetch first page of entities - filtered, projected, sorted_endpoint according to it's definition.

        :return: Lists of the view names along with the list of results and list of field headers, with pretty names.
        """

        def _get_field_titles(entity):
            entity_fields = self._entity_fields(entity)
            name_to_title = {}
            for field in entity_fields['generic']:
                name_to_title[field['name']] = field['title']
            for type in entity_fields['specific']:
                for field in entity_fields['specific'][type]:
                    name_to_title[field['name']] = field['title']
            return name_to_title

        logger.info("Getting views data")
        views_data = []
        for entity in EntityType:
            field_to_title = _get_field_titles(entity)
            saved_views = self.gui.entity_query_views_db_map[entity].find(filter_archived({'query_type': 'saved'}))
            for i, view_doc in enumerate(saved_views):
                try:
                    view = view_doc.get('view')
                    if view:
                        field_list = view.get('fields', [])
                        logger.info(field_list)
                        views_data.append({
                            'name': view_doc.get('name', f'View {i}'), 'entity': entity.value,
                            'fields': [{field_to_title.get(field, field): field} for field in field_list],
                            'data': gui_helpers.get_entities(view.get('pageSize', 20), 0,
                                                             parse_filter(view.get('query', {}).get('filter', '')),
                                                             gui_helpers.get_sort(
                                                                 view), {field: 1 for field in field_list},
                                                             self.gui.entity_query_views_db_map[entity],
                                                             self._entity_views_db_map[entity], entity,
                                                             default_sort=self._system_settings['defaultSort'])
                        })
                except Exception:
                    logger.exception(f"Problem with View {str(i)} ViewDoc {str(view_doc)}")
        return views_data

    @stoppable
    def _on_trigger(self):
        self._run_queries_phase()
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

    @gui_helpers.add_rule_unauthenticated('export_report')
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
            'adapter_devices': self._adapter_devices(),
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

    def _run_queries_phase(self):
        """
        Run all saved queries (i.e. views) and save the result count in the DB
        """
        for entity_type in EntityType:
            views = self.gui.entity_query_views_db_map[entity_type].find({'query_type': 'saved'})
            for view in views:
                try:
                    parsed_view_filter = parse_filter(view['view']['query']['filter'])
                    count = self._entity_views_db_map[entity_type].count(parsed_view_filter)
                    self.gui.entity_views_results_db_map[entity_type].insert_one({
                        "view": view['name'],
                        "count": count,
                        "accurate_for_datetime": datetime.now(tz=timezone.utc)
                    })
                except Exception:
                    logger.exception(f"Exception on running view {view}")

    @gui_helpers.add_rule_unauthenticated('test_exec_report', methods=['POST'])
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

        exec_report_job = self._exec_report_scheduler.get_job(EXEC_REPORT_THREAD_ID)

        # If job dosen't exist generate it
        if exec_report_job is None:
            self._exec_report_scheduler.add_job(func=self._send_report_thread,
                                                trigger=new_interval_triggger,
                                                next_run_time=next_run_time,
                                                name=EXEC_REPORT_THREAD_ID,
                                                id=EXEC_REPORT_THREAD_ID,
                                                max_instances=1)
        else:
            exec_report_job.modify(next_run_time=next_run_time)
            self._exec_report_scheduler.reschedule_job(EXEC_REPORT_THREAD_ID, trigger=new_interval_triggger)

        exec_reports_settings_collection.replace_one({}, exec_report_data, upsert=True)
        logger.info(f"Scheduling an exec_report sending for {next_run_time} and period of {time_period}.")
        return "Scheduled next run."

    @gui_helpers.add_rule_unauthenticated('exec_report', methods=['POST', 'GET'])
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

    @gui_helpers.add_rule_unauthenticated('metadata', methods=['GET'])
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

    @gui_helpers.add_rule_unauthenticated('analytics', methods=['GET'], auth_method=None)
    def get_analytics(self):
        return jsonify(self._maintenance_settings[ANALYTICS_SETTING])

    @gui_helpers.add_rule_unauthenticated('troubleshooting', methods=['GET'], auth_method=None)
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
                            "title": "Percentage Fields Severity Ranges",
                            "type": "array",
                            "items": [
                                {
                                    "name": "error",
                                    "title": "Poor:",
                                    "type": "range"
                                },
                                {
                                    "name": "warning",
                                    "title": "Average:",
                                    "type": "range"
                                },
                                {
                                    "name": "success",
                                    "title": "Good:",
                                    "type": "range"
                                }
                            ],
                            "required": ["poor", "average", "good"]
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
            "pretty_name": "GUI Configuration",
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
                    "error": {"lte": 40, "gte": 0},
                    "warning": {"lte": 60, "gte": 41},
                    "success": {"lte": 100, "gte": 61},
                },
                "tableView": True
            }
        }
