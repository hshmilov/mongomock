import csv
import logging

from axonius.consts.plugin_consts import ADAPTERS_LIST_LENGTH

logger = logging.getLogger(f"axonius.{__name__}")
from axonius.adapter_base import AdapterProperty

from axonius.utils.files import get_local_config_file
from axonius.plugin_base import PluginBase, add_rule, return_error, EntityType
from axonius.devices.device_adapter import DeviceAdapter
from axonius.users.user_adapter import UserAdapter
from axonius.consts import plugin_consts
from axonius.consts.scheduler_consts import ResearchPhases, StateLevels, Phases
from gui.consts import ChartTypes
from gui.report_generator import ReportGenerator

import tarfile
import io
import os
from datetime import date, datetime
from flask import jsonify, request, session, after_this_request, make_response, send_file
from passlib.hash import bcrypt
from elasticsearch import Elasticsearch
import requests
import configparser
import pymongo
from bson import ObjectId
import json
from axonius.utils.parsing import parse_filter
import re

# the maximal amount of data a pagination query will give
PAGINATION_LIMIT_MAX = 2000


def add_rule_unauthenticated(rule, require_connected=True, *args, **kwargs):
    """
    Syntactic sugar for add_rule(should_authenticate=False, ...)
    :param rule: rule name
    :param require_connected: whether or not to require that the user is connected
    :param args:
    :param kwargs:
    :return:
    """
    add_rule_res = add_rule(rule, should_authenticate=False, *args, **kwargs)
    if require_connected:
        return lambda func: requires_connected(add_rule_res(func))
    return add_rule_res


# Caution! These decorators must come BEFORE @add_rule


def requires_connected(func):
    """
    Decorator stating that the view requires the user to be connected
    """

    def wrapper(self, *args, **kwargs):
        user = session.get('user')
        if user is None:
            return return_error("You're not connected", 401)
        return func(self, *args, **kwargs)

    return wrapper


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


# Caution! These decorators must come BEFORE @add_rule
def paginated(limit_max=PAGINATION_LIMIT_MAX):
    """
    Decorator stating that the view supports "?limit=X&start=Y" for pagination
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            # it's fine to raise here - an exception will be nicely JSONly displayed by add_rule
            limit = request.args.get('limit', limit_max, int)
            if limit < 0:
                raise ValueError("Limit mustn't be negative")
            if limit > limit_max:
                limit = limit_max
            skip = int(request.args.get('skip', 0, int))
            if skip < 0:
                raise ValueError("start mustn't be negative")
            return func(self, limit=limit, skip=skip, *args, **kwargs)

        return actual_wrapper

    return wrap


# Caution! These decorators must come BEFORE @add_rule
def filtered():
    """
    Decorator stating that the view supports ?filter='adapters == "active_directory_adapter"'
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            filter_obj = dict()
            try:
                filter_expr = request.args.get('filter')
                if filter_expr:
                    logger.debug("Parsing filter: {0}".format(filter_expr))
                    filter_obj = parse_filter(filter_expr)
            except Exception as e:
                return return_error("Could not create mongo filter. Details: {0}".format(e), 400)
            return func(self, mongo_filter=filter_obj, *args, **kwargs)

        return actual_wrapper

    return wrap


def sorted():
    """
    Decorator stating that the view supports ?sort=<field name><'-'/'+'>
    The field name must match a field in the collection to sort by
    and the -/+ determines whether sort is descending or ascending
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            sort_obj = {}
            try:
                sort_param = request.args.get('sort')
                if sort_param:
                    logger.debug(f'Parsing sort: {sort_param}')
                    sort_field = sort_param[:-1]
                    sort_direction = sort_param[-1]
                    sort_obj[sort_field] = pymongo.DESCENDING if (sort_direction == '-') else pymongo.ASCENDING
            except Exception as e:
                return return_error("Could not create mongo sort. Details: {0}".format(e), 400)
            return func(self, mongo_sort=sort_obj, *args, **kwargs)

        return actual_wrapper

    return wrap


# Caution! These decorators must come BEFORE @add_rule
def projected():
    """
    Decorator stating that the view supports ?fields=["name","hostname",["os_type":"OS.type"]]
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            fields = request.args.get('fields')
            mongo_fields = None
            if fields:
                try:
                    mongo_fields = {}
                    for field in fields.split(","):
                        mongo_fields[field] = 1
                except json.JSONDecodeError:
                    pass
            return func(self, mongo_projection=mongo_fields, *args, **kwargs)

        return actual_wrapper

    return wrap


def beautify_db_entry(entry):
    """
    Renames the '_id' to 'date_fetched', and stores it as an id to 'uuid' in a dict from mongo
    :type entry: dict
    :param entry: dict from mongodb
    :return: dict
    """
    tmp = {**entry, **{'date_fetched': entry['_id']}}
    tmp['uuid'] = str(entry['_id'])
    del tmp['_id']
    return tmp


def filter_archived():
    return {'$or': [{'archived': {'$exists': False}}, {'archived': False}]}


class GuiService(PluginBase):
    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__), *args, **kwargs)
        self.wsgi_app.config['SESSION_TYPE'] = 'memcached'
        self.wsgi_app.config['SECRET_KEY'] = 'this is my secret key which I like very much, I have no idea what is this'
        self._elk_addr = self.config['gui_specific']['elk_addr']
        self._elk_auth = self.config['gui_specific']['elk_auth']
        self.db_user = self.config['gui_specific']['db_user']
        self.db_password = self.config['gui_specific']['db_password']
        self._get_collection('users', limited_user=False).update({'user_name': 'admin'},
                                                                 {'user_name': 'admin',
                                                                  'first_name': 'administrator',
                                                                  'last_name': '',
                                                                  'pic_name': 'avatar.png',
                                                                  'password': bcrypt.hash('cAll2SecureAll')},
                                                                 upsert=True)
        self.user_queries = self._get_collection("user_queries", limited_user=False)
        self.device_queries = self._get_collection("device_queries", limited_user=False)
        self._queries_db_map = {
            EntityType.Users: self.user_queries,
            EntityType.Devices: self.device_queries,
        }
        self.add_default_queries(EntityType.Devices, 'default_queries_devices.ini')
        self.add_default_queries(EntityType.Users, 'default_queries_users.ini')

        self.user_view = self._get_collection("user_views", limited_user=False)
        self.device_view = self._get_collection("device_views", limited_user=False)
        self._views_db_map = {
            EntityType.Users: self.user_view,
            EntityType.Devices: self.device_view,
        }
        self.add_default_views(EntityType.Devices, 'default_views_devices.ini')
        self.add_default_views(EntityType.Users, 'default_views_users.ini')

        self.add_default_reports('default_reports.ini')

        self.add_default_dashboard_charts('default_dashboard_charts.ini')

    def add_default_queries(self, entity_type: EntityType, default_queries_ini_path):
        """
        Adds default queries.
        :param entity_type: "device" or "user"
        :param default_queries_ini_path: the file path with the queries
        :return:
        """
        # Load default queries and save them to the DB
        try:
            config = configparser.ConfigParser()
            config.read(os.path.abspath(os.path.join(os.path.dirname(__file__), f'configs/{default_queries_ini_path}')))

            # Save default queries
            for name, query in config.items():
                if name == 'DEFAULT':
                    # ConfigParser always has a fake DEFAULT key, skip it
                    continue
                try:
                    self._insert_query(self._queries_db_map[entity_type], name, query['query'])
                except Exception:
                    logger.exception(f'Error adding default query {name}')
        except Exception:
            logger.exception(f'Error adding default queries')

    def add_default_views(self, entity_type: EntityType, default_views_ini_path):
        """
        Adds default views.
        :param entity_type: EntityType
        :param default_views_ini_path: the file path with the queries
        :return:
        """
        # Load default queries and save them to the DB
        try:
            config = configparser.ConfigParser()
            config.read(os.path.abspath(os.path.join(os.path.dirname(__file__), f'configs/{default_views_ini_path}')))

            # Save default views
            for name, view in config.items():
                if name == 'DEFAULT':
                    # ConfigParser always has a fake DEFAULT key, skip it
                    continue
                try:
                    self._insert_view(self._views_db_map[entity_type], name, json.loads(view['view']))
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
                    self._insert_report(name, report)
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
                    self._insert_dashboard_chart(name, data['type'], json.loads(data['queries']))
                except Exception as e:
                    logger.exception(f'Error adding default dashboard chart {name}. Reason: {repr(e)}')
        except Exception as e:
            logger.exception(f'Error adding default dashboard chart. Reason: {repr(e)}')

    def _insert_query(self, queries_collection, name, query_filter, query_expressions=[]):
        existed_query = queries_collection.find_one({'filter': query_filter, 'name': name})
        if existed_query is not None and not existed_query.get('archived'):
            logger.info(f'Query {name} already exists id: {existed_query["_id"]}')
            return existed_query['_id']
        result = queries_collection.update({'name': name}, {'$set': {'name': name, 'filter': query_filter,
                                                                     'expressions': query_expressions,
                                                                     'query_type': 'saved', 'timestamp': datetime.now(),
                                                                     'archived': False}}, upsert=True)
        logger.info(f'Added query {name} id: {result.get("inserted_id", "")}')
        return result.get('inserted_id', '')

    def _insert_view(self, views_collection, name, mongo_view):
        existed_view = views_collection.find_one({'name': name})
        if existed_view is not None and not existed_view.get('archived'):
            logger.info(f'view {name} already exists id: {existed_view["_id"]}')
            return existed_view['_id']

        result = views_collection.insert_one({'name': name, 'view': mongo_view})
        logger.info(f'Added view {name} id: {result.inserted_id}')
        return result.inserted_id

    def _insert_report(self, name, report):
        reports_collection = self._get_collection("reports", limited_user=False)
        existed_report = reports_collection.find_one({'name': name})
        if existed_report is not None and not existed_report.get('archived'):
            logger.info(f'Report {name} already exists under id: {existed_report["_id"]}')
            return

        result = reports_collection.insert_one({'name': name, 'adapters': json.loads(report['adapters'])})
        logger.info(f'Added report {name} id: {result.inserted_id}')

    def _insert_dashboard_chart(self, dashboard_name, dashboard_type, dashboard_queries):
        dashboard_collection = self._get_collection("dashboard", limited_user=False)
        existed_dashboard_chart = dashboard_collection.find_one({'name': dashboard_name})
        if existed_dashboard_chart is not None and not existed_dashboard_chart.get('archived'):
            logger.info(f'Report {dashboard_name} already exists under id: {existed_dashboard_chart["_id"]}')
            return

        result = dashboard_collection.insert_one({'name': dashboard_name,
                                                  'type': dashboard_type,
                                                  'queries': dashboard_queries})

        logger.info(f'Added report {dashboard_name} id: {result.inserted_id}')

    ########
    # DATA #
    ########

    def _get_entities(self, limit, skip, filter, sort, projection, entity_type: EntityType):
        """
        Get Axonius data of type <entity_type>, from the aggregator which is expected to store them.
        """
        logger.debug(f'Fetching data for entity {entity_type.name}')
        with self._get_db_connection(False) as db_connection:
            pipeline = [{'$match': filter}]
            if projection:
                projection['internal_axon_id'] = 1
                projection['adapters'] = 1
                projection['unique_adapter_names'] = 1
                projection['labels'] = 1
                projection[ADAPTERS_LIST_LENGTH] = 1
                pipeline.append({'$project': projection})
            if sort:
                pipeline.append({'$sort': sort})
            elif entity_type == EntityType.Devices:
                settings = self._get_collection('settings', limited_user=False).find_one({}) or {}
                if settings.get('defaultSort', False):
                    # Default sort by adapters list size and then Mongo id (giving order of insertion)
                    pipeline.append({'$sort': {ADAPTERS_LIST_LENGTH: pymongo.DESCENDING, '_id': pymongo.DESCENDING}})

            if skip:
                pipeline.append({'$skip': skip})
            if limit:
                pipeline.append({'$limit': limit})

            # Fetch from Mongo is done with aggregate, for the purpose of setting 'allowDiskUse'.
            # The reason is that sorting without the flag, causes exceeding of the memory limit.
            data_list = self._entity_views_db_map[entity_type].aggregate(pipeline, allowDiskUse=True)

            if filter and not skip:
                filter = request.args.get('filter')
                self._queries_db_map[entity_type].replace_one(
                    {'name': {'$exists': False}, 'filter': filter},
                    {'filter': filter, 'query_type': 'history', 'timestamp': datetime.now(), 'archived': False},
                    upsert=True)
            if not projection:
                return [beautify_db_entry(entity) for entity in data_list]
            return [self._parse_entity_fields(entity, projection.keys()) for entity in data_list]

    def _parse_entity_fields(self, entity_data, fields):
        """
        For each field in given list, if it begins with adapters_data, just fetch it from corresponding adapter.

        :param entity_data: A nested dict representing parsed values of an entity
        :param fields:      List of paths to values in the entity_data dict
        :return:            Mapping of a field path to it's value list as found in the entity_data
        """
        field_to_value = {}
        for field in fields:
            field_to_value[field] = self._find_entity_field(entity_data, field)
        return field_to_value

    def _find_entity_field(self, entity_data, field_path):
        """
        Recursively expand given entity, following period separated properties of given field_path,
        until reaching the requested value

        :param entity_data: A nested dict representing parsed values of an entity
        :param field_path:  A path to a field ('.' separated chain of keys)
        :return:
        """
        if entity_data is None:
            # Return no value for this path
            return ''
        if not field_path:
            # Return value corresponding with given path
            return entity_data

        if type(entity_data) != list:
            first_dot = field_path.find('.')
            if first_dot == -1:
                # Return value of last key in the chain
                return entity_data.get(field_path)
            # Continue recursively with value of current key and rest of path
            return self._find_entity_field(entity_data.get(field_path[:first_dot]), field_path[first_dot + 1:])

        if len(entity_data) == 1:
            # Continue recursively on the single element in the list, with the same path
            return self._find_entity_field(entity_data[0], field_path)

        children = []
        for item in entity_data:
            # Continue recursively for current element of the list
            child_value = self._find_entity_field(item, field_path)
            if child_value:
                def new_instance(value):
                    """
                    Test if given value is not yet found in the children list, according to comparison rules.
                    For strings, if value is a prefix of or has a prefix in the list, is considered to be found.
                    :param value:   Value for testing if exists in the list
                    :return: True, if value is new to the children list and False otherwise
                    """

                    def same_string(x, y):
                        return type(x) != 'str' or (re.match(x, y, re.I) or re.match(y, x, re.I))

                    if type(value) == str:
                        return len([child for child in children if same_string(child, value)]) == 0
                    if type(value) == int:
                        return value in children
                    if type(value) == dict:
                        # For a dict, check if there is an element of whom all keys are identical to value's keys
                        return len([item for item in children if len([key for key in item.keys()
                                                                      if same_string(item[key], value[key])]) > 0]) == 0
                    return False

                if type(child_value) == list:
                    # Check which elements of found value can be added to children
                    children = children + list(filter(new_instance, child_value))
                elif new_instance(child_value):
                    # Check if value found can be added to children
                    children.append(child_value)

        return children

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
        entities = self._get_entities(None, None, mongo_filter, mongo_sort, mongo_projection, entity_type)
        output = ''
        if len(entities) > 0:
            # Beautifying the resulting csv.
            del mongo_projection['internal_axon_id']
            del mongo_projection['unique_adapter_names']
            # Getting pretty titles for all generic fields as well as specific
            entity_fields = self._entity_fields(entity_type)
            for field in entity_fields['generic']:
                if field['name'] in mongo_projection:
                    mongo_projection[field['name']] = field['title']
            for type in entity_fields['specific']:
                for field in entity_fields['specific'][type]:
                    if field['name'] in mongo_projection:
                        mongo_projection[field['name']] = field['title']
            for current_entity in entities:
                del current_entity['internal_axon_id']
                del current_entity['unique_adapter_names']
                for field in mongo_projection.keys():
                    # Replace field paths with their pretty titles
                    if field in current_entity:
                        current_entity[mongo_projection[field]] = current_entity[field]
                        del current_entity[field]
            dw = csv.DictWriter(string_output, mongo_projection.values())
            dw.writeheader()
            dw.writerows(entities)
            output = make_response(string_output.getvalue())
            timestamp = datetime.now().strftime("%d%m%Y-%H%M%S")
            output.headers['Content-Disposition'] = f'attachment; filename=axonius-data_{timestamp}.csv'
            output.headers['Content-type'] = 'text/csv'
        return output

    def _entity_by_id(self, entity_type: EntityType, entity_id, advanced_fields=[]):
        """
        Retrieve device by the given id, from current devices DB or update it
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
                'basic': self._parse_entity_fields(entity, _basic_generic_field_names()),
                'advanced': [{
                    'name': category, 'data': self._find_entity_field(entity, f'specific_data.data.{category}')
                } for category in advanced_fields],
                'data': entity['generic_data']
            },
            'labels': entity['labels'],
            'internal_axon_id': entity['internal_axon_id']
        })

    def _entity_queries(self, limit, skip, filter, entity_type: EntityType):
        """
                GET Fetch all queries saved for given module, answering give filter
                POST Save a new query for given module
                     Data with a name for the query and a string filter is expected for saving

                :param limit: limit for pagination
                :param skip: start index for pagination
                :return: GET - List of query names and filters
                         POST - Id of inserted document saving given query
                """
        queries_collection = self._queries_db_map[entity_type]
        if request.method == 'GET':
            filter['$or'] = filter_archived()['$or']
            return jsonify(beautify_db_entry(entry) for entry in queries_collection.find(filter)
                           .sort([('timestamp', pymongo.DESCENDING)])
                           .skip(skip).limit(limit))
        if request.method == 'POST':
            query_to_add = request.get_json(silent=True)
            if query_to_add is None or query_to_add['filter'] == '':
                return return_error("Invalid query", 400)
            inserted_id = self._insert_query(queries_collection, query_to_add.get('name'), query_to_add.get('filter'),
                                             query_to_add.get('expressions'))
            return str(inserted_id), 200

    def _entity_queries_delete(self, entity_type: EntityType, query_id):
        queries_collection = self._queries_db_map[entity_type]
        queries_collection.update({'_id': ObjectId(query_id)},
                                  {
                                      '$set': {
                                          'archived': True
                                      }}
                                  )
        return ""

    def _get_entities_count(self, filter, entity_type: EntityType):
        """
        Count total number of devices answering given mongo_filter

        :param filter: Object defining a Mongo query
        :return: Number of devices
        """
        if filter:
            data_collection = self._entity_views_db_map[entity_type]
        else:
            # optimization: if there's no filter we can search the raw DB
            data_collection = self._entity_db_map[entity_type]
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
        with self._get_db_connection(False) as db_connection:
            plugins_from_db = list(db_connection['core']['configs'].find({}).
                                   sort([(plugin_consts.PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)]))
            for plugin in plugins_from_db:
                if not plugin[plugin_consts.PLUGIN_UNIQUE_NAME] in plugins_available:
                    continue
                plugin_fields = db_connection[plugin[plugin_consts.PLUGIN_UNIQUE_NAME]][f'{entity_type.value}_fields']
                if not plugin_fields:
                    continue
                plugin_fields_record = plugin_fields.find_one({'name': 'parsed'}, projection={'schema': 1})
                if not plugin_fields_record:
                    continue
                fields['schema']['specific'][plugin[plugin_consts.PLUGIN_NAME]] = plugin_fields_record['schema']
                fields['specific'][plugin[plugin_consts.PLUGIN_NAME]] = self._flatten_fields(
                    plugin_fields_record['schema'], f'adapters_data.{plugin[plugin_consts.PLUGIN_NAME]}', ['scanner'])

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
        with self._get_db_connection(False) as db_connection:
            entities = list(self._entity_db_map.get(entity_type).find(
                {'internal_axon_id': {
                    "$in": entity_uuids
                }}))

            entities_ids_by_adapters = {}
            for axonius_device in entities:
                for adapter_entity in axonius_device['adapters']:
                    entities_ids_by_adapters.setdefault(adapter_entity[plugin_consts.PLUGIN_UNIQUE_NAME], []).append(
                        adapter_entity['data']['id'])

                    # all adapters that are disabelable and that theres atleast one
                    entitydisabelables_adapters = [x[plugin_consts.PLUGIN_UNIQUE_NAME]
                                                   for x in
                                                   db_connection['core']['configs'].find(
                                                       filter={
                                                           'supported_features': feature,
                                                           plugin_consts.PLUGIN_UNIQUE_NAME: {
                                                               "$in": list(entities_ids_by_adapters.keys())
                                                           }
                                                       },
                                                       projection={
                                                           plugin_consts.PLUGIN_UNIQUE_NAME: 1
                                                       }
                    )]
        return entitydisabelables_adapters, entities_ids_by_adapters

    def _entity_views(self, method, entity_type: EntityType):
        """
        Save or fetch views over the entities db
        :return:
        """
        entity_views_collection = self._views_db_map[entity_type]
        if method == 'GET':
            mongo_filter = filter_archived()
            return jsonify(beautify_db_entry(entry) for entry in entity_views_collection.find(mongo_filter))

        # Handle POST request
        view_data = self.get_request_data_as_object()
        if not view_data.get('name'):
            return return_error(f'Name is required in order to save a view', 400)
        if not view_data.get('view'):
            return return_error(f'View data is required in order to save one', 400)
        update_result = entity_views_collection.replace_one({'name': view_data['name']}, view_data, upsert=True)
        if not update_result.upserted_id and not update_result.modified_count:
            return return_error(f'View named {view_data.name} was not saved', 400)
        return ''

    def _entity_labels(self, db, namespace):
        """
        GET Find all tags that currently belong to devices, to form a set of current tag values
        POST Add new tags to the list of given devices
        DELETE Remove old tags from the list of given devices
        :return:
        """
        all_labels = set()
        with self._get_db_connection(False) as db_connection:
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
            entities = [(entity[plugin_consts.PLUGIN_UNIQUE_NAME], entity['data']['id']) for entity in entities]

            response = namespace.add_many_labels(entities, labels=entities_and_labels['labels'],
                                                 are_enabled=request.method == 'POST')

            if response.status_code != 200:
                logger.error(f"Tagging did not complete. First {response.json()}")
                return_error(f'Tagging did not complete. First error: {response.json()}', 400)

            return '', 200

    ##########
    # DEVICE #
    ##########

    @paginated()
    @filtered()
    @sorted()
    @projected()
    @add_rule_unauthenticated("device")
    def get_devices(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        return jsonify(self._get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection, EntityType.Devices))

    @filtered()
    @sorted()
    @projected()
    @add_rule_unauthenticated("device/csv")
    def get_devices_csv(self, mongo_filter, mongo_sort, mongo_projection):
        return self._get_csv(mongo_filter, mongo_sort, mongo_projection, EntityType.Devices)

    @add_rule_unauthenticated("device/<device_id>", methods=['GET'])
    def device_by_id(self, device_id):
        return self._entity_by_id(EntityType.Devices, device_id, ['installed_software', 'security_patches', 'users'])

    @paginated()
    @filtered()
    @add_rule_unauthenticated("device/queries", methods=['POST', 'GET'])
    def device_queries_do(self, limit, skip, mongo_filter):
        return self._entity_queries(limit, skip, mongo_filter, EntityType.Devices)

    @add_rule_unauthenticated("device/queries/<query_id>", methods=['DELETE'])
    def device_queries_delete(self, query_id):
        return self._entity_queries_delete(EntityType.Devices, query_id)

    @filtered()
    @add_rule_unauthenticated("device/count")
    def get_devices_count(self, mongo_filter):
        return self._get_entities_count(mongo_filter, EntityType.Devices)

    @add_rule_unauthenticated("device/fields")
    def device_fields(self):
        return jsonify(self._entity_fields(EntityType.Devices))

    @add_rule_unauthenticated("device/views", methods=['GET', 'POST'])
    def device_views(self):
        """
        Save or fetch views over the devices db
        :return:
        """
        return self._entity_views(request.method, EntityType.Devices)

    @add_rule_unauthenticated("device/labels", methods=['GET', 'POST', 'DELETE'])
    def device_labels(self):
        return self._entity_labels(self.devices_db_view, self.devices)

    @add_rule_unauthenticated("device/disable", methods=['POST'])
    def disable_device(self):
        return self._disable_entity(EntityType.Devices)

    #########
    # USER #
    #########

    @paginated()
    @filtered()
    @sorted()
    @projected()
    @add_rule_unauthenticated("user")
    def get_users(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        return jsonify(self._get_entities(limit, skip, mongo_filter, mongo_sort, mongo_projection, EntityType.Users))

    @filtered()
    @sorted()
    @projected()
    @add_rule_unauthenticated("user/csv")
    def get_users_csv(self, mongo_filter, mongo_sort, mongo_projection):
        return self._get_csv(mongo_filter, mongo_sort, mongo_projection, EntityType.Users)

    @add_rule_unauthenticated("user/<user_id>", methods=['GET'])
    def user_by_id(self, user_id):
        return self._entity_by_id(EntityType.Users, user_id, ['associated_devices'])

    @paginated()
    @filtered()
    @add_rule_unauthenticated("user/queries", methods=['POST', 'GET'])
    def user_queries(self, limit, skip, mongo_filter):
        return self._entity_queries(limit, skip, mongo_filter, EntityType.Users)

    @add_rule_unauthenticated("user/queries/<query_id>", methods=['DELETE'])
    def user_queries_delete(self, query_id):
        return self._entity_queries_delete(EntityType.Users, query_id)

    @filtered()
    @add_rule_unauthenticated("user/count")
    def get_users_count(self, mongo_filter):
        return self._get_entities_count(mongo_filter, EntityType.Users)

    @add_rule_unauthenticated("user/fields")
    def user_fields(self):
        return jsonify(self._entity_fields(EntityType.Users))

    @add_rule_unauthenticated("user/disable", methods=['POST'])
    def disable_user(self):
        return self._disable_entity(EntityType.Users)

    @add_rule_unauthenticated("user/views", methods=['GET', 'POST'])
    def user_views(self):
        return self._entity_views(request.method, EntityType.Users)

    @add_rule_unauthenticated("user/labels", methods=['GET', 'POST', 'DELETE'])
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

    @filtered()
    @add_rule_unauthenticated("adapters")
    def adapters(self, mongo_filter):
        """
        Get all adapters from the core
        :mongo_filter
        :return:
        """
        plugins_available = requests.get(self.core_address + '/register').json()
        with self._get_db_connection(False) as db_connection:
            adapters_from_db = db_connection['core']['configs'].find({'$or': [{'plugin_type': 'Adapter'},
                                                                              {'plugin_type': 'ScannerAdapter'}]}).sort(
                [(plugin_consts.PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
            adapters_to_return = []
            for adapter in adapters_from_db:
                adapter_name = adapter[plugin_consts.PLUGIN_UNIQUE_NAME]
                if adapter_name not in plugins_available:
                    # Plugin not registered - unwanted in UI
                    continue

                plugin_db = db_connection[adapter_name]
                clients_configured = plugin_db['clients'].find(
                    projection={'_id': 1}).count()
                status = ''
                if clients_configured:
                    clients_connected = plugin_db['clients'].find(
                        {'status': 'success'}, projection={'_id': 1}).count()
                    status = 'success' if clients_configured == clients_connected else 'warning'

                adapters_to_return.append({'plugin_name': adapter['plugin_name'],
                                           'unique_plugin_name': adapter_name,
                                           'status': status,
                                           'supported_features': adapter['supported_features'],
                                           'config_data': self.__extract_configs_and_schemas(db_connection,
                                                                                             adapter_name)
                                           })

            return jsonify(adapters_to_return)

    def _query_client_for_devices(self, request, adapter_unique_name):
        client_to_add = request.get_json(silent=True)
        if client_to_add is None:
            return return_error("Invalid client", 400)

        # adding client to specific adapter
        response = self.request_remote_plugin("clients", adapter_unique_name, method='put', json=client_to_add)
        if response.status_code != 200:
            # failed, return immediately
            return response.text, response.status_code

        # if there's no aggregator, that's fine
        try:
            self.request_remote_plugin(f"trigger/{adapter_unique_name}",
                                       plugin_consts.AGGREGATOR_PLUGIN_NAME, method='post')
            research_state = self.request_remote_plugin(f"state",
                                                        plugin_consts.SYSTEM_SCHEDULER_PLUGIN_NAME, method='get').json()
            if research_state[StateLevels.Phase.name] == Phases.Stable.name:
                logger.info('System is stable, triggering static correlator')
                self.request_remote_plugin(
                    f"trigger/execute", plugin_consts.STATIC_CORRELATOR_PLUGIN_NAME, method='post')
            else:
                logger.info('System is in research phase, not triggering static correlator')
        except Exception:
            # if there's no aggregator, there's nothing we can do
            pass
        return response.text, response.status_code

    @paginated()
    @add_rule_unauthenticated("adapters/<adapter_unique_name>/clients", methods=['PUT', 'GET'])
    def adapters_clients(self, adapter_unique_name, limit, skip):
        """
        Gets or creates clients in the adapter
        :param adapter_unique_name: the adapter to refer to
        :param limit: for pagination (only for GET)
        :param skip: for pagination (only for GET)
        :return:
        """
        with self._get_db_connection(False) as db_connection:
            if request.method == 'GET':
                client_collection = db_connection[adapter_unique_name]['clients']
                return jsonify({
                    'schema': self._get_plugin_schemas(db_connection, adapter_unique_name)['clients'],
                    'clients': [beautify_db_entry(client) for client in
                                client_collection.find().skip(skip).limit(limit)]
                })
            if request.method == 'PUT':
                return self._query_client_for_devices(request, adapter_unique_name)

    @add_rule_unauthenticated("adapters/<adapter_unique_name>/clients/<client_id>", methods=['PUT', 'DELETE'])
    def adapters_clients_update(self, adapter_unique_name, client_id):
        """
        Gets or creates clients in the adapter
        :param adapter_unique_name: the adapter to refer to
        :param client_id: UUID of client to delete
        :return:
        """
        self.request_remote_plugin("clients/" + client_id, adapter_unique_name, method='delete')
        if request.method == 'PUT':
            return self._query_client_for_devices(request, adapter_unique_name)
        if request.method == 'DELETE':
            return '', 200

    @add_rule_unauthenticated("actions/<action_type>", methods=['POST'])
    def actions_run(self, action_type):
        """
        Executes a run shell command on devices.
        Expected values: a list of internal axon ids, the action name, and the action command.
        :return:
        """
        action_data = self.get_request_data_as_object()
        action_data['action_type'] = action_type

        # The format of data is defined in device_control\service.py::run_shell
        try:
            device_control_unique_name = self.get_plugin_by_name("device_control")['plugin_unique_name']
            response = self.request_remote_plugin('run_action', device_control_unique_name, 'post', json=action_data)
            if response.status_code != 200:
                logger.error(
                    f"Execute of {action_type} returned {response.status_code}. Reason: {str(response.content)}")
                raise ValueError(
                    f"Execute of {action_type} returned {response.status_code}. Reason: {str(response.content)}")
            return '', 200
        except Exception as e:
            return return_error(f'Attempt to run action {action_type} caused exception. Reason: {repr(e)}', 400)

    @add_rule_unauthenticated("reports", methods=['GET', 'PUT'])
    def reports(self):
        """
        GET results in list of all currently configured alerts, with their query id they were created with
        PUT Send report_service a new report to be configured

        :return:
        """
        if request.method == 'GET':
            with self._get_db_connection(False) as db_connection:
                reports_to_return = []
                report_service = self.get_plugin_by_name('reports')
                for report in db_connection[report_service[plugin_consts.PLUGIN_UNIQUE_NAME]]['reports'].find(
                        projection={'name': 1, 'report_creation_time': 1, 'severity': 1, 'actions': 1, 'triggers': 1,
                                    'retrigger': 1, 'query': 1}).sort([('report_creation_time', pymongo.DESCENDING)]):
                    reports_to_return.append(beautify_db_entry(report))
                return jsonify(reports_to_return)

        if request.method == 'PUT':
            report_to_add = request.get_json(silent=True)
            query_name = report_to_add['query']
            query_entity = report_to_add['queryEntity']
            assert query_entity in [x.value for x in EntityType.__members__.values()]
            queries = self.device_queries if query_entity == EntityType.Devices.value else self.user_queries
            if queries.find_one({'name': query_name}) is None:
                return return_error(f"Missing query {query_name} requested for creating alert")

            response = self.request_remote_plugin("reports", "reports", method='put', json=report_to_add)
            return response.text, response.status_code

    @add_rule_unauthenticated("reports/<report_id>", methods=['DELETE', 'POST'])
    def alerts_update(self, report_id):
        """

        :param alert_id:
        :return:
        """
        if request.method == 'DELETE':
            response = self.request_remote_plugin(f"reports/{report_id}", "reports", method='delete')
            if response is None:
                return return_error("No response whether alert was removed")
            return response.text, response.status_code

        if request.method == 'POST':
            report_to_update = request.get_json(silent=True)
            query_name = report_to_update['query']
            query_entity = report_to_update['queryEntity']
            assert query_entity in [x.value for x in EntityType.__members__.values()]
            queries = self.device_queries if query_entity == EntityType.Devices.value else self.user_queries
            if queries.find_one({'name': query_name}) is None:
                return return_error(f"Missing query {query_name} requested for updating alert")

            response = self.request_remote_plugin(f"reports/{report_id}", "reports", method='post',
                                                  json=report_to_update)
            if response is None:
                return return_error("No response whether alert was updated")

            return response.text, response.status_code

    @filtered()
    @add_rule_unauthenticated("plugins")
    def plugins(self, mongo_filter):
        """
        Get all plugins configured in core and update each one's status.
        Status will be "error" if the plugin is not registered.
        Otherwise it will be "success", if currently running or "warning", if  stopped.

        :mongo_filter
        :return: List of plugins with
        """
        plugins_available = requests.get(self.core_address + '/register').json()
        with self._get_db_connection(False) as db_connection:
            plugins_from_db = db_connection['core']['configs'].find({'plugin_type': 'Plugin'}).sort(
                [(plugin_consts.PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
            plugins_to_return = []
            for plugin in plugins_from_db:
                # TODO check supported features
                if plugin['plugin_type'] != "Plugin" or plugin['plugin_name'] in [plugin_consts.AGGREGATOR_PLUGIN_NAME,
                                                                                  "gui",
                                                                                  "watch_service",
                                                                                  "execution",
                                                                                  "system_scheduler"]:
                    continue

                processed_plugin = {'plugin_name': plugin['plugin_name'],
                                    'unique_plugin_name': plugin[plugin_consts.PLUGIN_UNIQUE_NAME],
                                    'status': 'error',
                                    'state': 'Disabled'
                                    }
                if plugin[plugin_consts.PLUGIN_UNIQUE_NAME] in plugins_available:
                    processed_plugin['status'] = 'warning'
                    response = self.request_remote_plugin(
                        "trigger_state/execute", plugin[plugin_consts.PLUGIN_UNIQUE_NAME])
                    if response.status_code != 200:
                        logger.error("Error getting state of plugin {0}".format(
                            plugin[plugin_consts.PLUGIN_UNIQUE_NAME]))
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
        configs = list(db_connection[plugin_unique_name]['configs'].find())
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

    @add_rule_unauthenticated("plugins/configs/<plugin_unique_name>/<config_name>", methods=['POST'])
    def plugins_configs_set(self, plugin_unique_name, config_name):
        """
        Set a specific config on a specific plugin
        """
        config_to_set = request.get_json(silent=True)
        if config_to_set is None:
            return return_error("Invalid config", 400)

        with self._get_db_connection(False) as db_connection:
            config_collection = db_connection[plugin_unique_name]['configs']

            config_collection.replace_one(filter={
                'config_name': config_name
            },
                replacement={
                    "config_name": config_name,
                    "config": config_to_set
            })
            self.request_remote_plugin("update_config", plugin_unique_name, method='POST')

        return ""

    @add_rule_unauthenticated("plugins/<plugin_unique_name>/<command>", methods=['POST'])
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

    @add_rule_unauthenticated("config/<config_name>", methods=['POST', 'GET'])
    def config(self, config_name):
        """
        Get or set config by name
        :param config_name: Config to fetch
        :return:
        """
        configs_collection = self._get_collection('config', limited_user=False)
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

    @paginated()
    @filtered()
    @add_rule_unauthenticated("notifications", methods=['POST', 'GET'])
    def notifications(self, limit, skip, mongo_filter):
        """
        Get all notifications
        :param limit: limit for pagination
        :param skip: start index for pagination
        :return:
        """
        with self._get_db_connection(False) as db:
            notification_collection = db['core']['notifications']
            if request.method == 'GET':
                return jsonify(beautify_db_entry(n) for n in
                               notification_collection.find(mongo_filter, projection={
                                   "_id": 1,
                                   "who": 1,
                                   "plugin_name": 1,
                                   "type": 1,
                                   "title": 1,
                                   "seen": 1,
                                   "severity": 1}).skip(skip).limit(limit))
            elif request.method == 'POST':
                notifications_to_see = request.get_json(silent=True)
                if notifications_to_see is None:
                    return return_error("Invalid notification list", 400)
                update_result = notification_collection.update_many(
                    {"_id": {"$in": [ObjectId(x) for x in notifications_to_see.get('notification_ids', [])]}
                     }, {"$set": {'seen': notifications_to_see.get('seen', True)}})
                return str(update_result.modified_count), 200

    @filtered()
    @add_rule_unauthenticated("notifications/count", methods=['GET'])
    def notifications_count(self, mongo_filter):
        """
        Fetches from core's notification collection, according to given mongo_filter,
        and counts how many entries in retrieved cursor
        :param mongo_filter: Generated by the filtered() decorator, according to uri param "filter"
        :return: Number of notifications matching given filter
        """
        with self._get_db_connection(False) as db:
            notification_collection = db['core']['notifications']
            return str(notification_collection.find(mongo_filter).count())

    @add_rule_unauthenticated("notifications/<notification_id>", methods=['GET'])
    def notifications_by_id(self, notification_id):
        """
        Get all notification data
        :param notification_id: Notification ID
        :return:
        """
        with self._get_db_connection(False) as db:
            notification_collection = db['core']['notifications']
            return jsonify(beautify_db_entry(notification_collection.find_one({'_id': ObjectId(notification_id)})))

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
            del user['password']
            return jsonify(user), 200

        users_collection = self._get_collection('users', limited_user=False)
        log_in_data = self.get_request_data_as_object()
        if log_in_data is None:
            return return_error("No login data provided", 400)
        user_name = log_in_data.get('user_name')
        password = log_in_data.get('password')
        user_from_db = users_collection.find_one({'user_name': user_name})
        if user_from_db is None:
            logger.info(f"Unknown user {user_name} tried logging in")
            return return_error("Wrong user name or password", 401)
        if not bcrypt.verify(password, user_from_db['password']):
            logger.info(f"User {user_name} tried logging in with wrong password")
            return return_error("Wrong user name or password", 401)
        session['user'] = user_from_db
        return ""

    @add_rule_unauthenticated("logout", methods=['GET'])
    def logout(self):
        """
        Clears session, logs out
        :return:
        """
        session['user'] = None
        return ""

    # @paginated()
    # @add_rule("users", methods=['GET', 'POST'])
    # def users(self, limit, skip):
    #     """
    #     View or add users
    #     :param limit: limit for pagination
    #     :param skip: start index for pagination
    #     :return:
    #     """
    #     users_collection = self._get_collection('users', limited_user=False)
    #     if request.method == 'GET':
    #         return jsonify(beautify_db_entry(n) for n in
    #                        users_collection.find(projection={
    #                            "_id": 1,
    #                            "user_name": 1,
    #                            "first_name": 1,
    #                            "last_name": 1,
    #                            "pic_name": 1}).sort(
    #                            [('_id', pymongo.ASCENDING)]).skip(skip).limit(limit))
    #     elif request.method == 'POST':
    #         user_data = self.get_request_data_as_object()
    #         users_collection.update({'user_name': user_data['user_name']},
    #                                 {'user_name': user_data['user_name'],
    #                                  'first_name': user_data.get('first_name'),
    #                                  'last_name': user_data.get('last_name'),
    #                                  'pic_name': user_data.get('pic_name'),
    #                                  'password': bcrypt.hash(user_data['password']),
    #                                  },
    #                                 upsert=True)
    #         return "", 201

    @paginated()
    @add_rule_unauthenticated("logs")
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

    @add_rule_unauthenticated("dashboard", methods=['POST', 'GET'])
    def get_dashboard(self):
        if request.method == 'GET':
            return jsonify(self._get_dashboard())

        # Handle 'POST' request method - save dashboard configuration
        dashboard_data = self.get_request_data_as_object()
        if not dashboard_data.get('name'):
            return return_error('Name required in order to save Dashboard Chart', 400)
        if not dashboard_data.get('queries'):
            return return_error('At least one query required in order to save Dashboard Chart', 400)
        update_result = self._get_collection('dashboard', limited_user=False).replace_one(
            {'name': dashboard_data['name']}, dashboard_data, upsert=True)
        if not update_result.upserted_id and not update_result.modified_count:
            return return_error('Error saving dashboard chart', 400)
        return str(update_result.upserted_id)

    def _get_dashboard(self):
        """
        GET Fetch current dashboard chart definitions. For each definition, fetch each of it's queries and
        fetch devices_db_view with their view. Amount of results is mapped to each queries' name, under 'data' key,
        to be returned with the dashboard definition.

        POST Save a new dashboard chart definition, given it has a name and at least one query attached

        :return:
        """
        dashboard_list = []
        for dashboard in self._get_collection('dashboard', limited_user=False).find(filter_archived()):
            if not dashboard.get('name'):
                logger.info(f'No name for dashboard {dashboard["_id"]}')
            elif not dashboard.get('queries'):
                logger.info(f'No queries found for dashboard {dashboard.get("name")}')
            else:
                # Let's fetch and execute them query filters, depending on the chart's type
                try:
                    if dashboard['type'] == ChartTypes.compare.name:
                        dashboard['data'] = self._fetch_data_for_chart_compare(dashboard['queries'])
                    elif dashboard['type'] == ChartTypes.intersect.name:
                        dashboard['data'] = self._fetch_data_for_chart_intersect(dashboard['queries'])
                    dashboard_list.append(beautify_db_entry(dashboard))
                except Exception as e:
                    # Since there is no data, not adding this chart to the list
                    logger.exception(
                        f'Error fetching data for chart {dashboard["name"]} ({dashboard["_id"]}). Reason: {e}')
        return dashboard_list

    def _fetch_data_for_chart_compare(self, dashboard_queries):
        """
        Iterate given queries, fetch each one's filter from the appropriate query collection, according to its module,
        and execute the filter on the appropriate entity collection.

        :param dashboard_queries:
        :return:
        """
        if not dashboard_queries:
            raise Exception('No queries for the chart')
        data = []
        for query in dashboard_queries:
            # Can be optimized by taking all names in advance and querying each module's collection once
            # But since list is very short the simpler and more readable implementation is fine
            query_object = self._get_collection(f'{query["module"]}_queries', limited_user=False).find_one(
                {'name': query['name']})
            if not query_object or not query_object.get('filter'):
                raise Exception(f'No filter found for query {query["name"]}')
            data.append({'name': query['name'], 'filter': query_object['filter'], 'module': query['module'],
                         'count': self.aggregator_db_connection[f'{query["module"]}s_db_view'].find(
                             parse_filter(query_object['filter']), {'_id': 1}).count()})
        return data

    def _fetch_data_for_chart_intersect(self, dashboard_queries):
        """
        This chart shows intersection of 1 or 2 'Child' queries with a 'Parent' (expected not to be a subset of them).
        Module to be queried is defined by the parent query.

        :param dashboard_queries: List of 2 or 3 queries
        :return: List of result portions for the query executions along with their names. First represents Parent query.
                 If 1 child, second represents Child intersecting with Parent.
                 If 2 children, intersection between all three is calculated, namely 'Intersection'.
                                Second and third represent each Child intersecting with Parent, excluding Intersection.
                                Fourth represents Intersection.
        """
        if not dashboard_queries or len(dashboard_queries) < 2:
            raise Exception('Pie chart requires at least two queries')
        module = dashboard_queries[0]['module']
        # Query and data collections according to given parent's module
        queries_collection = self._get_collection(f'{module}_queries', limited_user=False)
        data_collection = self.aggregator_db_connection[f'{module}s_db_view']

        parent_name = dashboard_queries[0]['name']
        parent_filter = parse_filter(queries_collection.find_one({'name': parent_name})['filter'])
        data = [{'name': parent_name, 'count': data_collection.find(parent_filter, {'_id': 1}).count()}]

        child_name_1 = dashboard_queries[1]['name']
        child_filter_1 = parse_filter(queries_collection.find_one({'name': child_name_1})['filter'])
        if len(dashboard_queries) == 2:
            # Fetch the only child, intersecting with parent
            data.append({'name': child_name_1,
                         'count': data_collection.find({'$and': [parent_filter, child_filter_1]}, {'_id': 1}).count()})
        else:
            child_name_2 = dashboard_queries[2]['name']
            child_filter_2 = parse_filter(queries_collection.find_one({'name': child_name_2})['filter'])

            # Fetch the intersection of parent and 2 children and create match to exclude their _IDs
            intersection_cursor = data_collection.find({'$and': [parent_filter, child_filter_1, child_filter_2]},
                                                       {'_id': 1})
            not_intersection = {'_id': {'$not': {'$in': [ObjectId(entry['_id']) for entry in intersection_cursor]}}}
            # Child1 + Parent - Intersection
            data.append({'name': child_name_1,
                         'count': data_collection.find({'$and': [parent_filter, child_filter_1, not_intersection]},
                                                       {'_id': 1}).count()})
            # Intersection
            data.append({'name': f'{child_name_1} + {child_name_2}', 'count': intersection_cursor.count()})
            # Child2 + Parent - Intersection
            data.append({'name': child_name_2,
                         'count': data_collection.find({'$and': [parent_filter, child_filter_2, not_intersection]},
                                                       {'_id': 1}).count()})
        return data

    @add_rule_unauthenticated("dashboard/<dashboard_id>", methods=['DELETE'])
    def remove_dashboard(self, dashboard_id):
        """
        Fetches data, according to definition saved for the dashboard named by given name

        :param dashboard_name: Name of the dashboard to fetch data for
        :return:
        """
        update_result = self._get_collection('dashboard', limited_user=False).replace_one(
            {'_id': ObjectId(dashboard_id)}, {'archived': True})
        if not update_result.modified_count:
            return return_error(f'No dashboard by the id {dashboard_id} found or updated', 400)
        return ''

    @add_rule_unauthenticated("dashboard/lifecycle", methods=['GET'])
    def get_system_lifecycle(self):
        """
        Fetches and build data needed for presenting current status of the system's lifecycle in a graph

        :return: Data containing:
         - All research phases names, for showing the whole picture
         - Current research sub-phase, which is empty if system is not stable
         - Portion of work remaining for the current sub-phase
         - The time next cycle is scheduled to run
        """
        state_response = self.request_remote_plugin('state', plugin_consts.SYSTEM_SCHEDULER_PLUGIN_NAME)
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

        run_time_response = self.request_remote_plugin('next_run_time', plugin_consts.SYSTEM_SCHEDULER_PLUGIN_NAME)
        if run_time_response.status_code != 200:
            return return_error(f"Error fetching run time of system scheduler. Reason: {run_time_response.text}")

        return jsonify({'sub_phases': sub_phases, 'next_run_time': run_time_response.text})

    @add_rule_unauthenticated("dashboard/lifecycle_rate", methods=['GET', 'POST'])
    def system_lifecycle_rate(self):
        """

        """
        if self.get_method() == 'GET':
            response = self.request_remote_plugin('research_rate', plugin_consts.SYSTEM_SCHEDULER_PLUGIN_NAME)
            return response.content
        elif self.get_method() == 'POST':
            response = self.request_remote_plugin(
                'research_rate', plugin_consts.SYSTEM_SCHEDULER_PLUGIN_NAME, method='POST',
                json=self.get_request_data_as_object())
            logger.info(f"response code: {response.status_code} response crap: {response.content}")
            return ''

    def _adapter_devices(self):
        """
        For each adapter currently registered in system, count how many devices it fetched.

        :return: Map between each adapter and the number of devices it has, unless no devices
        """
        plugins_available = requests.get(self.core_address + '/register').json()
        adapter_devices = {'total_gross': 0, 'adapter_count': []}
        with self._get_db_connection(False) as db_connection:
            adapter_devices['total_net'] = self.devices_db.count()
            adapters_from_db = db_connection['core']['configs'].find({'plugin_type': 'Adapter'})
            for adapter in adapters_from_db:
                if not adapter[plugin_consts.PLUGIN_UNIQUE_NAME] in plugins_available:
                    # Plugin not registered - unwanted in UI
                    continue
                devices_count = self.devices_db.count({'adapters.plugin_name': adapter['plugin_name']})
                if not devices_count:
                    # No need to document since adapter has no devices
                    continue
                adapter_devices['adapter_count'].append({'name': adapter['plugin_name'], 'count': devices_count})
                adapter_devices['total_gross'] = adapter_devices['total_gross'] + devices_count
        return adapter_devices

    @add_rule_unauthenticated("dashboard/adapter_devices", methods=['GET'])
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
        devices_total = self.devices_db_view.count()
        if not devices_total:
            return []
        coverage_list = [
            {'title': 'Managed Device', 'properties': [AdapterProperty.Manager.name, AdapterProperty.Agent.name],
             'description': 'Deploy appropriate agents on unmanaged devices, and add them to Active Directory.'},
            {'title': 'Endpoint Protection', 'properties': [AdapterProperty.Endpoint_Protection_Platform.name],
             'description': 'Add an endpoint protection solution to uncovered devices.'},
            {'title': 'VA Scanner', 'properties': [AdapterProperty.Vulnerability_Assessment.name],
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

    @add_rule_unauthenticated("dashboard/coverage", methods=['GET'])
    def get_dashboard_coverage(self):
        return jsonify(self._get_dashboard_coverage())

    @add_rule_unauthenticated("research_phase", methods=['POST'])
    def schedule_research_phase(self):
        """
        Schedules or initiates research phase.

        :return: Map between each adapter and the number of devices it has, unless no devices
        """
        data = self.get_request_data_as_object()
        logger.info(f"Scheduling Research Phase to: {data if data else 'Now'}")
        response = self.request_remote_plugin(
            'trigger/execute', plugin_consts.SYSTEM_SCHEDULER_PLUGIN_NAME, 'POST', json=data)

        if response.status_code != 200:
            logger.error(f"Could not schedule research phase to: {data if data else 'Now'}")
            return return_error(f"Could not schedule research phase to: {data if data else 'Now'}",
                                response.status_code)

        return ''

    #############
    # SETTINGS #
    #############

    @add_rule_unauthenticated("settings", methods=['POST', 'GET'])
    def settings(self):
        """
        Gets or saves current settings for the system

        :return:
        """
        settings_collection = self._get_collection('settings', limited_user=False)
        if (request.method == 'GET'):
            settings_object = settings_collection.find_one({})
            if not settings_object:
                return jsonify({})
            return jsonify(beautify_db_entry(settings_object))

        # Handle POST request
        settings_object = self.get_request_data_as_object()
        update_result = settings_collection.replace_one({}, settings_object, upsert=True)
        if not update_result.upserted_id and not update_result.modified_count:
            return return_error('Error saving settings', 400)
        return ''

    @add_rule_unauthenticated("email_server", methods=['POST', 'GET', 'DELETE'])
    def email_server(self):
        """
        Adds, Gets and Deletes currently saved mail servers

        :return: Map between each adapter and the number of devices it has, unless no devices
        """
        response = self.request_remote_plugin('email_server', None, self.get_method(),
                                              json=self.get_request_data_as_object())
        if self.get_method() in ('POST', 'GET') and response.status_code == 200:
            return jsonify(response.json())
        else:
            return response.content, response.status_code

    @add_rule_unauthenticated("execution/<plugin_state>", methods=['POST'])
    def toggle_execution(self, plugin_state):
        services = ['execution', 'careful_execution_correlator', 'general_info']
        statuses = []
        for current_service in services:
            response = self.request_remote_plugin('plugin_state', current_service, 'POST',
                                                  params={'wanted': plugin_state})

            if response.status_code != 200:
                logger.error(f"Failed to {plugin_state} {current_service}.")
                statuses.append(False)
            else:
                logger.info(f"Switched {current_service} to be {plugin_state}.")
                statuses.append(True)

        return '' if all(statuses) else return_error(f'Failed to {plugin_state} all plugins', 500)

    @add_rule_unauthenticated("execution", methods=['GET'])
    def get_execution(self):
        services = ['execution', 'careful_execution_correlator', 'general_info']
        enabled = False
        for current_service in services:
            response = self.request_remote_plugin('plugin_state', current_service)
            if response.status_code == 200 and response.json()['state'] == 'enabled':
                enabled = True
                break

        return 'enabled' if enabled else 'disabled'

    @add_rule_unauthenticated('export_report')
    def export_report(self):
        """
        Gets definition of report from DB for the dynamic content.
        Gets all the needed data for both pre-defined and dynamic content definitions.
        Sends the complete data to the report generator to be composed to one document and generated as a pdf file.

        TBD Should receive ID of the report to export (once there will be an option to save many report definitions)
        :return:
        """
        report_data = {
            'adapter_devices': self._adapter_devices(),
            'covered_devices': self._get_dashboard_coverage(),
            'custom_charts': self._get_dashboard(),
            'views_data': self._get_saved_views_data()
        }
        report = self._get_collection('reports', limited_user=False).find_one({'name': 'Main Report'})
        if report.get('adapters'):
            report_data['adapter_queries'] = self._get_adapter_queries(report['adapters'])
        temp_report_filename = ReportGenerator(report_data, 'gui/templates/report/').generate()
        return send_file(temp_report_filename, mimetype='application/pdf', as_attachment=True,
                         attachment_filename=temp_report_filename)

    def _get_adapter_queries(self, adapters):
        """
        Get the definition of the adapters to include in the report. For each adapter, get the queries defined for it
        and execute each one, according to its entity, to get the amount of results for it.

        :return:
        """
        adapter_queries = []
        for adapter in adapters:
            queries = []
            for query in adapter.get('queries', []):
                if not query.get('name') or not query.get('entity'):
                    continue
                entity = EntityType(query['entity'])
                filter = self._queries_db_map[entity].find_one({'name': query['name']}).get('filter')
                if filter:
                    logger.info(f'Executing filter {filter} on entity {entity.name}')
                    queries.append({
                        **query,
                        'count': self._entity_views_db_map[entity].find(parse_filter(filter), {'_id': 1}).count()
                    })
            if queries:
                adapter_queries.append({'name': adapter.get('name', 'Adapter'), 'queries': queries})
        return adapter_queries

    def _get_saved_views_data(self):
        """
        For each entity in system, fetch all saved views.
        For each view, fetch first page of entities - filtered, projected, sorted according to it's definition.

        :return: Lists of the view names along with the list of results and list of field headers, with pretty names.
        """

        def _get_sort(view):
            sort_def = view.get('sort')
            sort_obj = {}
            if sort_def and sort_def.get('field'):
                sort_obj[sort_def['field']] = pymongo.DESCENDING if (sort_def['desc']) else pymongo.ASCENDING
            return sort_obj

        def _get_field_titles(entity):
            entity_fields = self._entity_fields(entity)
            name_to_title = {}
            for field in entity_fields['generic']:
                name_to_title[field['name']] = field['title']
            for type in entity_fields['specific']:
                for field in entity_fields['specific'][type]:
                    name_to_title[field['name']] = field['title']
            return name_to_title

        views_data = []
        for entity in EntityType:
            field_to_title = _get_field_titles(entity)
            saved_views = self._views_db_map[entity].find(filter_archived())
            for i, view_doc in enumerate(saved_views):
                view = view_doc.get('view')
                if view:
                    field_list = view.get('fields', [])
                    views_data.append({
                        'name': view_doc.get('name', f'View {i}'),
                        'fields': [{'name': field, 'title': field_to_title.get(field, field)} for field in field_list],
                        'data': self._get_entities(view.get('pageSize', 20), 0,
                                                   parse_filter(view.get('query', {}).get('filter', '')),
                                                   _get_sort(view), {field: 1 for field in field_list}, entity)
                    })
        return views_data

    @property
    def plugin_subtype(self):
        return "Core"
